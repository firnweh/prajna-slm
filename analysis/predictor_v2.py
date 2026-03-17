"""
Exam Predictor v2 — Multi-signal scoring engine with confidence,
marks prediction, question type forecasting, and explainability.

Signals:
  1. Recency-weighted frequency (exponential decay)
  2. Trend slope (rising/stable/declining via linear regression)
  3. Gap return probability (longer gap → higher return chance)
  4. Cycle match (periodic reappearance detection)
  5. Marks weightage stability
  6. Cross-exam signal
  7. Chapter spread need (blueprint coverage)
  8. Syllabus status gate (multiplicative)

Outputs per topic:
  - appearance_probability (0-1)
  - expected_marks (min, mid, max)
  - likely_question_types (ranked)
  - likely_difficulty (1-5)
  - confidence (HIGH/MEDIUM/LOW/SPECULATIVE)
  - trend_direction (RISING/STABLE/DECLINING/NEW)
  - syllabus_status (RETAINED/MODIFIED/NEW/REMOVED)
  - signal_breakdown (per-signal contribution)
  - reasons (human-readable)
"""

import numpy as np
import pandas as pd
from collections import Counter
from utils.db import get_questions_df
from analysis.trend_analyzer import detect_cycles
from data.historical_events import NEET_2024_REMOVED, NEET_2024_ADDED, JEE_2024_REMOVED

HOLDOUT_YEARS = {2024, 2025, 2026}

WEIGHTS = {
    "recency_weighted_freq": 0.25,
    "trend_slope":           0.15,
    "gap_return":            0.15,
    "cycle_match":           0.10,
    "marks_stability":       0.10,
    "cross_exam":            0.08,
    "chapter_spread":        0.07,
    "difficulty_signal":     0.05,
    "format_predictability": 0.05,
}

DECAY_FACTOR = 1.5  # Exponential decay for recency weighting


def _syllabus_status(topic, micro_topic, exam):
    """Determine syllabus status for a topic."""
    topic_lower = (topic or "").lower()
    micro_lower = (micro_topic or "").lower()
    combined = f"{topic_lower} {micro_lower}"

    removed_list = NEET_2024_REMOVED if "NEET" in (exam or "") else JEE_2024_REMOVED
    added_list = NEET_2024_ADDED if "NEET" in (exam or "") else []

    for r in removed_list:
        if any(w in combined for w in r.lower().split() if len(w) > 3):
            return "REMOVED", 0.0

    for a in added_list:
        if any(w in combined for w in a.lower().split() if len(w) > 3):
            return "NEW", 0.5

    # Check for modification signals (topic exists but scope changed)
    # For now, default to RETAINED
    return "RETAINED", 1.0


def _recency_weighted_freq(years, target_year, decay=DECAY_FACTOR):
    """Compute recency-weighted frequency — recent years matter more."""
    if not years:
        return 0.0
    weights = []
    for y in years:
        distance = target_year - y
        if distance > 0:
            weights.append(1.0 / (distance ** decay))
        else:
            weights.append(1.0)
    return sum(weights)


def _trend_slope(year_counts, recent_window=10):
    """Compute trend slope using linear regression on recent years."""
    if len(year_counts) < 3:
        return 0.0, "NEW"

    # Use last N years
    recent = year_counts.tail(recent_window)
    if len(recent) < 3:
        recent = year_counts

    x = recent["year"].values.astype(float)
    y = recent["count"].values.astype(float)

    # Simple linear regression
    n = len(x)
    x_mean = x.mean()
    y_mean = y.mean()
    numerator = sum((x - x_mean) * (y - y_mean))
    denominator = sum((x - x_mean) ** 2)

    if denominator == 0:
        return 0.0, "STABLE"

    slope = numerator / denominator

    if slope > 0.15:
        direction = "RISING"
    elif slope < -0.15:
        direction = "DECLINING"
    else:
        direction = "STABLE"

    return slope, direction


