"""
PRAJNA Chatbot — RAG-style Q&A on 23,119 exam questions.

Uses sentence-transformer embeddings for semantic search over the question database.
No external LLM API needed — uses template-based answer generation with retrieved context.

Capabilities:
  - "How many questions on thermodynamics in NEET?" → count + year breakdown
  - "What topics are trending in JEE Main?" → rising trend analysis
  - "Compare Physics vs Chemistry difficulty in NEET" → subject comparison
  - "Show me gap topics for NEET 2026" → gap analysis
  - "What's the hardest topic in JEE Advanced?" → difficulty ranking
"""

import os
import re
import numpy as np
import pandas as pd
from collections import Counter
from utils.db import get_questions_df

# Try to import sentence-transformers for semantic search
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    HAS_ST = True
except ImportError:
    HAS_ST = False


# ================================================================
# KNOWLEDGE BASE BUILDER
# ================================================================

class ExamKnowledgeBase:
    """Builds searchable knowledge from the exam database."""

    def __init__(self, db_path="data/exam.db"):
        self.db_path = db_path
        self.df = get_questions_df(db_path)
        self.st_model = None
        self.topic_embeddings = {}
        self.fact_embeddings = None
        self.facts = []

        self._build_facts()

    def _build_facts(self):
        """Pre-compute facts about the dataset for retrieval."""
        df = self.df

        # ── Overall stats ──
        self.facts.append(f"The database contains {len(df)} questions from {df['year'].min()} to {df['year'].max()}.")
        self.facts.append(f"Exams covered: {', '.join(df['exam'].unique())}.")
        for exam in df["exam"].unique():
            edf = df[df["exam"] == exam]
            self.facts.append(
                f"{exam} has {len(edf)} questions across {edf['year'].nunique()} years "
                f"({edf['year'].min()}-{edf['year'].max()})."
            )

        # ── Subject stats ──
        for subject in df["subject"].unique():
            sdf = df[df["subject"] == subject]
            self.facts.append(f"{subject} has {len(sdf)} total questions across all exams.")
            for exam in sdf["exam"].unique():
                sedf = sdf[sdf["exam"] == exam]
                self.facts.append(
                    f"{subject} in {exam}: {len(sedf)} questions, "
                    f"avg difficulty {sedf['difficulty'].mean():.1f}/5."
                )

        # ── Topic-level facts ──
        for (exam, topic), group in df.groupby(["exam", "topic"]):
            years = sorted(group["year"].unique())
            qs_per_year = group.groupby("year").size()
            avg_qs = qs_per_year.mean()
            last_year = max(years)
            recent_3 = len([y for y in years if y >= last_year - 2])
            avg_diff = group["difficulty"].mean()
            types = group["question_type"].value_counts()
            top_type = types.index[0] if len(types) > 0 else "MCQ"

            self.facts.append(
                f"'{topic}' in {exam}: {len(group)} questions across {len(years)} years, "
                f"avg {avg_qs:.1f} qs/year, last seen {last_year}, "
                f"avg difficulty {avg_diff:.1f}/5, most common type: {top_type}."
            )

            # Trend
            if len(years) >= 5:
                recent_avg = qs_per_year.iloc[-3:].mean() if len(qs_per_year) >= 3 else avg_qs
                older_avg = qs_per_year.iloc[:-3].mean() if len(qs_per_year) > 3 else avg_qs
                if recent_avg > older_avg * 1.3:
                    self.facts.append(f"'{topic}' in {exam} is TRENDING UP (recent avg {recent_avg:.1f} vs older {older_avg:.1f}).")
                elif recent_avg < older_avg * 0.7:
                    self.facts.append(f"'{topic}' in {exam} is DECLINING (recent avg {recent_avg:.1f} vs older {older_avg:.1f}).")

            # Gap
            gap = 2026 - last_year
            if gap >= 3:
                self.facts.append(
                    f"'{topic}' in {exam} has NOT appeared in {gap} years (last: {last_year}). "
                    f"Historically appears every {np.mean([years[i+1]-years[i] for i in range(len(years)-1)]):.1f} years."
                )

        # ── Micro-topic facts (top ones only) ──
        micro_counts = df.groupby(["exam", "micro_topic"]).size().reset_index(name="count")
        top_micros = micro_counts.nlargest(100, "count")
        for _, row in top_micros.iterrows():
            mdf = df[(df["exam"] == row["exam"]) & (df["micro_topic"] == row["micro_topic"])]
            self.facts.append(
                f"Micro-topic '{row['micro_topic']}' in {row['exam']}: "
                f"{row['count']} questions, avg difficulty {mdf['difficulty'].mean():.1f}/5."
            )

    def _get_st_model(self):
        if self.st_model is None:
            self.st_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.fact_embeddings = self.st_model.encode(self.facts, show_progress_bar=False)
        return self.st_model

    def search_facts(self, query, top_k=10):
        """Semantic search over pre-computed facts."""
        if not HAS_ST:
            return self._keyword_search(query, top_k)

        model = self._get_st_model()
        q_emb = model.encode([query])
        scores = st_util.cos_sim(q_emb, self.fact_embeddings)[0].numpy()
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.facts[i], float(scores[i])) for i in top_indices]

    def _keyword_search(self, query, top_k=10):
        """Fallback keyword search if sentence-transformers unavailable."""
        query_words = set(query.lower().split())
        scored = []
        for fact in self.facts:
            fact_words = set(fact.lower().split())
            overlap = len(query_words & fact_words)
            if overlap > 0:
                scored.append((fact, overlap / len(query_words)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


# ================================================================
# QUERY HANDLERS
# ================================================================

def _count_query(df, query):
    """Handle 'how many' questions."""
    # Extract exam, subject, topic from query
    exam_match = _detect_exam(query)
    subject_match = _detect_subject(query)
    topic_match = _detect_topic(df, query)

    filtered = df.copy()
    label_parts = []

    if exam_match:
        filtered = filtered[filtered["exam"] == exam_match]
        label_parts.append(exam_match)
    if subject_match:
        filtered = filtered[filtered["subject"] == subject_match]
        label_parts.append(subject_match)
    if topic_match:
        filtered = filtered[filtered["topic"].str.lower().str.contains(topic_match.lower())]
        label_parts.append(f"'{topic_match}'")

    label = " > ".join(label_parts) if label_parts else "all exams"

    total = len(filtered)
    year_range = f"{filtered['year'].min()}-{filtered['year'].max()}" if total > 0 else "N/A"
    by_year = filtered.groupby("year").size().to_dict() if total > 0 else {}

    return {
        "type": "count",
        "answer": f"There are **{total} questions** for {label} ({year_range}).",
        "details": {
            "total": total,
            "label": label,
            "year_range": year_range,
            "by_year": dict(sorted(by_year.items())[-10:]),  # last 10 years
            "by_subject": filtered.groupby("subject").size().to_dict() if total > 0 else {},
        }
    }


def _trend_query(df, query):
    """Handle 'trending / rising / declining' questions."""
    exam_match = _detect_exam(query)
    if exam_match:
        df = df[df["exam"] == exam_match]

    # Calculate trend for each topic
    trends = []
    max_year = df["year"].max()
    for topic, group in df.groupby("topic"):
        qs_per_year = group.groupby("year").size()
        if len(qs_per_year) < 3:
            continue
        recent = qs_per_year[qs_per_year.index >= max_year - 2].mean()
        older = qs_per_year[qs_per_year.index < max_year - 2].mean()
        if older > 0:
            trend_ratio = recent / older
        else:
            trend_ratio = 2.0 if recent > 0 else 0
        trends.append({
            "topic": topic,
            "subject": group["subject"].mode().iloc[0],
            "recent_avg": round(recent, 1),
            "older_avg": round(older, 1),
            "trend_ratio": round(trend_ratio, 2),
            "direction": "RISING" if trend_ratio > 1.3 else "DECLINING" if trend_ratio < 0.7 else "STABLE",
        })

    trends.sort(key=lambda x: -x["trend_ratio"])

    rising = [t for t in trends if t["direction"] == "RISING"][:10]
    declining = [t for t in trends if t["direction"] == "DECLINING"][:10]

    exam_label = exam_match or "all exams"
    answer = f"**Trending topics in {exam_label}:**\n\n"
    answer += "📈 **Rising:**\n"
    for t in rising[:5]:
        answer += f"- {t['topic']} ({t['subject']}): {t['recent_avg']} qs/yr recently vs {t['older_avg']} before\n"
    answer += "\n📉 **Declining:**\n"
    for t in declining[:5]:
        answer += f"- {t['topic']} ({t['subject']}): {t['recent_avg']} qs/yr recently vs {t['older_avg']} before\n"

    return {
        "type": "trend",
        "answer": answer,
        "details": {"rising": rising, "declining": declining},
    }


def _difficulty_query(df, query):
    """Handle difficulty-related questions."""
    exam_match = _detect_exam(query)
    if exam_match:
        df = df[df["exam"] == exam_match]

    topic_diff = df.groupby("topic").agg(
        avg_difficulty=("difficulty", "mean"),
        count=("difficulty", "count"),
        subject=("subject", lambda x: x.mode().iloc[0]),
    ).reset_index()

    topic_diff = topic_diff[topic_diff["count"] >= 5]
    topic_diff = topic_diff.sort_values("avg_difficulty", ascending=False)

    hardest = topic_diff.head(10).to_dict("records")
    easiest = topic_diff.tail(10).to_dict("records")

    exam_label = exam_match or "all exams"
    answer = f"**Difficulty analysis for {exam_label}:**\n\n"
    answer += "🔴 **Hardest topics (avg difficulty/5):**\n"
    for t in hardest[:5]:
        answer += f"- {t['topic']} ({t['subject']}): {t['avg_difficulty']:.1f}/5 ({t['count']} qs)\n"
    answer += "\n🟢 **Easiest topics:**\n"
    for t in easiest[:5]:
        answer += f"- {t['topic']} ({t['subject']}): {t['avg_difficulty']:.1f}/5 ({t['count']} qs)\n"

    return {
        "type": "difficulty",
        "answer": answer,
        "details": {"hardest": hardest, "easiest": easiest},
    }


def _gap_query(df, query):
    """Handle gap/overdue topic questions."""
    exam_match = _detect_exam(query)
    if exam_match:
        df = df[df["exam"] == exam_match]

    target_year = 2026
    gap_topics = []

    for topic, group in df.groupby("topic"):
        years = sorted(group["year"].unique())
        last = max(years)
        gap = target_year - last
        if gap >= 2 and len(years) >= 3:
            avg_gap = np.mean([years[i+1] - years[i] for i in range(len(years)-1)])
            gap_topics.append({
                "topic": topic,
                "subject": group["subject"].mode().iloc[0],
                "last_appeared": last,
                "gap_years": gap,
                "avg_gap": round(avg_gap, 1),
                "overdue_ratio": round(gap / avg_gap, 1) if avg_gap > 0 else 0,
                "total_qs": len(group),
            })

    gap_topics.sort(key=lambda x: -x["overdue_ratio"])

    exam_label = exam_match or "all exams"
    answer = f"**Gap topics for {exam_label} (overdue for {target_year}):**\n\n"
    for t in gap_topics[:10]:
        answer += (
            f"- **{t['topic']}** ({t['subject']}): last seen {t['last_appeared']} "
            f"({t['gap_years']}yr gap, usually appears every {t['avg_gap']}yr, "
            f"overdue ratio: {t['overdue_ratio']}x)\n"
        )

    return {
        "type": "gap",
        "answer": answer,
        "details": {"gap_topics": gap_topics[:20]},
    }


def _compare_query(df, query):
    """Handle comparison questions."""
    exam_match = _detect_exam(query)
    if exam_match:
        df = df[df["exam"] == exam_match]

    subjects = df["subject"].unique()
    comparison = []
    for s in subjects:
        sdf = df[df["subject"] == s]
        comparison.append({
            "subject": s,
            "total_questions": len(sdf),
            "avg_difficulty": round(sdf["difficulty"].mean(), 2),
            "topics_count": sdf["topic"].nunique(),
            "micro_topics": sdf["micro_topic"].nunique(),
            "years_covered": sdf["year"].nunique(),
        })

    comparison.sort(key=lambda x: -x["total_questions"])

    exam_label = exam_match or "all exams"
    answer = f"**Subject comparison for {exam_label}:**\n\n"
    for c in comparison:
        answer += (
            f"- **{c['subject']}**: {c['total_questions']} questions, "
            f"{c['topics_count']} topics, avg difficulty {c['avg_difficulty']}/5\n"
        )

    return {
        "type": "compare",
        "answer": answer,
        "details": {"subjects": comparison},
    }


def _topic_detail_query(df, query, topic_name):
    """Detailed info about a specific topic."""
    exam_match = _detect_exam(query)
    if exam_match:
        df = df[df["exam"] == exam_match]

    tdf = df[df["topic"].str.lower().str.contains(topic_name.lower())]
    if tdf.empty:
        # Try micro-topic
        tdf = df[df["micro_topic"].str.lower().str.contains(topic_name.lower())]

    if tdf.empty:
        return {"type": "topic", "answer": f"No data found for '{topic_name}'.", "details": {}}

    actual_topic = tdf["topic"].mode().iloc[0]
    years = sorted(tdf["year"].unique())
    qs_per_year = tdf.groupby("year").size().to_dict()
    types = tdf["question_type"].value_counts().to_dict()
    micros = tdf["micro_topic"].value_counts().head(5).to_dict()

    answer = f"**{actual_topic}** "
    if exam_match:
        answer += f"in {exam_match}:\n\n"
    else:
        answer += f"(across all exams):\n\n"

    answer += f"- **Total questions:** {len(tdf)}\n"
    answer += f"- **Years appeared:** {len(years)} ({min(years)}-{max(years)})\n"
    answer += f"- **Avg questions/year:** {len(tdf)/len(years):.1f}\n"
    answer += f"- **Avg difficulty:** {tdf['difficulty'].mean():.1f}/5\n"
    answer += f"- **Question types:** {', '.join(f'{k}: {v}' for k, v in list(types.items())[:3])}\n"
    answer += f"- **Top micro-topics:** {', '.join(list(micros.keys())[:5])}\n"

    recent_qs = {y: c for y, c in qs_per_year.items() if y >= max(years) - 4}
    if recent_qs:
        answer += f"- **Recent years:** {recent_qs}\n"

    return {
        "type": "topic",
        "answer": answer,
        "details": {
            "topic": actual_topic,
            "total": len(tdf),
            "years": years,
            "qs_per_year": qs_per_year,
            "types": types,
            "micro_topics": micros,
            "avg_difficulty": round(tdf["difficulty"].mean(), 2),
        }
    }


# ================================================================
# INTENT DETECTION HELPERS
# ================================================================

def _detect_exam(query):
    q = query.lower()
    if "neet" in q:
        return "NEET"
    if "jee advanced" in q or "jee adv" in q or "iit" in q:
        return "JEE Advanced"
    if "jee main" in q or "jee mains" in q:
        return "JEE Main"
    if "jee" in q:
        return "JEE Main"
    return None


def _detect_subject(query):
    q = query.lower()
    if "physics" in q or "phy" in q:
        return "Physics"
    if "chemistry" in q or "chem" in q:
        return "Chemistry"
    if "biology" in q or "bio" in q:
        return "Biology"
    if "math" in q or "maths" in q:
        return "Mathematics"
    return None


def _detect_topic(df, query):
    """Try to find a topic name mentioned in the query."""
    q = query.lower()
    all_topics = df["topic"].unique()
    best_match = None
    best_len = 0
    for topic in all_topics:
        if topic.lower() in q and len(topic) > best_len:
            best_match = topic
            best_len = len(topic)
    return best_match


# ================================================================
# MAIN CHATBOT
# ================================================================

class PrajnaChatbot:
    """
    PRAJNA Chatbot — answers questions about 23,119 exam questions.

    Uses intent detection + semantic search for retrieval-augmented answers.
    """

    def __init__(self, db_path="data/exam.db"):
        self.db_path = db_path
        self.df = get_questions_df(db_path)
        self.kb = ExamKnowledgeBase(db_path)

    def ask(self, query):
        """
        Process a user query and return a structured response.

        Returns dict with: type, answer (markdown), details (for charts/tables)
        """
        q = query.lower().strip()

        # ── Intent routing ──

        # Count queries
        if any(w in q for w in ["how many", "count", "total", "number of"]):
            return _count_query(self.df, query)

        # Trend queries
        if any(w in q for w in ["trend", "rising", "declining", "hot", "cold", "popular"]):
            return _trend_query(self.df, query)

        # Difficulty queries
        if any(w in q for w in ["difficult", "hardest", "easiest", "hard", "easy", "tough"]):
            return _difficulty_query(self.df, query)

        # Gap queries
        if any(w in q for w in ["gap", "overdue", "missing", "not appeared", "absent"]):
            return _gap_query(self.df, query)

        # Comparison queries
        if any(w in q for w in ["compare", "vs", "versus", "comparison", "difference"]):
            return _compare_query(self.df, query)

        # Topic-specific queries
        topic_match = _detect_topic(self.df, query)
        if topic_match:
            return _topic_detail_query(self.df, query, topic_match)

        # ── Fallback: semantic search over facts ──
        results = self.kb.search_facts(query, top_k=5)
        if results and results[0][1] > 0.3:
            answer = "Based on the exam database:\n\n"
            for fact, score in results:
                if score > 0.25:
                    answer += f"- {fact}\n"
            return {"type": "search", "answer": answer, "details": {"results": results}}

        return {
            "type": "unknown",
            "answer": (
                "I can help you with:\n"
                "- **Counts**: 'How many Physics questions in NEET?'\n"
                "- **Trends**: 'What topics are trending in JEE Main?'\n"
                "- **Difficulty**: 'What are the hardest topics in NEET?'\n"
                "- **Gaps**: 'Which topics are overdue in NEET 2026?'\n"
                "- **Comparisons**: 'Compare Physics vs Chemistry in NEET'\n"
                "- **Topic details**: 'Tell me about Thermodynamics in JEE'\n"
            ),
            "details": {},
        }
