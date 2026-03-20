"""
Insights Router
================
Endpoints for generating structured insights at all hierarchy levels.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from packages.schemas.contracts import (
    ChapterSummaryRequest, ChapterSummaryResponse,
    InsightRequest, InsightResponse,
    SubjectStrategyRequest, SubjectStrategyResponse,
    TrendReportRequest, TrendReportResponse,
)
from packages.schemas.intelligence import InsightType, PersonaType
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


@router.post("/micro-topic", response_model=InsightResponse,
             summary="Explain a micro-topic's importance")
async def micro_topic_insight(
    request: InsightRequest,
    adapter:   PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
    generator:  InsightGenerator            = Depends(insight_generator_dep),
):
    """
    Generate a grounded explanation of why a micro-topic is important
    for the upcoming exam. Ideal for student-facing or teacher-facing views.
    """
    req_id = str(uuid.uuid4())

    # Fetch predictions
    micro_preds = await adapter.get_predictions(
        exam_type=request.exam_type,
        target_year=request.target_year,
        subject=request.subject,
    )

    # Filter to the requested micro-topic if specified
    if request.micro_topic:
        micro_preds = [m for m in micro_preds
                       if request.micro_topic.lower() in m.micro_topic_name.lower()]

    if not micro_preds:
        return InsightResponse(
            success=True, request_id=req_id,
            exam_type=request.exam_type, target_year=request.target_year,
            persona=request.persona, insights=[], total_count=0,
        )

    batch = aggregator.build_batch(micro_preds)
    top_micros = list(batch.micro_topic_index.values())[:request.top_n]

    insights = []
    for micro in top_micros[:5]:   # cap at 5 SLM calls per request
        signals = {
            "importance_probability":   micro.importance_probability,
            "confidence_score":         micro.confidence_score,
            "recurrence_score":         micro.recurrence_score,
            "topic_trend_score":        micro.topic_trend_score,
            "historical_frequency":     micro.historical_frequency,
            "syllabus_coverage_signal": micro.syllabus_coverage_signal,
            "recent_appearance_pattern": micro.recent_appearance_pattern,
            "expected_weightage_band":  str(micro.expected_weightage_band),
        }
        insight = await generator.generate_topic_insight(
            micro_topic_name=micro.micro_topic_name,
            prediction_signals=signals,
            exam_type=request.exam_type,
            target_year=request.target_year,
            persona=request.persona,
            subject=micro.subject,
            chapter=micro.chapter,
        )
        insights.append(insight)

    return InsightResponse(
        success=True, request_id=req_id,
        exam_type=request.exam_type, target_year=request.target_year,
        persona=request.persona, insights=insights, total_count=len(insights),
    )


@router.post("/chapter", response_model=ChapterSummaryResponse,
             summary="Chapter intelligence summary")
async def chapter_insight(
    request: ChapterSummaryRequest,
    adapter:    PredictionAdapter            = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator  = Depends(aggregator_dep),
    generator:  InsightGenerator             = Depends(insight_generator_dep),
):
    """
    Generate a comprehensive chapter intelligence summary including:
    importance tier, expected questions, top micro-topics, trend analysis.
    """
    req_id = str(uuid.uuid4())

    micro_preds = await adapter.get_predictions(
        exam_type=request.exam_type,
        target_year=request.target_year,
        subject=request.subject,
    )
    batch   = aggregator.build_batch(micro_preds)
    summary = aggregator.build_chapter_summary(batch, request.subject, request.chapter)

    if summary is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Chapter '{request.chapter}' not found")

    # Generate SLM narrative for the summary
    ranked_topics = [
        {
            "name": p.scope_name,
            "importance_probability": p.importance_probability,
            "confidence_score": p.confidence,
            "trend_direction": str(p.trend_direction),
            "urgency": str(p.urgency),
        }
        for p in summary.top_priority_topics[:8]
    ]

    signals = {
        "composite_importance": summary.composite_importance,
        "confidence":           summary.confidence,
        "trend_direction":      str(summary.trend_direction),
        "importance_tier":      summary.importance_tier,
        "expected_questions":   summary.expected_questions,
        "revision_priority":    str(summary.revision_priority),
    }

    insight = await generator.generate_chapter_insight(
        chapter=request.chapter,
        subject=request.subject,
        prediction_signals=signals,
        ranked_topics=ranked_topics,
        exam_type=request.exam_type,
        target_year=request.target_year,
        persona=request.persona,
    )

    summary.chapter_brief   = insight.narrative
    summary.teacher_notes   = insight.recommended_action
    summary.student_summary = insight.claim

    return ChapterSummaryResponse(
        success=True, request_id=req_id, summary=summary
    )


@router.post("/subject-strategy", response_model=SubjectStrategyResponse,
             summary="Full subject revision strategy")
async def subject_strategy(
    request: SubjectStrategyRequest,
    adapter:          PredictionAdapter            = Depends(prediction_adapter_dep),
    aggregator:       TopicIntelligenceAggregator  = Depends(aggregator_dep),
    cluster_detector: TopicClusterDetector         = Depends(cluster_detector_dep),
    generator:        InsightGenerator             = Depends(insight_generator_dep),
):
    """
    Generate a complete subject revision strategy with chapter rankings,
    micro-topic priorities, cluster analysis, and SLM-generated study plan.
    """
    req_id = str(uuid.uuid4())

    micro_preds = await adapter.get_predictions(
        exam_type=request.exam_type,
        target_year=request.target_year,
        subject=request.subject,
    )
    batch    = aggregator.build_batch(micro_preds)
    strategy = aggregator.build_subject_strategy(batch, request.subject)

    if strategy is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Subject '{request.subject}' not found")

    # Detect clusters
    clusters = cluster_detector.detect_clusters(batch, subject=request.subject)
    strategy.high_risk_clusters = clusters

    # Build context for SLM
    cluster_summary = "\n".join(
        f"- {c.cluster_name}: {', '.join(c.member_topics[:3])} (importance={c.cluster_importance:.0%})"
        for c in clusters[:5]
    ) or "No clusters detected"

    ranked_chapters = [
        {
            "name": cs.chapter,
            "importance_probability": cs.composite_importance,
            "confidence_score": cs.confidence,
            "trend_direction": str(cs.trend_direction),
            "importance_tier": cs.importance_tier,
        }
        for cs in strategy.chapter_summaries[:10]
    ]

    signals = {
        "subject_rank":         strategy.subject_rank,
        "overall_importance":   strategy.overall_importance,
        "confidence":           strategy.confidence,
        "recommended_hours":    strategy.recommended_study_hours,
        "expected_marks":       strategy.expected_marks_coverage,
        "must_revise_count":    len(strategy.must_revise_chapters),
    }

    insight = await generator.generate_subject_strategy(
        subject=request.subject,
        prediction_signals=signals,
        ranked_chapters=ranked_chapters,
        cluster_summary=cluster_summary,
        trend_summary=f"{len(clusters)} clusters detected for {request.subject}",
        exam_type=request.exam_type,
        target_year=request.target_year,
        persona=request.persona,
    )

    strategy.executive_summary  = insight.claim
    strategy.strategy_narrative = insight.narrative
    strategy.insights           = [insight]

    return SubjectStrategyResponse(
        success=True, request_id=req_id, strategy=strategy
    )


@router.get("/top-topics", summary="Top N predicted topics across all subjects")
async def top_topics(
    exam_type:   ExamType = Query(...),
    target_year: int      = Query(...),
    subject:     Optional[str] = Query(None),
    top_n:       int      = Query(default=20, ge=1, le=100),
    adapter:    PredictionAdapter           = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator = Depends(aggregator_dep),
):
    """
    Fast endpoint — returns top predicted micro-topics with key signals.
    No SLM call — pure prediction engine output, ranked and formatted.
    """
    micro_preds = await adapter.get_predictions(
        exam_type=exam_type,
        target_year=target_year,
        subject=subject,
    )
    batch = aggregator.build_batch(micro_preds)

    from packages.utils.hierarchy import get_top_n_micro_topics
    top = get_top_n_micro_topics(batch, subject=subject, n=top_n)

    return {
        "success":     True,
        "exam_type":   exam_type,
        "target_year": target_year,
        "total":       len(top),
        "topics": [
            {
                "rank":                   i + 1,
                "micro_topic":            m.micro_topic_name,
                "topic":                  m.topic,
                "chapter":                m.chapter,
                "subject":                m.subject,
                "importance_probability": round(m.importance_probability, 3),
                "confidence":             round(m.confidence_score, 3),
                "trend":                  m.topic_trend_score,
                "recurrence":             round(m.recurrence_score, 3),
                "weightage_band":         str(m.expected_weightage_band),
                "appearance_pattern":     str(m.recent_appearance_pattern),
            }
            for i, m in enumerate(top)
        ],
    }