def _gap_return_probability(gap, mean_gap, total_appearances):
    """Probability of return based on gap vs historical pattern."""
    if total_appearances < 2:
        return 0.3  # Low data, moderate default

    if mean_gap == 0:
        return 0.5

    # If current gap exceeds mean gap, probability increases
    ratio = gap / mean_gap
    if ratio >= 1.5:
        return min(0.9, 0.5 + (ratio - 1.0) * 0.2)
    elif ratio >= 1.0:
        return 0.5
    else:
        return max(0.1, 0.5 - (1.0 - ratio) * 0.3)


def _marks_stability(marks_list):
    """How stable is the marks allocation for this topic?"""
    if len(marks_list) < 2:
        return 0.5, 0.0

    mean_marks = np.mean(marks_list)
    if mean_marks == 0:
        return 0.5, 0.0

    std_marks = np.std(marks_list)
    cv = std_marks / mean_marks  # Coefficient of variation
    stability = max(0, 1.0 - cv)
    return stability, cv


def _confidence_score(total_appearances, appeared_in_last_5yr, marks_stability, syllabus_status):
    """Compute confidence score separate from prediction score."""
    data_richness = min(total_appearances / 10, 1.0)
    recency_conf = 1.0 if appeared_in_last_5yr else 0.5
    syllabus_certainty = {"RETAINED": 1.0, "MODIFIED": 0.7, "NEW": 0.3, "REMOVED": 0.0}.get(syllabus_status, 0.5)

    raw = (0.35 * data_richness +
           0.25 * recency_conf +
           0.20 * marks_stability +
           0.20 * syllabus_certainty)

    if raw > 0.75:
        label = "HIGH"
    elif raw > 0.50:
        label = "MEDIUM"
    elif raw > 0.25:
        label = "LOW"
    else:
        label = "SPECULATIVE"

    return round(raw, 3), label


