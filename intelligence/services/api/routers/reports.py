"""
Reports Router — Batch report generation
"""

from __future__ import annotations
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from packages.schemas.contracts import RevisionPlanRequest, RevisionPlanResponse
from packages.schemas.prediction import ExamType
from services.api.deps import (
    aggregator_dep, cluster_detector_dep,
    insight_generator_dep, prediction_adapter_dep,
)
from services.topic_intelligence.aggregator import TopicIntelligenceAggregator
from services.topic_intelligence.cluster_detector import TopicClusterDetector
from services.insight_engine.generator import InsightGenerator
from services.prediction_adapter.client import PredictionAdapter

router = APIRouter()


@router.post("/revision-plan", response_model=RevisionPlanResponse,
             summary="Generate a complete revision plan")
async def revision_plan(
    request: RevisionPlanRequest,
    adapter:          PredictionAdapter            = Depends(prediction_adapter_dep),
    aggregator:       TopicIntelligenceAggregator  = Depends(aggregator_dep),
    cluster_detector: TopicClusterDetector         = Depends(cluster_detector_dep),
    generator:        InsightGenerator             = Depends(insight_generator_dep),
):
    """
    Generate a complete, prioritized revision plan across all subjects.
    Includes per-subject strategies, chapter rankings, and SLM-generated study recommendations.
    """
    req_id = str(uuid.uuid4())

    micro_preds = await adapter.get_predictions(
        exam_type=request.exam_type,
        target_year=request.target_year,
    )
    batch = aggregator.build_batch(micro_preds)

    subjects = request.subjects or list({m.subject for m in micro_preds})
    subject_strategies = []

    for subject in subjects:
        strategy = aggregator.build_subject_strategy(
            batch, subject, available_days=request.available_days
        )
        if strategy:
            subject_strategies.append(strategy)

    # Global top priorities across all subjects
    global_priorities = aggregator.rank_revision_priorities(batch, top_n=20)

    # Generate exam brief
    ranked_items = [
        {"name": p.scope_name, "importance_probability": p.importance_probability,
         "confidence_score": p.confidence, "chapter": p.parent_chain[1] if len(p.parent_chain) > 1 else ""}
        for p in global_priorities[:15]
    ]
    insight = await generator.generate_exam_brief(
        exam_type=request.exam_type,
        target_year=request.target_year,
        ranked_items=ranked_items,
        trend_summary=f"{len(subject_strategies)} subjects analyzed",
        cluster_summary="See individual subject strategies for cluster details",
        prediction_signals={"total_micro_topics": batch.total_micro_topics_predicted},
        persona=request.persona,
    )

    return RevisionPlanResponse(
        success=True, request_id=req_id,
        exam_type=request.exam_type, target_year=request.target_year,
        subject_strategies=subject_strategies,
        global_top_priorities=global_priorities,
        exam_brief=insight.narrative,
    )


@router.get("/trend-analysis", summary="Topic trend analysis vs previous year")
async def trend_analysis(
    exam_type:    ExamType   = Query(...),
    current_year: int        = Query(...),
    compare_year: int        = Query(...),
    subject:      Optional[str] = Query(None),
    adapter:    PredictionAdapter            = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator  = Depends(aggregator_dep),
):
    """Compare topic importance between two years and surface trend shifts."""
    req_id = str(uuid.uuid4())

    current_preds = await adapter.get_predictions(exam_type, current_year, subject)
    compare_preds = await adapter.get_predictions(exam_type, compare_year, subject)

    current_batch = aggregator.build_batch(current_preds, f"batch-{current_year}")
    compare_batch = aggregator.build_batch(compare_preds, f"batch-{compare_year}")

    report = aggregator.detect_trend_shifts(current_batch, compare_batch, subject)

    return {
        "success":    True,
        "request_id": req_id,
        "report":     report.dict(),
    }
