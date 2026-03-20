"""
API Request / Response Contracts
==================================
FastAPI-level schemas: what comes in, what goes out.
All SLM input/output is also typed here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .prediction import ExamType, HierarchyScope
from .intelligence import (
    InsightObject, InsightType, PersonaType,
    RevisionPriorityObject, SubjectStrategySummary,
    ChapterSummaryObject, TrendShiftReport, TopicClusterObject,
)


# ── Common base ───────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class APIResponse(BaseModel):
    success: bool = True
    request_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None


# ── Insight Requests ──────────────────────────────────────────────────────────

class InsightRequest(BaseModel):
    """Generic insight generation request."""
    exam_type:   ExamType
    target_year: int
    subject:     Optional[str] = None
    chapter:     Optional[str] = None
    topic:       Optional[str] = None
    micro_topic: Optional[str] = None
    persona:     PersonaType = PersonaType.STUDENT
    insight_types: List[InsightType] = Field(default_factory=list,
        description="If empty, generate all applicable insight types")
    top_n:       int = Field(default=10, ge=1, le=50)


class InsightResponse(APIResponse):
    exam_type:   ExamType
    target_year: int
    persona:     PersonaType
    insights:    List[InsightObject]
    total_count: int


# ── Copilot / NL Query ────────────────────────────────────────────────────────

class CopilotRequest(BaseModel):
    """Natural language question from a user."""
    question:    str = Field(min_length=5, max_length=1000)
    exam_type:   ExamType
    target_year: int
    persona:     PersonaType = PersonaType.STUDENT
    subject_filter: Optional[str] = None
    chapter_filter: Optional[str] = None
    # Context from previous turns (for multi-turn)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)


class CopilotResponse(APIResponse):
    question:    str
    answer:      str
    confidence:  float = Field(ge=0.0, le=1.0)
    insights:    List[InsightObject] = Field(default_factory=list)
    sources:     List[Dict[str, Any]] = Field(default_factory=list)
    follow_up_questions: List[str]   = Field(default_factory=list)


# ── Revision Plan ─────────────────────────────────────────────────────────────

class RevisionPlanRequest(BaseModel):
    exam_type:        ExamType
    target_year:      int
    subjects:         List[str] = Field(default_factory=list,
        description="If empty, generate for all subjects")
    persona:          PersonaType = PersonaType.STUDENT
    available_days:   Optional[int] = None    # study days remaining before exam
    top_n_per_subject: int = 10


class RevisionPlanResponse(APIResponse):
    exam_type:     ExamType
    target_year:   int
    subject_strategies: List[SubjectStrategySummary]
    global_top_priorities: List[RevisionPriorityObject]
    exam_brief:    str   = ""   # Cross-subject strategic summary


# ── Chapter Summary ────────────────────────────────────────────────────────────

class ChapterSummaryRequest(BaseModel):
    exam_type:   ExamType
    target_year: int
    subject:     str
    chapter:     str
    persona:     PersonaType = PersonaType.TEACHER


class ChapterSummaryResponse(APIResponse):
    summary: ChapterSummaryObject


# ── Subject Strategy ───────────────────────────────────────────────────────────

class SubjectStrategyRequest(BaseModel):
    exam_type:   ExamType
    target_year: int
    subject:     str
    persona:     PersonaType = PersonaType.ACADEMIC_PLANNER
    include_micro_topics: bool = True


class SubjectStrategyResponse(APIResponse):
    strategy: SubjectStrategySummary


# ── Trend Report ───────────────────────────────────────────────────────────────

class TrendReportRequest(BaseModel):
    exam_type:    ExamType
    current_year: int
    compare_year: int
    subject:      Optional[str] = None


class TrendReportResponse(APIResponse):
    report: TrendShiftReport


# ── SLM Input / Output Contract ───────────────────────────────────────────────

class SLMInputContext(BaseModel):
    """
    The structured context sent to the SLM for insight generation.
    Keeps the SLM grounded in prediction data + retrieved evidence.
    """
    # User request
    task:        str   = Field(description="What to generate: 'explain'|'strategize'|'answer'|'brief'")
    question:    Optional[str] = None
    persona:     PersonaType

    # Prediction signals (structured)
    scope:       HierarchyScope
    scope_name:  str
    exam_type:   ExamType
    target_year: int

    prediction_signals: Dict[str, Any] = Field(
        description="Key signals from prediction engine: importance, trend, recurrence, etc."
    )
    ranked_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top N ranked topics/chapters with their scores"
    )

    # Retrieved evidence (from RAG)
    retrieved_passages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Relevant excerpts from curriculum, past exams, playbooks"
    )

    # Anti-hallucination constraints
    allowed_claims:     List[str] = Field(default_factory=list,
        description="Claims the SLM is permitted to make (evidence-backed)")
    forbidden_topics:   List[str] = Field(default_factory=list,
        description="Topics not covered in predictions — SLM must not speculate")


class SLMOutputContract(BaseModel):
    """
    Typed output from the SLM.
    Parsed from raw model text before being converted to InsightObject.
    """
    title:              str
    claim:              str
    narrative:          str
    recommended_action: str
    confidence:         float = Field(ge=0.0, le=1.0)
    is_grounded:        bool  = True
    evidence_refs:      List[str] = Field(default_factory=list,
        description="IDs of evidence objects cited in narrative")
    tags:               List[str] = Field(default_factory=list)
    fallback_triggered: bool  = False   # True if evidence was too weak
    fallback_message:   Optional[str] = None
