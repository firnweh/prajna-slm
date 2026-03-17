"""
Deep topic analysis module — provides detailed per-topic breakdowns,
timeline analysis, and syllabus coverage mapping.
"""

import pandas as pd
from utils.db import get_questions_df
from data.syllabus import NEET_SYLLABUS, JEE_SYLLABUS


def get_topic_deep_dive(db_path, topic_name, exam=None):
    """Get comprehensive analysis for a single topic."""
    df = get_questions_df(db_path)
    if exam:
        df = df[df["exam"] == exam]

    mask = (df["topic"] == topic_name) | (df["micro_topic"] == topic_name)
    topic_df = df[mask]

    if topic_df.empty:
        return None

    # Year-wise breakdown
    year_counts = topic_df.groupby("year").size().reset_index(name="count")

    # Difficulty trend over years
    diff_by_year = topic_df.groupby("year")["difficulty"].mean().reset_index()

    # Subtopic breakdown
    subtopic_counts = topic_df.groupby("micro_topic").agg(
        count=("id", "size"),
        years=("year", lambda x: sorted(x.unique().tolist())),
        avg_difficulty=("difficulty", "mean"),
        first_appeared=("year", "min"),
        last_appeared=("year", "max"),
    ).reset_index().sort_values("count", ascending=False)

    # Question type distribution
    type_dist = topic_df["question_type"].value_counts().to_dict()

    # All questions for this topic
    questions = topic_df[[
        "id", "exam", "year", "shift", "micro_topic",
        "question_text", "question_type", "difficulty", "answer",
    ]].sort_values("year", ascending=False)

    # Cross-exam presence
    exam_counts = topic_df.groupby("exam").size().to_dict()

    return {
        "topic": topic_name,
        "total_questions": len(topic_df),
        "year_counts": year_counts,
        "difficulty_trend": diff_by_year,
        "subtopic_counts": subtopic_counts,
        "type_distribution": type_dist,
        "questions": questions,
        "exam_counts": exam_counts,
        "first_year": int(topic_df["year"].min()),
        "last_year": int(topic_df["year"].max()),
        "subjects": topic_df["subject"].unique().tolist(),
    }


def get_topic_tree(db_path, exam=None):
    """Build hierarchical tree: subject > topic > micro_topic with counts."""
    df = get_questions_df(db_path)
    if exam:
        df = df[df["exam"] == exam]

    tree = []
    for (subject, topic, micro_topic), group in df.groupby(["subject", "topic", "micro_topic"]):
        tree.append({
            "subject": subject,
            "topic": topic,
            "micro_topic": micro_topic,
            "count": len(group),
            "years": sorted(group["year"].unique().tolist()),
            "avg_difficulty": round(group["difficulty"].mean(), 1),
        })

    return pd.DataFrame(tree)


def get_syllabus_coverage(db_path, exam_name):
    """Map database topics to official syllabus and compute coverage."""
    df = get_questions_df(db_path)
    if exam_name in ("NEET",):
        syllabus = NEET_SYLLABUS
    else:
        syllabus = JEE_SYLLABUS

    # Filter to relevant exam
    exam_df = df[df["exam"].str.contains(exam_name.split()[0], case=False, na=False)]

    coverage = []
    for subject, chapters in syllabus.items():
        for chapter, topics in chapters.items():
            chapter_lower = chapter.lower()
            # Match database topics to syllabus chapters using fuzzy keyword matching
            matched_qs = exam_df[
                exam_df["topic"].str.lower().str.contains(
                    _make_pattern(chapter_lower), case=False, na=False, regex=True
                )
                | exam_df["micro_topic"].str.lower().str.contains(
                    _make_pattern(chapter_lower), case=False, na=False, regex=True
                )
            ]

            for st in topics:
                st_lower = st.lower()
                st_matched = exam_df[
                    exam_df["micro_topic"].str.lower().str.contains(
                        _make_pattern(st_lower), case=False, na=False, regex=True
                    )
                    | exam_df["question_text"].str.lower().str.contains(
                        _make_pattern(st_lower), case=False, na=False, regex=True
                    )
                ]
                q_count = len(st_matched)
                years = sorted(st_matched["year"].unique().tolist()) if q_count > 0 else []

                coverage.append({
                    "subject": subject,
                    "chapter": chapter,
                    "subtopic": st,
                    "questions_found": q_count,
                    "years_appeared": years,
                    "last_appeared": max(years) if years else 0,
                    "frequency": q_count,
                })

    return pd.DataFrame(coverage)


def _make_pattern(text):
    """Create a regex pattern from syllabus text for fuzzy matching."""
    # Extract key words (>3 chars) and join with .*
    words = [w for w in text.split() if len(w) > 3]
    if not words:
        words = text.split()
    # Match if any key word appears
    return "|".join(words[:3])


def get_subject_weightage_timeline(db_path, exam=None):
    """Get subject weightage as percentage over time."""
    df = get_questions_df(db_path)
    if exam:
        df = df[df["exam"] == exam]

    counts = df.groupby(["year", "subject"]).size().unstack(fill_value=0)
    totals = counts.sum(axis=1)
    pct = counts.div(totals, axis=0) * 100
    return pct.reset_index()


def get_difficulty_evolution(db_path, exam=None):
    """Get average difficulty per subject per year."""
    df = get_questions_df(db_path)
    if exam:
        df = df[df["exam"] == exam]

    return df.groupby(["year", "subject"])["difficulty"].mean().unstack().reset_index()
