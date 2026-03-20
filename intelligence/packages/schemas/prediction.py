"""
Prediction Engine Output Contracts
====================================
These Pydantic models define the data contract between the PRAJNA prediction
engine and the intelligence layer.  The intelligence layer CONSUMES these;
it never modifies them.

Academic hierarchy:
    micro_topic → topic → chapter → subject → exam
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class HierarchyScope(str, Enum):
    MICRO_TOPIC = "micro_topic"
    TOPIC       = "topic"
    CHAPTER     = "chapter"
    SUBJECT     = "subject"


class WeightageBand(str, Enum):
    """Expected question count band in the upcoming exam."""
    VERY_HIGH = "very_high"   # 5+ questions
    HIGH      = "high"        # 3–5 questions
    MEDIUM    = "medium"      # 1–3 questions
    LOW       = "low"         # 0–1 questions
    NEGLIGIBLE = "negligible" # unlikely to appear


class TrendDirection(str, Enum):
    RISING        = "rising"
    STABLE        = "stable"
    DECLINING     = "declining"
    VOLATILE      = "volatile"
    FIRST_TIME    = "first_time"   # never appeared before


class AppearancePattern(str, Enum):
    APPEARED_LAST_YEAR  = "appeared_last_year"
    APPEARED_LAST_2     = "appeared_last_2_years"
    APPEARED_LAST_3     = "appeared_last_3_years"
    GAP_1_YEAR          = "gap_1_year"
    GAP_2_YEARS         = "gap_2_years"
    GAP_3_PLUS          = "gap_3_plus_years"
    LONG_ABSENT         = "long_absent"         # 5+ year gap
    NEVER_APPEARED      = "never_appeared"
    IRREGULAR           = "irregular"


class ExamType(str, Enum):
    NEET         = "neet"
    JEE_MAIN     = "jee_main"
    JEE_ADVANCED = "jee_advanced"
    NEET_UG      = "neet_ug"
    ALL          = "all"


# ── Core prediction objects ───────────────────────────────────────────────────

class TopicClusterRef(BaseModel):
    """A reference to a related topic cluster (output from PRAJNA cluster detection)."""
    cluster_id:   str
    cluster_name: str
    member_count: int
    avg_importance: float = Field(ge=0.0, le=1.0)
    is_anchor: bool = False   # is this item the anchor of the cluster?


class MicroTopicPrediction(BaseModel):
    """
    Single micro-topic prediction from the PRAJNA prediction engine.
    This is the atomic unit of prediction output.
    """
    # Identity
    prediction_id:   str = Field(description="Unique prediction record ID")
    micro_topic_id:  str
    micro_topic_name: str
    topic:           str
    chapter:         str
    subject:         str
    exam_type:       ExamType
    target_year:     int  = Field(description="Year being predicted for")

    # Core signals from PRAJNA SLM
    importance_probability:   float = Field(ge=0.0, le=1.0,
        description="P(topic appears) from PRAJNA SLM backbone")
    importance_rank:          int   = Field(ge=1,
        description="1 = most important in subject")
    expected_weightage_band:  WeightageBand
    recurrence_score:         float = Field(ge=0.0, le=1.0,
        description="How regularly this topic recurs across exam history")
    recent_appearance_pattern: AppearancePattern
    historical_frequency:     float = Field(ge=0.0, le=1.0,
        description="Fraction of years this topic appeared, over full history")
    topic_trend_score:        float = Field(ge=-1.0, le=1.0,
        description="Positive = rising, negative = declining trend")
    syllabus_coverage_signal: float = Field(ge=0.0, le=1.0,
        description="How well this topic covers the official syllabus prescription")
    confidence_score:         float = Field(ge=0.0, le=1.0,
        description="Engine's self-reported confidence in this prediction")

    # Cluster / relational signals
    related_topic_clusters:   List[TopicClusterRef] = Field(default_factory=list)

    # Metadata
    predicted_at: datetime = Field(default_factory=datetime.utcnow)
    engine_version: str = "prajna-slm-v3"
    feature_vector_dim: int = 399   # matches PRAJNA SLM input dim

    @field_validator("importance_probability", "recurrence_score",
                     "historical_frequency", "syllabus_coverage_signal",
                     "confidence_score", mode="before")
    @classmethod
    def clamp_to_unit(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("topic_trend_score", mode="before")
    @classmethod
    def clamp_trend(cls, v: float) -> float:
        return max(-1.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def validate_rank_positive(self) -> "MicroTopicPrediction":
        if self.importance_rank < 1:
            raise ValueError("importance_rank must be >= 1")
        return self

    class Config:
        use_enum_values = True


class TopicPrediction(BaseModel):
    """
    Aggregated prediction at the TOPIC level.
    Rolled up from one or more MicroTopicPredictions.
    """
    topic:           str
    chapter:         str
    subject:         str
    exam_type:       ExamType
    target_year:     int

    # Rolled-up signals
    composite_importance:   float = Field(ge=0.0, le=1.0)
    topic_rank_in_chapter:  int
    topic_rank_in_subject:  int
    expected_weightage_band: WeightageBand
    trend_direction:        TrendDirection
    recurrence_score:       float = Field(ge=0.0, le=1.0)
    composite_confidence:   float = Field(ge=0.0, le=1.0)

    # Child micro-topic predictions
    micro_topic_predictions: List[MicroTopicPrediction] = Field(default_factory=list)

    # Derived
    top_micro_topics: List[str] = Field(default_factory=list,
        description="Names of top-3 micro-topics by importance_probability")

    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class ChapterPrediction(BaseModel):
    """Aggregated prediction at the CHAPTER level."""
    chapter:     str
    subject:     str
    exam_type:   ExamType
    target_year: int

    composite_importance:  float = Field(ge=0.0, le=1.0)
    chapter_rank_in_subject: int
    expected_weightage_band: WeightageBand
    trend_direction:        TrendDirection
    recurrence_score:       float = Field(ge=0.0, le=1.0)
    composite_confidence:   float = Field(ge=0.0, le=1.0)

    topic_predictions:  List[TopicPrediction] = Field(default_factory=list)
    top_topics:         List[str] = Field(default_factory=list)
    total_micro_topics: int = 0

    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class SubjectPrediction(BaseModel):
    """Aggregated prediction at the SUBJECT level."""
    subject:     str
    exam_type:   ExamType
    target_year: int

    composite_importance:  float = Field(ge=0.0, le=1.0)
    subject_rank:          int
    top_chapters:          List[str] = Field(default_factory=list)
    high_priority_topics:  List[str] = Field(default_factory=list)
    composite_confidence:  float = Field(ge=0.0, le=1.0)

    chapter_predictions:   List[ChapterPrediction] = Field(default_factory=list)

    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class PredictionBatch(BaseModel):
    """Full prediction output batch from the PRAJNA engine for one exam/year."""
    batch_id:      str
    exam_type:     ExamType
    target_year:   int
    generated_at:  datetime = Field(default_factory=datetime.utcnow)
    engine_version: str = "prajna-slm-v3"

    subject_predictions: List[SubjectPrediction] = Field(default_factory=list)

    # Flat index for fast lookup
    micro_topic_index: Dict[str, MicroTopicPrediction] = Field(
        default_factory=dict,
        description="Keyed by micro_topic_id for O(1) retrieval"
    )

    total_micro_topics_predicted: int = 0
    total_topics_predicted:       int = 0
    total_chapters_predicted:     int = 0
