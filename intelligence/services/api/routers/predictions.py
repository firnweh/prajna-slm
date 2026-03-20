"""
Predictions Router — Raw prediction passthrough
================================================
Exposes the PRAJNA prediction engine output directly via REST.
These endpoints let consumers query the raw prediction signals
without any SLM processing.  Useful for dashboards, custom UIs,
and third-party integrations that want to build their own views.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from packages.schemas.prediction import (
    ExamType, HierarchyScope, MicroTopicPrediction,
    ChapterPrediction, SubjectPrediction, PredictionBatch,
)
from packages.utils.confidence import compute_priority_score, priority_score_to_urgency
from packages.utils.hierarchy import get_chapter_from_batch, subject_importance_vector
from services.api.deps import aggregator_dep, prediction_adapter_dep
from services.topic_intelligence.aggregator import TopicIntelligenceAggregator
from services.prediction_adapter.client import PredictionAdapter

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class MicroTopicSummary(BaseModel):
    """Lightweight summary of a single micro-topic prediction."""
    micro_topic_id:  str
    micro_topic_name: str
    topic:           str
    chapter:         str
    subject:         str
    importance_probability: float
    confidence_score:       float
    trend_direction: str
    priority_score:  float
    urgency:         str


class BatchSummaryResponse(BaseModel):
    success:      bool = True
    request_id:   str
    exam_type:    ExamType
    target_year:  int
    total_subjects:     int
    total_chapters:     int
    total_topics:       int
    total_micro_topics: int
    subject_importance_vector: dict   # {subject: composite_importance}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/batch-summary",
    response_model=BatchSummaryResponse,
    summary="High-level batch summary for an exam/year",
)
async def batch_summary(
    exam_type:   ExamType = Query(..., description="Exam type (neet/jee_main/jee_advanced)"),
    target_year: int      = Query(..., ge=2024, le=2035),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Returns a lightweight summary of the prediction batch — counts and
    subject-level importance vector.  No SLM is involved.
    """
    req_id = str(uuid.uuid4())
    micro_preds = await adapter.get_predictions(exam_type, target_year)
    batch = aggregator.build_batch(micro_preds)

    return BatchSummaryResponse(
        request_id=req_id,
        exam_type=exam_type,
        target_year=target_year,
        total_subjects=len(batch.subject_predictions),
        total_chapters=batch.total_chapters_predicted,
        total_topics=batch.total_topics_predicted,
        total_micro_topics=batch.total_micro_topics_predicted,
        subject_importance_vector=subject_importance_vector(batch),
    )


@router.get(
    "/micro-topics",
    response_model=List[MicroTopicSummary],
    summary="List micro-topic predictions with priority scores",
)
async def list_micro_topics(
    exam_type:   ExamType    = Query(...),
    target_year: int         = Query(..., ge=2024, le=2035),
    subject:     Optional[str] = Query(None),
    chapter:     Optional[str] = Query(None),
    min_importance: float    = Query(0.0, ge=0.0, le=1.0),
    top_n:       int         = Query(50, ge=1, le=200),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Return raw micro-topic predictions, optionally filtered by subject/chapter.
    Results are sorted by computed priority score (descending).
    """
    micro_preds = await adapter.get_predictions(exam_type, target_year, subject)

    # Optional chapter filter
    if chapter:
        micro_preds = [m for m in micro_preds if m.chapter.lower() == chapter.lower()]

    # Minimum importance filter
    micro_preds = [m for m in micro_preds if m.importance_probability >= min_importance]

    # Compute priority score and sort
    scored: list[tuple[float, MicroTopicPrediction]] = []
    for m in micro_preds:
        ps = compute_priority_score(
            importance_probability=m.importance_probability,
            confidence=m.confidence_score,
            recurrence_score=m.recurrence_score,
            trend_score=m.topic_trend_score,
            syllabus_coverage=m.syllabus_coverage_signal,
        )
        scored.append((ps, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    return [
        MicroTopicSummary(
            micro_topic_id=m.micro_topic_id,
            micro_topic_name=m.micro_topic_name,
            topic=m.topic,
            chapter=m.chapter,
            subject=m.subject,
            importance_probability=m.importance_probability,
            confidence_score=m.confidence_score,
            trend_direction=m.topic_trend_score >= 0.1 and "rising"
                or m.topic_trend_score <= -0.1 and "declining" or "stable",
            priority_score=round(ps, 2),
            urgency=priority_score_to_urgency(ps),
        )
        for ps, m in top
    ]


@router.get(
    "/chapter/{chapter_name}",
    summary="Full chapter-level prediction detail",
)
async def chapter_detail(
    chapter_name: str,
    exam_type:    ExamType = Query(...),
    target_year:  int      = Query(..., ge=2024, le=2035),
    subject:      Optional[str] = Query(None),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Return the full aggregated prediction for a single chapter,
    including all topic-level and micro-topic-level breakdown.
    """
    micro_preds = await adapter.get_predictions(exam_type, target_year, subject)
    batch = aggregator.build_batch(micro_preds)

    chap = get_chapter_from_batch(batch, chapter_name)
    if not chap:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter '{chapter_name}' not found in prediction batch for "
                   f"{exam_type.value} {target_year}",
        )
    return {
        "success":    True,
        "request_id": str(uuid.uuid4()),
        "chapter":    chap.dict(),
    }


@router.get(
    "/subject/{subject_name}",
    summary="Subject-level prediction summary",
)
async def subject_detail(
    subject_name: str,
    exam_type:    ExamType = Query(...),
    target_year:  int      = Query(..., ge=2024, le=2035),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Return aggregated predictions for a single subject.
    """
    micro_preds = await adapter.get_predictions(exam_type, target_year, subject_name)
    batch = aggregator.build_batch(micro_preds)

    subject_pred = next(
        (s for s in batch.subject_predictions
         if s.subject.lower() == subject_name.lower()),
        None,
    )
    if not subject_pred:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{subject_name}' not found in prediction batch",
        )
    return {
        "success":    True,
        "request_id": str(uuid.uuid4()),
        "subject":    subject_pred.dict(),
    }


@router.get(
    "/rank-all",
    summary="Ranked list of all micro-topics across subjects",
)
async def rank_all(
    exam_type:   ExamType = Query(...),
    target_year: int      = Query(..., ge=2024, le=2035),
    top_n:       int      = Query(100, ge=1, le=500),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Compute and return a global ranking of revision priorities
    across all subjects.  Returns RevisionPriorityObjects sorted
    by priority_score descending.  No SLM involved — pure signal.
    """
    micro_preds = await adapter.get_predictions(exam_type, target_year)
    batch = aggregator.build_batch(micro_preds)
    priorities = aggregator.rank_revision_priorities(batch, top_n=top_n)

    return {
        "success":    True,
        "request_id": str(uuid.uuid4()),
        "exam_type":  exam_type,
        "target_year": target_year,
        "count":      len(priorities),
        "priorities": [p.dict() for p in priorities],
    }
