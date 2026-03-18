"""
PRAJNA SLM — Small Language Model for Exam Topic Prediction.

Architecture:
  Topic Name -> Sentence-Transformer (22M params) -> 384-dim embedding
  Concat with 15 numerical features (399-dim total)
  MLP Head: 399 -> 256 -> 128 -> 64
  Output heads: P(appear), Exp.Questions, Difficulty

What makes this a genuine SLM:
  1. Pre-trained language backbone (all-MiniLM-L6-v2, 22M params)
  2. Learned prediction weights via gradient descent
  3. Multi-task output heads
  4. Total ~23M params, runs on CPU in <50ms
"""

import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer
from collections import Counter
from utils.db import get_questions_df


# ================================================================
# FEATURE EXTRACTION
# ================================================================

def extract_features_for_year(df, topic_name, subject, target_year, min_year, max_year):
    """
    Extract 15 numerical features for a (topic, year) pair using only
    data available BEFORE target_year.
    """
    features = np.zeros(15, dtype=np.float32)

    topic_df = df[(df["topic"] == topic_name) & (df["year"] < target_year)]

    if topic_df.empty:
        features[14] = _subject_val(subject)
        return features

    years_appeared = sorted(topic_df["year"].unique())
    qs_per_year = topic_df.groupby("year").size().to_dict()
    year_span = max(max_year - min_year + 1, 1)

    # 0: Appearance rate
    features[0] = len(years_appeared) / year_span

    # 1: Recency-weighted frequency
    rwf = sum(1.0 / ((target_year - y) ** 1.5 + 1) for y in years_appeared)
    max_possible = sum(1.0 / ((target_year - y) ** 1.5 + 1) for y in range(min_year, max_year + 1))
    features[1] = min(rwf / (max_possible + 0.01), 1.0)

    # 2-3: Recent presence
    features[2] = min(sum(1 for y in years_appeared if y >= max_year - 2) / 3.0, 1.0)
    features[3] = min(sum(1 for y in years_appeared if y >= max_year - 4) / 5.0, 1.0)

    # 4: Gap years (normalized)
    gap = target_year - max(years_appeared)
    features[4] = min(gap / 10.0, 1.0)

    # 5: Mean gap (normalized)
    gaps_sorted = sorted(set(years_appeared))
    inter_gaps = [gaps_sorted[i+1] - gaps_sorted[i] for i in range(len(gaps_sorted) - 1)]
    features[5] = min(np.mean(inter_gaps) / 5.0, 1.0) if inter_gaps else 0.5

    # 6: Trend slope
    recent_window = list(range(max(min_year, max_year - 9), max_year + 1))
    year_counts = Counter(years_appeared)
    y_vals = [year_counts.get(yr, 0) for yr in recent_window]
    if len(y_vals) >= 3 and sum(y_vals) > 0:
        x = np.arange(len(y_vals), dtype=float)
        slope = np.polyfit(x, y_vals, 1)[0]
        features[6] = min(max((slope + 0.5) / 1.0, 0), 1.0)
    else:
        features[6] = 0.5

    # 7-9: Question count stats
    qs_values = list(qs_per_year.values())
    features[7] = min(np.mean(qs_values) / 6.0, 1.0)
    features[8] = min(np.std(qs_values) / 3.0, 1.0) if len(qs_values) > 1 else 0.0
    features[9] = min(max(qs_values) / 8.0, 1.0)

    # 10: Total appearances (normalized)
    features[10] = min(len(years_appeared) / 20.0, 1.0)

    # 11: Cross-exam presence (set by caller)
    features[11] = 0.0

    # 12: Cycle regularity
    if inter_gaps and len(inter_gaps) >= 3:
        cv = np.std(inter_gaps) / (np.mean(inter_gaps) + 0.01)
        features[12] = max(0, 1.0 - cv)
    else:
        features[12] = 0.0

    # 13: Recent yield average
    recent_vals = sorted(qs_per_year.items(), key=lambda x: x[0])[-3:]
    features[13] = min(np.mean([v for _, v in recent_vals]) / 4.0, 1.0)

    # 14: Subject encoding
    features[14] = _subject_val(subject)

    return features


def _subject_val(subject):
    return {"Physics": 0.25, "Chemistry": 0.50, "Biology": 0.75, "Mathematics": 1.0}.get(subject, 0.0)