def predict_topics_v2(db_path="data/exam.db", target_year=2026, exam=None):
    """Enhanced prediction engine with multi-signal scoring."""
    full_df = get_questions_df(db_path)

    # Training data: exclude holdout years
    df = full_df[~full_df["year"].isin(HOLDOUT_YEARS)]
    if exam:
        df = df[df["exam"] == exam]

    if df.empty:
        return []

    max_year = df["year"].max()
    min_year = df["year"].min()
    year_span = max_year - min_year + 1

    # Cross-exam reference (without holdout)
    cross_df = full_df[~full_df["year"].isin(HOLDOUT_YEARS)]

    # Cycle detection
    cycles = detect_cycles(db_path, exclude_years=HOLDOUT_YEARS)
    cycle_map = {c["micro_topic"]: c for c in cycles}

    # Per-topic aggregation
    topic_groups = df.groupby(["subject", "topic", "micro_topic"])

    # All unique topics in the exam for chapter spread
    all_topics_set = set(df["topic"].unique())
    total_topics = len(all_topics_set)

    # Year-level topic counts for trend calculation
    year_topic_counts = df.groupby(["micro_topic", "year"]).size().reset_index(name="count")

    predictions = []

    for (subject, topic, micro_topic), group in topic_groups:
        years_appeared = sorted(group["year"].unique())
        total_appearances = len(years_appeared)
        total_questions = len(group)
        marks_list = group["marks"].dropna().tolist()
        difficulty_list = group["difficulty"].dropna().tolist()
        question_types = group["question_type"].value_counts().to_dict()

        # --- Syllabus gate ---
        syl_status, syl_gate = _syllabus_status(topic, micro_topic, exam)
        if syl_gate == 0.0:
            # REMOVED topic — skip or include with zero score
            predictions.append(_make_removed_prediction(
                subject, topic, micro_topic, total_appearances, years_appeared, min_year, max_year
            ))
            continue

        reasons = []
        signal_breakdown = {}

        # --- Signal 1: Recency-weighted frequency ---
        rwf = _recency_weighted_freq(years_appeared, target_year)
        # Normalize: compare against max possible (appeared every year recently)
        max_rwf = _recency_weighted_freq(list(range(min_year, max_year + 1)), target_year)
        rwf_norm = min(rwf / (max_rwf + 0.01), 1.0)
        signal_breakdown["recency_weighted_freq"] = {
            "value": round(rwf_norm, 3), "weight": WEIGHTS["recency_weighted_freq"],
            "contribution": round(rwf_norm * WEIGHTS["recency_weighted_freq"], 4),
        }
        if rwf_norm > 0.3:
            reasons.append(f"Strong recency-weighted frequency ({total_appearances} appearances, recent ones weighted higher)")

        # --- Signal 2: Trend slope ---
        topic_year_df = year_topic_counts[year_topic_counts["micro_topic"] == micro_topic]
        # Fill missing years with 0
        all_years = pd.DataFrame({"year": range(min_year, max_year + 1)})
        topic_year_full = all_years.merge(topic_year_df[["year", "count"]], on="year", how="left").fillna(0)
        slope, trend_dir = _trend_slope(topic_year_full)
        slope_norm = min(max((slope + 0.5) / 1.0, 0), 1.0)  # Normalize slope to 0-1
        signal_breakdown["trend_slope"] = {
            "value": round(slope_norm, 3), "weight": WEIGHTS["trend_slope"],
            "contribution": round(slope_norm * WEIGHTS["trend_slope"], 4),
        }
        if trend_dir == "RISING":
            reasons.append(f"Rising trend — frequency increasing over recent years")
        elif trend_dir == "DECLINING":
            reasons.append(f"Declining trend — appeared less frequently recently")

        # --- Signal 3: Gap return probability ---
        gap = target_year - max(years_appeared)
        gaps_between = [years_appeared[i+1] - years_appeared[i] for i in range(len(years_appeared)-1)]
        mean_gap = np.mean(gaps_between) if gaps_between else year_span
        gap_prob = _gap_return_probability(gap, mean_gap, total_appearances)
        signal_breakdown["gap_return"] = {
            "value": round(gap_prob, 3), "weight": WEIGHTS["gap_return"],
            "contribution": round(gap_prob * WEIGHTS["gap_return"], 4),
        }
        if gap >= 3:
            reasons.append(f"Gap bonus: not seen in {gap} years (avg gap: {mean_gap:.1f}yr)")

        # --- Signal 4: Cycle match ---
        cycle_score = 0.0
        if micro_topic in cycle_map:
            cycle = cycle_map[micro_topic]
            cycle_len = cycle["estimated_cycle_years"]
            if cycle_len > 0:
                years_since = target_year - max(years_appeared)
                remainder = years_since % cycle_len
                if remainder == 0:
                    cycle_score = 1.0
                    reasons.append(f"Cycle match: ~{cycle_len}-year cycle, due in {target_year}")
                elif remainder <= 1 or (cycle_len - remainder) <= 1:
                    cycle_score = 0.5
                    reasons.append(f"Near cycle: ~{cycle_len}-year pattern")
        signal_breakdown["cycle_match"] = {
            "value": round(cycle_score, 3), "weight": WEIGHTS["cycle_match"],
            "contribution": round(cycle_score * WEIGHTS["cycle_match"], 4),
        }

        # --- Signal 5: Marks stability ---
        m_stability, cv = _marks_stability(marks_list)
        signal_breakdown["marks_stability"] = {
            "value": round(m_stability, 3), "weight": WEIGHTS["marks_stability"],
            "contribution": round(m_stability * WEIGHTS["marks_stability"], 4),
        }
        if m_stability > 0.7:
            reasons.append(f"Stable marks allocation (CV={cv:.2f})")

        # --- Signal 6: Cross-exam signal ---
        micro_cross = cross_df[cross_df["micro_topic"] == micro_topic]
        exams_present = micro_cross["exam"].unique()
        cross_score = min(len(exams_present) / 3, 1.0)
        signal_breakdown["cross_exam"] = {
            "value": round(cross_score, 3), "weight": WEIGHTS["cross_exam"],
            "contribution": round(cross_score * WEIGHTS["cross_exam"], 4),
        }
        if len(exams_present) > 1:
            reasons.append(f"Cross-exam: appears in {', '.join(exams_present)}")

        # --- Signal 7: Chapter spread need ---
        # How much does the exam typically need this chapter represented?
        topic_paper_coverage = df[df["topic"] == topic].groupby(["year", "shift"]).size()
        papers_with_topic = len(topic_paper_coverage)
        total_papers = len(df.groupby(["year", "shift"]))
        spread_need = min(papers_with_topic / (total_papers + 0.01), 1.0)
        signal_breakdown["chapter_spread"] = {
            "value": round(spread_need, 3), "weight": WEIGHTS["chapter_spread"],
            "contribution": round(spread_need * WEIGHTS["chapter_spread"], 4),
        }

        # --- Signal 8: Difficulty signal ---
        if difficulty_list:
            recent_diff = [d for y, d in zip(group["year"], group["difficulty"]) if y >= max_year - 5]
            older_diff = [d for y, d in zip(group["year"], group["difficulty"]) if y < max_year - 5]
            if recent_diff and older_diff:
                diff_shift = np.mean(recent_diff) - np.mean(older_diff)
                # Topics getting harder may be emphasized by examiners
                diff_signal = min(max((diff_shift + 1) / 2, 0), 1.0)
            else:
                diff_signal = 0.5
        else:
            diff_signal = 0.5
        signal_breakdown["difficulty_signal"] = {
            "value": round(diff_signal, 3), "weight": WEIGHTS["difficulty_signal"],
            "contribution": round(diff_signal * WEIGHTS["difficulty_signal"], 4),
        }

        # --- Signal 9: Format predictability ---
        if question_types:
            most_common_count = max(question_types.values())
            total_type_count = sum(question_types.values())
            format_pred = most_common_count / total_type_count
        else:
            format_pred = 0.5
        signal_breakdown["format_predictability"] = {
            "value": round(format_pred, 3), "weight": WEIGHTS["format_predictability"],
            "contribution": round(format_pred * WEIGHTS["format_predictability"], 4),
        }

        # --- Composite score ---
        raw_score = sum(s["contribution"] for s in signal_breakdown.values())
        final_score = raw_score * syl_gate  # Apply syllabus gate

        # --- Marks prediction ---
        if marks_list:
            marks_min = int(np.percentile(marks_list, 25))
            marks_mid = int(np.median(marks_list))
            marks_max = int(np.percentile(marks_list, 75))
        else:
            marks_min, marks_mid, marks_max = 4, 4, 4

        # --- Question type prediction ---
        type_ranked = sorted(question_types.items(), key=lambda x: x[1], reverse=True)
        likely_types = [t[0] for t in type_ranked[:3]]
        if not likely_types:
            likely_types = ["MCQ_single"]

        # --- Difficulty prediction (recency-weighted) ---
        if difficulty_list:
            recent_weights = [1.0 / ((target_year - y) ** 0.5 + 1) for y in group["year"]]
            weighted_diff = np.average(group["difficulty"].values, weights=recent_weights)
            likely_diff = round(float(weighted_diff), 1)
        else:
            likely_diff = 3.0

        # --- Confidence ---
        appeared_last_5 = any(y >= max_year - 5 for y in years_appeared)
        conf_score, conf_label = _confidence_score(
            total_appearances, appeared_last_5, m_stability, syl_status
        )

        if not reasons:
            reasons.append("Low signal — limited historical data")

        predictions.append({
            "subject": subject,
            "topic": topic,
            "micro_topic": micro_topic,
            "appearance_probability": round(min(final_score * 2, 0.99), 3),  # Scale to 0-1 range
            "score": round(final_score, 4),
            "expected_marks": {"min": marks_min, "mid": marks_mid, "max": marks_max},
            "likely_question_types": likely_types,
            "likely_difficulty": likely_diff,
            "trend_direction": trend_dir,
            "syllabus_status": syl_status,
            "confidence": conf_label,
            "confidence_score": conf_score,
            "signal_breakdown": signal_breakdown,
            "reasons": reasons,
            "total_appearances": total_appearances,
            "total_questions": total_questions,
            "last_appeared": max(years_appeared),
            "training_years": f"{min_year}–{max_year}",
        })

    predictions.sort(key=lambda x: x["score"], reverse=True)
    return predictions


