"""
Copilot Router — Natural Language Q&A
"""

from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from packages.schemas.contracts import CopilotRequest, CopilotResponse
from services.api.deps import (
    aggregator_dep, insight_generator_dep, prediction_adapter_dep,
)
from services.topic_intelligence.aggregator import TopicIntelligenceAggregator
from services.insight_engine.generator import InsightGenerator
from services.prediction_adapter.client import PredictionAdapter

router = APIRouter()


@router.post("/ask", response_model=CopilotResponse,
             summary="Ask a natural language question about upcoming exam topics")
async def ask_copilot(
    request:    CopilotRequest,
    adapter:    PredictionAdapter            = Depends(prediction_adapter_dep),
    aggregator: TopicIntelligenceAggregator  = Depends(aggregator_dep),
    generator:  InsightGenerator             = Depends(insight_generator_dep),
):
    """
    Natural language question answering grounded in prediction data.

    Examples:
    - "Which chapters in Physics should I prioritize for NEET 2026?"
    - "What topics in Organic Chemistry are trending upward?"
    - "Give me an exam brief for JEE Main 2026"
    - "Which Biology micro-topics have a long gap and are overdue?"
    """
    req_id = str(uuid.uuid4())

    micro_preds = await adapter.get_predictions(
        exam_type=request.exam_type,
        target_year=request.target_year,
        subject=request.subject_filter,
    )
    batch = aggregator.build_batch(micro_preds)
    insight = await generator.answer_copilot_question(request, batch)

    follow_ups = [
        f"What are the top micro-topics in {insight.parent_chain[0] if insight.parent_chain else 'Physics'}?",
        f"How many hours should I spend on {insight.scope_name}?",
        f"What topic clusters should I study together?",
    ]

    return CopilotResponse(
        success=True, request_id=req_id,
        question=request.question,
        answer=insight.narrative,
        confidence=insight.confidence,
        insights=[insight],
        sources=[{"source": e.source_name, "type": str(e.evidence_type)} for e in insight.evidence],
        follow_up_questions=follow_ups,
    )