# ================================================================
# DATASET
# ================================================================

class ExamPredictionDataset(Dataset):
    def __init__(self, embeddings, features, labels):
        self.X = torch.tensor(
            np.concatenate([embeddings, features], axis=1), dtype=torch.float32
        )
        self.y_appear = torch.tensor(labels["appeared"], dtype=torch.float32)
        self.y_qs = torch.tensor(labels["num_qs"], dtype=torch.float32)
        self.y_diff = torch.tensor(labels["difficulty"], dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y_appear[idx], self.y_qs[idx], self.y_diff[idx]


# ================================================================
# MODEL ARCHITECTURE
# ================================================================

class PrajnaSLM(nn.Module):
    """
    Small Language Model for exam topic prediction.
    Input: 384 (embedding) + 15 (features) = 399 dims
    Output: P(appear), expected_questions, difficulty_class
    """

    def __init__(self, embed_dim=384, feat_dim=15, hidden_dims=(256, 128, 64), dropout=0.2):
        super().__init__()

        input_dim = embed_dim + feat_dim

        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h),
                nn.LayerNorm(h),
                nn.GELU(),
                nn.Dropout(dropout),
            ])
            prev_dim = h
        self.backbone = nn.Sequential(*layers)

        self.appear_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 16), nn.GELU(),
            nn.Linear(16, 1), nn.Sigmoid(),
        )
        self.questions_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 16), nn.GELU(),
            nn.Linear(16, 1), nn.ReLU(),
        )
        self.difficulty_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 16), nn.GELU(),
            nn.Linear(16, 3),
        )

    def forward(self, x):
        shared = self.backbone(x)
        p_appear = self.appear_head(shared).squeeze(-1)
        exp_qs = self.questions_head(shared).squeeze(-1)
        difficulty = self.difficulty_head(shared)
        return p_appear, exp_qs, difficulty

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ================================================================
# TRAINING DATA BUILDER
# ================================================================

def build_training_data(db_path="data/exam.db", exam=None,
                        train_years=range(2010, 2024), level="chapter"):
    """
    Build (X, y) for all (topic, year) pairs.
    For each target_year: features from data before it, labels from actual paper.
    """
    full_df = get_questions_df(db_path)
    if exam:
        full_df = full_df[full_df["exam"] == exam]

    cross_df = get_questions_df(db_path)

    print("Loading sentence-transformer (all-MiniLM-L6-v2)...")
    st_model = SentenceTransformer("all-MiniLM-L6-v2")

    group_col = "topic" if level == "chapter" else "micro_topic"

    all_topics = sorted(full_df[group_col].unique())
    topic_subjects = {}
    for _, row in full_df.drop_duplicates(group_col).iterrows():
        topic_subjects[row[group_col]] = row["subject"]

    print(f"Computing embeddings for {len(all_topics)} topics...")
    emb_array = st_model.encode(all_topics, show_progress_bar=True, batch_size=64)
    topic_embeddings = {t: emb_array[i] for i, t in enumerate(all_topics)}

    cross_counts = {}
    for topic in all_topics:
        exams = cross_df[cross_df[group_col] == topic]["exam"].nunique()
        cross_counts[topic] = min(exams / 3.0, 1.0)

    all_embeddings, all_features = [], []
    all_appeared, all_num_qs, all_difficulty = [], [], []
    all_topic_names = []

    for target_year in train_years:
        train_df = full_df[full_df["year"] < target_year]
        actual_df = full_df[full_df["year"] == target_year]
        if actual_df.empty:
            continue

        actual_topics = set(actual_df[group_col].unique())
        actual_qs = actual_df.groupby(group_col).size().to_dict()
        actual_diff = actual_df.groupby(group_col)["difficulty"].mean().to_dict()

        min_year = int(train_df["year"].min()) if not train_df.empty else target_year - 10
        max_year = int(train_df["year"].max()) if not train_df.empty else target_year - 1

        for topic in all_topics:
            subject = topic_subjects.get(topic, "Physics")

            feat = extract_features_for_year(
                train_df, topic, subject, target_year, min_year, max_year
            )
            feat[11] = cross_counts.get(topic, 0.0)

            appeared = 1.0 if topic in actual_topics else 0.0
            num_qs = float(actual_qs.get(topic, 0))

            raw_diff = actual_diff.get(topic, 3.0)
            if raw_diff <= 2.0:
                diff_class = 0
            elif raw_diff <= 3.5:
                diff_class = 1
            else:
                diff_class = 2

            all_embeddings.append(topic_embeddings[topic])
            all_features.append(feat)
            all_appeared.append(appeared)
            all_num_qs.append(num_qs)
            all_difficulty.append(diff_class)
            all_topic_names.append(topic)

    pos = sum(1 for a in all_appeared if a > 0)
    neg = sum(1 for a in all_appeared if a == 0)
    print(f"Built {len(all_embeddings)} training samples ({pos} positive, {neg} negative)")

    embeddings = np.array(all_embeddings, dtype=np.float32)
    features = np.array(all_features, dtype=np.float32)
    labels = {
        "appeared": np.array(all_appeared, dtype=np.float32),
        "num_qs": np.array(all_num_qs, dtype=np.float32),
        "difficulty": np.array(all_difficulty, dtype=np.int64),
    }

    return embeddings, features, labels, all_topic_names, topic_embeddings, st_model