def _make_removed_prediction(subject, topic, micro_topic, total_appearances, years, min_year, max_year):
    """Create a zero-score prediction for removed topics."""
    return {
        "subject": subject,
        "topic": topic,
        "micro_topic": micro_topic,
        "appearance_probability": 0.0,
        "score": 0.0,
        "expected_marks": {"min": 0, "mid": 0, "max": 0},
        "likely_question_types": [],
        "likely_difficulty": 0,
        "trend_direction": "REMOVED",
        "syllabus_status": "REMOVED",
        "confidence": "HIGH",
        "confidence_score": 0.95,
        "signal_breakdown": {},
        "reasons": ["Topic removed from current syllabus — will not appear"],
        "total_appearances": total_appearances,
        "total_questions": 0,
        "last_appeared": max(years) if years else 0,
        "training_years": f"{min_year}–{max_year}",
    }


def backtest(db_path="data/exam.db", test_years=None, exam=None, k=20):
    """
    Backtest the model against actual papers.
    Train on years < test_year, predict for test_year, compare.
    """
    if test_years is None:
        test_years = [2019, 2020, 2021, 2022, 2023]

    full_df = get_questions_df(db_path)
    if exam:
        full_df = full_df[full_df["exam"] == exam]

    results = []

    for test_year in test_years:
        # Actual topics that appeared
        actual = full_df[full_df["year"] == test_year]
        if actual.empty:
            continue
        actual_micros = set(actual["micro_topic"].unique())
        actual_marks_by_topic = actual.groupby("micro_topic")["marks"].sum().to_dict()

        # Predict (temporarily set holdout to include test_year+)
        import analysis.predictor_v2 as self_mod
        orig_holdout = self_mod.HOLDOUT_YEARS
        self_mod.HOLDOUT_YEARS = {y for y in range(test_year, 2030)}

        preds = predict_topics_v2(db_path, target_year=test_year, exam=exam)

        self_mod.HOLDOUT_YEARS = orig_holdout

        if not preds:
            continue

        predicted_micros_at_k = set(p["micro_topic"] for p in preds[:k])
        all_predicted_micros = set(p["micro_topic"] for p in preds)

        # Metrics
        hits_at_k = predicted_micros_at_k & actual_micros
        precision_at_k = len(hits_at_k) / k if k > 0 else 0
        recall_at_k = len(hits_at_k) / len(actual_micros) if actual_micros else 0

        # Topic hit rate
        hit_rate = len(all_predicted_micros & actual_micros) / len(actual_micros) if actual_micros else 0

        # Marks coverage: what % of total marks do our top-k predictions cover?
        actual_total_marks = sum(actual_marks_by_topic.values())
        covered_marks = sum(actual_marks_by_topic.get(m, 0) for m in predicted_micros_at_k)
        marks_coverage = covered_marks / actual_total_marks if actual_total_marks > 0 else 0

        results.append({
            "test_year": test_year,
            "actual_topics": len(actual_micros),
            "precision_at_k": round(precision_at_k, 3),
            "recall_at_k": round(recall_at_k, 3),
            "hit_rate": round(hit_rate, 3),
            "marks_coverage": round(marks_coverage, 3),
            "k": k,
            "top_k_hits": len(hits_at_k),
        })

    return results
