"""
Topic Hierarchy Utilities
==========================
Helpers for navigating and aggregating across the
micro_topic → topic → chapter → subject hierarchy.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from ..schemas.prediction import (
    MicroTopicPrediction, TopicPrediction, ChapterPrediction,
    SubjectPrediction, PredictionBatch, WeightageBand, TrendDirection,
)


# ── Weightage band helpers ────────────────────────────────────────────────────

WEIGHTAGE_BAND_ORDER = [
    WeightageBand.NEGLIGIBLE,
    WeightageBand.LOW,
    WeightageBand.MEDIUM,
    WeightageBand.HIGH,
    WeightageBand.VERY_HIGH,
]

WEIGHTAGE_BAND_MIDPOINTS = {
    WeightageBand.NEGLIGIBLE: 0.0,
    WeightageBand.LOW:        0.5,
    WeightageBand.MEDIUM:     2.0,
    WeightageBand.HIGH:       4.0,
    WeightageBand.VERY_HIGH:  6.0,
}


def score_to_band(importance: float) -> WeightageBand:
    if importance >= 0.80:  return WeightageBand.VERY_HIGH
    if importance >= 0.60:  return WeightageBand.HIGH
    if importance >= 0.35:  return WeightageBand.MEDIUM
    if importance >= 0.15:  return WeightageBand.LOW
    return WeightageBand.NEGLIGIBLE


def trend_score_to_direction(score: float) -> TrendDirection:
    if score > 0.25:   return TrendDirection.RISING
    if score > 0.05:   return TrendDirection.STABLE
    if score < -0.25:  return TrendDirection.DECLINING
    if score < -0.05:  return TrendDirection.STABLE
    return TrendDirection.VOLATILE


# ── Roll-up aggregation ───────────────────────────────────────────────────────

def aggregate_to_topic(
    micro_predictions: List[MicroTopicPrediction],
    topic: str,
    chapter: str,
    subject: str,
) -> TopicPrediction:
    """
    Roll up micro-topic predictions to a topic-level prediction.
    Uses importance_probability-weighted averaging for most signals.
    """
    if not micro_predictions:
        raise ValueError(f"No micro-topic predictions for topic '{topic}'")

    # Weighted average using importance_probability as weight
    total_weight = sum(m.importance_probability for m in micro_predictions)
    if total_weight == 0:
        total_weight = len(micro_predictions)
        weights = [1.0 / len(micro_predictions)] * len(micro_predictions)
    else:
        weights = [m.importance_probability / total_weight for m in micro_predictions]

    def wavg(attr: str) -> float:
        return sum(getattr(m, attr) * w for m, w in zip(micro_predictions, weights))

    composite_importance = wavg("importance_probability")
    recurrence_score     = wavg("recurrence_score")
    composite_confidence = wavg("confidence_score")
    avg_trend            = wavg("topic_trend_score")

    # Sort by importance descending
    sorted_micro = sorted(micro_predictions, key=lambda m: m.importance_probability, reverse=True)
    top_micros   = [m.micro_topic_name for m in sorted_micro[:3]]

    from ..schemas.prediction import ExamType
    return TopicPrediction(
        topic=topic,
        chapter=chapter,
        subject=subject,
        exam_type=micro_predictions[0].exam_type,
        target_year=micro_predictions[0].target_year,
        composite_importance=composite_importance,
        topic_rank_in_chapter=0,   # set after chapter aggregation
        topic_rank_in_subject=0,   # set after subject aggregation
        expected_weightage_band=score_to_band(composite_importance),
        trend_direction=trend_score_to_direction(avg_trend),
        recurrence_score=recurrence_score,
        composite_confidence=composite_confidence,
        micro_topic_predictions=micro_predictions,
        top_micro_topics=top_micros,
    )


def aggregate_to_chapter(
    topic_predictions: List[TopicPrediction],
    chapter: str,
    subject: str,
) -> ChapterPrediction:
    """Roll up topic predictions to a chapter-level prediction."""
    if not topic_predictions:
        raise ValueError(f"No topic predictions for chapter '{chapter}'")

    # Max-pooling for importance (a chapter is important if ANY topic is important)
    # Weighted average for confidence
    max_importance = max(t.composite_importance for t in topic_predictions)
    avg_confidence = sum(t.composite_confidence for t in topic_predictions) / len(topic_predictions)
    avg_recurrence = sum(t.recurrence_score     for t in topic_predictions) / len(topic_predictions)

    # Trend: use the direction of the most important topic
    top_topic = max(topic_predictions, key=lambda t: t.composite_importance)
    trend = top_topic.trend_direction

    # Rank topics within chapter
    sorted_topics = sorted(topic_predictions, key=lambda t: t.composite_importance, reverse=True)
    for rank, t in enumerate(sorted_topics, 1):
        t.topic_rank_in_chapter = rank

    top_topics = [t.topic for t in sorted_topics[:5]]
    total_micros = sum(len(t.micro_topic_predictions) for t in topic_predictions)

    return ChapterPrediction(
        chapter=chapter,
        subject=subject,
        exam_type=topic_predictions[0].exam_type,
        target_year=topic_predictions[0].target_year,
        composite_importance=max_importance,
        chapter_rank_in_subject=0,  # set after subject aggregation
        expected_weightage_band=score_to_band(max_importance),
        trend_direction=trend,
        recurrence_score=avg_recurrence,
        composite_confidence=avg_confidence,
        topic_predictions=sorted_topics,
        top_topics=top_topics,
        total_micro_topics=total_micros,
    )


def aggregate_to_subject(
    chapter_predictions: List[ChapterPrediction],
    subject: str,
) -> SubjectPrediction:
    """Roll up chapter predictions to subject-level."""
    if not chapter_predictions:
        raise ValueError(f"No chapter predictions for subject '{subject}'")

    max_importance = max(c.composite_importance for c in chapter_predictions)
    avg_confidence = sum(c.composite_confidence for c in chapter_predictions) / len(chapter_predictions)

    sorted_chaps = sorted(chapter_predictions, key=lambda c: c.composite_importance, reverse=True)
    for rank, c in enumerate(sorted_chaps, 1):
        c.chapter_rank_in_subject = rank
        # Propagate rank to topics within each chapter
        for t in c.topic_predictions:
            t.topic_rank_in_subject = (rank - 1) * 100 + t.topic_rank_in_chapter

    top_chapters = [c.chapter for c in sorted_chaps[:5]]
    high_priority_topics = []
    for c in sorted_chaps[:3]:
        high_priority_topics.extend(c.top_topics[:2])

    return SubjectPrediction(
        subject=subject,
        exam_type=chapter_predictions[0].exam_type,
        target_year=chapter_predictions[0].target_year,
        composite_importance=max_importance,
        subject_rank=0,  # set at batch level
        top_chapters=top_chapters,
        high_priority_topics=high_priority_topics[:10],
        composite_confidence=avg_confidence,
        chapter_predictions=sorted_chaps,
    )


def build_prediction_batch(
    flat_micro_predictions: List[MicroTopicPrediction],
    batch_id: str,
) -> PredictionBatch:
    """
    Build a full PredictionBatch from a flat list of MicroTopicPredictions.
    Groups them up through the hierarchy and builds a fast lookup index.
    """
    from collections import defaultdict
    from ..schemas.prediction import ExamType

    # Group by subject → chapter → topic
    tree: Dict[str, Dict[str, Dict[str, List[MicroTopicPrediction]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for m in flat_micro_predictions:
        tree[m.subject][m.chapter][m.topic].append(m)

    subject_predictions = []
    for subject, chapters in tree.items():
        chapter_preds = []
        for chapter, topics in chapters.items():
            topic_preds = []
            for topic, micros in topics.items():
                tp = aggregate_to_topic(micros, topic, chapter, subject)
                topic_preds.append(tp)
            cp = aggregate_to_chapter(topic_preds, chapter, subject)
            chapter_preds.append(cp)
        sp = aggregate_to_subject(chapter_preds, subject)
        subject_predictions.append(sp)

    # Rank subjects
    sorted_subjects = sorted(subject_predictions, key=lambda s: s.composite_importance, reverse=True)
    for rank, s in enumerate(sorted_subjects, 1):
        s.subject_rank = rank

    # Build micro-topic index
    micro_index = {m.micro_topic_id: m for m in flat_micro_predictions}

    exam_type    = flat_micro_predictions[0].exam_type if flat_micro_predictions else ExamType.NEET
    target_year  = flat_micro_predictions[0].target_year if flat_micro_predictions else 2026

    return PredictionBatch(
        batch_id=batch_id,
        exam_type=exam_type,
        target_year=target_year,
        subject_predictions=sorted_subjects,
        micro_topic_index=micro_index,
        total_micro_topics_predicted=len(flat_micro_predictions),
        total_topics_predicted=sum(
            len(c.topic_predictions)
            for s in sorted_subjects for c in s.chapter_predictions
        ),
        total_chapters_predicted=sum(
            len(s.chapter_predictions) for s in sorted_subjects
        ),
    )


# ── Lookup utilities ───────────────────────────────────────────────────────────

def get_chapter_from_batch(
    batch: PredictionBatch, subject: str, chapter: str
) -> Optional[ChapterPrediction]:
    for sp in batch.subject_predictions:
        if sp.subject.lower() == subject.lower():
            for cp in sp.chapter_predictions:
                if cp.chapter.lower() == chapter.lower():
                    return cp
    return None


def get_top_n_micro_topics(
    batch: PredictionBatch, subject: Optional[str] = None, n: int = 20
) -> List[MicroTopicPrediction]:
    """Get the top N micro-topics globally or within a subject, sorted by importance."""
    all_micros = list(batch.micro_topic_index.values())
    if subject:
        all_micros = [m for m in all_micros if m.subject.lower() == subject.lower()]
    return sorted(all_micros, key=lambda m: m.importance_probability, reverse=True)[:n]


def subject_importance_vector(batch: PredictionBatch) -> Dict[str, float]:
    """Returns {subject: composite_importance} for all subjects in batch."""
    return {s.subject: s.composite_importance for s in batch.subject_predictions}