# ================================================================
# TRAINING LOOP
# ================================================================

def train_slm(db_path="data/exam.db", exam=None, level="chapter",
              epochs=150, lr=1e-3, batch_size=128, save_path=None):
    """Train the PRAJNA SLM."""
    if save_path is None:
        exam_tag = (exam or "all").replace(" ", "_").lower()
        save_path = f"models/slm_{exam_tag}_{level}.pt"

    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else "models", exist_ok=True)

    embeddings, features, labels, topic_names, topic_emb_cache, st_model = \
        build_training_data(db_path, exam=exam, train_years=range(2010, 2024), level=level)

    dataset = ExamPredictionDataset(embeddings, features, labels)

    pos_count = labels["appeared"].sum()
    neg_count = len(labels["appeared"]) - pos_count
    pos_weight = torch.tensor([neg_count / (pos_count + 1)])

    model = PrajnaSLM(embed_dim=384, feat_dim=15)
    print(f"\nPRAJNA SLM: {model.count_parameters():,} trainable parameters")
    print(f"  + Sentence-Transformer backbone: ~22M frozen parameters")
    print(f"  = Total: ~{22_000_000 + model.count_parameters():,} parameters\n")

    mse_loss = nn.MSELoss()
    ce_loss = nn.CrossEntropyLoss()

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    history = {"loss": [], "appear_loss": [], "qs_loss": [], "diff_loss": []}
    best_loss = float("inf")

    for epoch in range(epochs):
        model.train()
        epoch_losses = {"total": 0, "appear": 0, "qs": 0, "diff": 0}
        n_batches = 0

        for X, y_appear, y_qs, y_diff in loader:
            optimizer.zero_grad()

            p_appear, pred_qs, pred_diff = model(X)

            weights = torch.where(y_appear == 1, pos_weight, torch.ones(1))
            l_appear = nn.functional.binary_cross_entropy(p_appear, y_appear, weight=weights)

            appear_mask = y_appear > 0
            if appear_mask.sum() > 0:
                l_qs = mse_loss(pred_qs[appear_mask], y_qs[appear_mask])
            else:
                l_qs = torch.tensor(0.0)

            l_diff = ce_loss(pred_diff, y_diff)

            loss = 0.50 * l_appear + 0.35 * l_qs + 0.15 * l_diff

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_losses["total"] += loss.item()
            epoch_losses["appear"] += l_appear.item()
            epoch_losses["qs"] += l_qs.item()
            epoch_losses["diff"] += l_diff.item()
            n_batches += 1

        scheduler.step()

        avg_loss = epoch_losses["total"] / n_batches
        history["loss"].append(avg_loss)
        history["appear_loss"].append(epoch_losses["appear"] / n_batches)
        history["qs_loss"].append(epoch_losses["qs"] / n_batches)
        history["diff_loss"].append(epoch_losses["diff"] / n_batches)

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save({
                "model_state": model.state_dict(),
                "epoch": epoch,
                "loss": best_loss,
                "exam": exam,
                "level": level,
            }, save_path)

        if (epoch + 1) % 25 == 0:
            print(f"  Epoch {epoch+1:3d}/{epochs} | Loss: {avg_loss:.4f} | "
                  f"Appear: {history['appear_loss'][-1]:.4f} | "
                  f"Qs: {history['qs_loss'][-1]:.4f} | "
                  f"Diff: {history['diff_loss'][-1]:.4f}")

    ckpt = torch.load(save_path, weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    print(f"\nBest model saved to {save_path} (epoch {ckpt['epoch']+1}, loss {ckpt['loss']:.4f})")

    emb_cache_path = save_path.replace(".pt", "_embeddings.npz")
    np.savez_compressed(emb_cache_path,
                        topics=list(topic_emb_cache.keys()),
                        embeddings=np.array(list(topic_emb_cache.values())))
    print(f"Topic embeddings cached to {emb_cache_path}")

    return model, history, topic_emb_cache, st_model


# ================================================================
# PREDICTION WITH TRAINED SLM
# ================================================================

def predict_with_slm(db_path="data/exam.db", target_year=2026, exam=None,
                     top_k=50, level="chapter", model_path=None):
    """
    Generate predictions using the trained PRAJNA SLM.
    Drop-in replacement for predict_chapters_v3 / predict_microtopics_v3.
    """
    from analysis.predictor_v3 import (
        _normalize_chapter, _syllabus_status, _predict_format,
        _confidence_score, _subject_balanced_rerank, SUBJECT_QUOTAS, HOLDOUT_YEARS
    )

    if model_path is None:
        exam_tag = (exam or "all").replace(" ", "_").lower()
        model_path = f"models/slm_{exam_tag}_{level}.pt"

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"SLM model not found at {model_path}. Run train_slm() first."
        )

    model = PrajnaSLM(embed_dim=384, feat_dim=15)
    ckpt = torch.load(model_path, weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    emb_cache_path = model_path.replace(".pt", "_embeddings.npz")
    st_model = None
    topic_emb_cache = {}

    if os.path.exists(emb_cache_path):
        data = np.load(emb_cache_path, allow_pickle=True)
        for t, e in zip(data["topics"], data["embeddings"]):
            topic_emb_cache[str(t)] = e

    def get_embedding(topic_name):
        if topic_name in topic_emb_cache:
            return topic_emb_cache[topic_name]
        nonlocal st_model
        if st_model is None:
            st_model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = st_model.encode([topic_name])[0]
        topic_emb_cache[topic_name] = emb
        return emb

    full_df = get_questions_df(db_path)
    train_df = full_df[~full_df["year"].isin(HOLDOUT_YEARS)]
    if exam:
        train_df = train_df[train_df["exam"] == exam]

    cross_df = get_questions_df(db_path)
    cross_df = cross_df[~cross_df["year"].isin(HOLDOUT_YEARS)]

    if train_df.empty:
        return []

    min_year = int(train_df["year"].min())
    max_year = int(train_df["year"].max())

    if level == "chapter":
        groups = train_df.groupby(["subject", "topic"])
    else:
        groups = train_df.groupby(["subject", "topic", "micro_topic"])

    predictions = []
    diff_labels = ["Easy", "Medium", "Hard"]

    for group_key, group in groups:
        if level == "chapter":
            subject, chapter = group_key
            micro_topic = group["micro_topic"].value_counts().index[0]
            topic_for_emb = chapter
        else:
            subject, chapter, micro_topic = group_key
            topic_for_emb = micro_topic

        normalized_chapter = _normalize_chapter(chapter)

        syl_status, syl_gate = _syllabus_status(chapter, exam)
        if syl_gate == 0.0:
            predictions.append({
                "chapter": chapter, "normalized_chapter": normalized_chapter,
                "subject": subject,
                **({"micro_topic": micro_topic} if level == "micro" else {}),
                "appearance_probability": 0.0, "expected_questions": 0,
                "expected_qs_min": 0, "expected_qs_max": 0,
                "likely_formats": [], "likely_difficulty": 0,
                "format_dominance": 0, "confidence": "HIGH",
                "confidence_score": 0.95, "final_score": 0.0,
                "signal_breakdown": {}, "reasons": ["Removed from syllabus"],
                "top_micro_topic": micro_topic if level == "chapter" else "",
                "trend_direction": "REMOVED", "syllabus_status": "REMOVED",
                "total_appearances": 0, "total_questions": 0, "last_appeared": 0,
                "training_years": f"{min_year}-{max_year}", "model": "SLM",
            })
            continue

        years_appeared = sorted(group["year"].unique())
        total_appearances = len(years_appeared)
        qs_per_year = group.groupby("year").size().to_dict()
        question_types = group["question_type"].value_counts().to_dict()
        difficulty_list = group["difficulty"].dropna().tolist()
        recent_diffs = [d for y, d in zip(group["year"], group["difficulty"]) if y >= max_year - 4]

        embedding = get_embedding(topic_for_emb)

        feat = extract_features_for_year(
            train_df, topic_for_emb if level == "micro" else chapter,
            subject, target_year, min_year, max_year
        )
        cross_exams = cross_df[cross_df["topic"] == chapter]["exam"].nunique()
        feat[11] = min(cross_exams / 3.0, 1.0)

        with torch.no_grad():
            X = torch.tensor(
                np.concatenate([embedding, feat]).reshape(1, -1), dtype=torch.float32
            )
            p_appear, pred_qs, pred_diff = model(X)

            app_prob = float(p_appear[0].item()) * syl_gate
            exp_qs_raw = float(pred_qs[0].item())
            diff_probs = torch.softmax(pred_diff[0], dim=0).numpy()
            diff_class = int(diff_probs.argmax())

        app_prob = min(max(app_prob, 0.0), 0.99)
        exp_qs = max(round(exp_qs_raw, 1), 0.0)

        qs_values = list(qs_per_year.values()) if qs_per_year else [1]
        exp_min = max(1, int(np.percentile(qs_values, 25)))
        exp_max = max(exp_min + 1, int(np.percentile(qs_values, 75)))

        likely_types, _, format_dom = _predict_format(question_types, difficulty_list, recent_diffs)
        likely_diff = [1.5, 3.0, 4.5][diff_class]
        cross_score = feat[11]

        slope = feat[6]
        if slope > 0.6:
            trend_dir = "RISING"
        elif slope < 0.4:
            trend_dir = "DECLINING"
        else:
            trend_dir = "STABLE"
        if syl_status == "NEW":
            trend_dir = "NEW"

        wt_conf = 1.0 - feat[8]
        conf_score, conf_label = _confidence_score(
            app_prob, wt_conf, total_appearances, syl_status, feat[2], slope
        )

        max_qs_norm = 8.0 if level == "chapter" else 4.0
        normalized_exp_qs = min(exp_qs / max_qs_norm, 1.0)
        yield_bonus = feat[13]

        final_score = (
            0.45 * app_prob + 0.35 * normalized_exp_qs +
            0.10 * yield_bonus + 0.05 * cross_score + 0.05 * syl_gate
        )

        reasons = []
        if app_prob > 0.6:
            reasons.append(f"SLM predicts {app_prob:.0%} appearance probability")
        if exp_qs >= 2:
            reasons.append(f"Expected ~{exp_qs:.1f} questions (SLM estimate)")
        if trend_dir == "RISING":
            reasons.append("Rising trend in recent years")
        if feat[4] > 0.3:
            reasons.append("Gap signal: overdue for return")
        if not reasons:
            reasons.append("Low SLM confidence")

        signal_breakdown = {
            "slm_appear": {"value": round(app_prob, 3)},
            "slm_exp_qs": {"value": round(exp_qs, 1)},
            "slm_difficulty": {"value": diff_labels[diff_class]},
            "recency_feat": {"value": round(float(feat[1]), 3)},
            "gap_feat": {"value": round(float(feat[4]), 3)},
            "trend_feat": {"value": round(float(feat[6]), 3)},
            "yield_feat": {"value": round(float(feat[13]), 3)},
            "cross_exam": {"value": round(cross_score, 3)},
        }

        pred = {
            "chapter": chapter, "normalized_chapter": normalized_chapter,
            "subject": subject,
            "appearance_probability": round(app_prob, 3),
            "expected_questions": round(exp_qs, 1),
            "expected_qs_min": exp_min, "expected_qs_max": exp_max,
            "likely_formats": likely_types, "likely_difficulty": likely_diff,
            "format_dominance": format_dom, "confidence": conf_label,
            "confidence_score": conf_score, "final_score": round(final_score, 4),
            "signal_breakdown": signal_breakdown, "reasons": reasons,
            "top_micro_topic": micro_topic if level == "chapter" else "",
            "trend_direction": trend_dir, "syllabus_status": syl_status,
            "total_appearances": total_appearances,
            "total_questions": len(group),
            "last_appeared": int(max(years_appeared)),
            "training_years": f"{min_year}-{max_year}", "model": "SLM",
        }
        if level == "micro":
            pred["micro_topic"] = micro_topic

        predictions.append(pred)

    predictions.sort(key=lambda x: x["final_score"], reverse=True)

    if level == "chapter":
        seen = set()
        deduped = []
        for p in predictions:
            norm = p["normalized_chapter"].lower()
            if norm not in seen:
                seen.add(norm)
                deduped.append(p)
        predictions = deduped

    active = [p for p in predictions if p["syllabus_status"] != "REMOVED"]
    removed = [p for p in predictions if p["syllabus_status"] == "REMOVED"]

    if exam:
        reranked = _subject_balanced_rerank(active, exam, top_k=top_k)
    else:
        reranked = active[:top_k]

    return reranked + removed


# ================================================================
# BACKTEST SLM
# ================================================================

def backtest_slm(db_path="data/exam.db", test_years=None, exam=None,
                 k=50, level="chapter"):
    """Backtest the SLM against actual papers."""
    from analysis.predictor_v3 import HOLDOUT_YEARS
    import analysis.predictor_v3 as v3_mod

    if test_years is None:
        test_years = [2019, 2020, 2021, 2022, 2023]

    full_df = get_questions_df(db_path)
    if exam:
        full_df = full_df[full_df["exam"] == exam]

    results = []

    for test_year in test_years:
        actual = full_df[full_df["year"] == test_year]
        if actual.empty:
            continue

        group_col = "micro_topic" if level == "micro" else "topic"
        actual_topics = set(actual[group_col].unique())
        actual_qs_map = actual.groupby(group_col).size().to_dict()
        actual_total = len(actual)
        heavy_topics = {t for t, c in actual_qs_map.items() if c >= 3}
        actual_subj_qs = actual.groupby("subject").size().to_dict()

        orig = v3_mod.HOLDOUT_YEARS
        v3_mod.HOLDOUT_YEARS = set(range(test_year, 2030))

        try:
            preds = predict_with_slm(db_path, target_year=test_year, exam=exam,
                                      top_k=k, level=level)
        finally:
            v3_mod.HOLDOUT_YEARS = orig

        if not preds:
            continue

        if level == "micro":
            pred_set = set(p["micro_topic"] for p in preds if p["syllabus_status"] != "REMOVED")
        else:
            pred_set = set(p["chapter"] for p in preds if p["syllabus_status"] != "REMOVED")

        hits = pred_set & actual_topics
        precision = len(hits) / k if k > 0 else 0
        covered_qs = sum(actual_qs_map.get(t, 0) for t in pred_set)
        coverage = covered_qs / actual_total if actual_total > 0 else 0
        heavy_hits = pred_set & heavy_topics
        heavy_recall = len(heavy_hits) / len(heavy_topics) if heavy_topics else 0

        subj_cov = {}
        for s, qs in actual_subj_qs.items():
            if level == "micro":
                pred_subj = set(p["micro_topic"] for p in preds
                               if p["subject"] == s and p["syllabus_status"] != "REMOVED")
            else:
                pred_subj = set(p["chapter"] for p in preds
                               if p["subject"] == s and p["syllabus_status"] != "REMOVED")
            covered = sum(actual_qs_map.get(t, 0) for t in pred_subj)
            subj_cov[s] = round(covered / qs, 3) if qs > 0 else 0

        avg_subj = np.mean(list(subj_cov.values())) if subj_cov else 0
        combined = 0.35 * precision + 0.40 * coverage + 0.15 * heavy_recall + 0.10 * avg_subj

        results.append({
            "test_year": test_year,
            "precision_at_k": round(precision, 3),
            "coverage_at_k": round(coverage, 3),
            "heavy_topic_recall": round(heavy_recall, 3),
            "avg_subject_coverage": round(avg_subj, 3),
            "combined_score": round(combined, 3),
            "questions_covered": covered_qs,
            "actual_questions": actual_total,
            "model": "SLM",
        })

    return results
