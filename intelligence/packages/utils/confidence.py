"""
Confidence Calibration Utilities
==================================
Functions for computing, propagating, and calibrating confidence scores
across the hierarchy. High-stakes predictions need well-calibrated confidence.
"""

from __future__ import annotations
import math
from typing import List, Dict, Any, Optional


# ── Composite confidence ───────────────────────────────────────────────────────

def composite_confidence(
    signal_confidences: List[float],
    weights: Optional[List[float]] = None,
) -> float:
    """
    Weighted geometric mean of individual signal confidences.
    Geometric mean penalizes any single very-low-confidence signal more than
    arithmetic mean — appropriate for high-stakes academic predictions.
    """
    if not signal_confidences:
        return 0.0
    n = len(signal_confidences)
    if weights is None:
        weights = [1.0 / n] * n
    assert abs(sum(weights) - 1.0) < 1e-6, "Weights must sum to 1.0"

    log_sum = sum(w * math.log(max(c, 1e-9)) for c, w in zip(signal_confidences, weights))
    return min(1.0, max(0.0, math.exp(log_sum)))


def confidence_tier(c: float) -> str:
    """Human-readable confidence tier label."""
    if c >= 0.80: return "high"
    if c >= 0.55: return "medium"
    if c >= 0.35: return "low"
    return "very_low"


def confidence_caveat(c: float) -> str:
    """Standard caveat text for a given confidence level."""
    if c >= 0.80:
        return "High confidence — prediction is well-supported by historical data."
    if c >= 0.55:
        return "Medium confidence — prediction is plausible but has some uncertainty."
    if c >= 0.35:
        return "Low confidence — treat as a weak signal; do not rely on this alone."
    return "Very low confidence — insufficient evidence; this is speculative."


# ── Propagation rules ──────────────────────────────────────────────────────────

def propagate_down(parent_confidence: float, depth: int = 1) -> float:
    """
    When propagating confidence down the hierarchy (e.g., subject → chapter),
    apply a small decay per level.
    """
    decay_per_level = 0.05
    return max(0.0, parent_confidence - depth * decay_per_level)


def propagate_up(child_confidences: List[float]) -> float:
    """
    When rolling up confidence (chapter → subject),
    use the max child confidence (optimistic) tempered by coverage.
    """
    if not child_confidences:
        return 0.0
    max_c = max(child_confidences)
    coverage_factor = min(1.0, len(child_confidences) / 10.0)  # more children = more reliable
    return max_c * (0.7 + 0.3 * coverage_factor)


# ── Evidence weighting ─────────────────────────────────────────────────────────

EVIDENCE_TYPE_WEIGHTS = {
    "prediction_signal":    1.0,   # PRAJNA SLM output — highest authority
    "historical_exam":      0.90,
    "curriculum_doc":       0.75,
    "benchmark_pattern":    0.65,
    "retrieved_chunk":      0.55,
    "student_performance":  0.40,
}


def evidence_weighted_confidence(
    base_confidence: float,
    evidence_items: List[Dict[str, Any]],
) -> float:
    """
    Adjust base confidence based on quality and quantity of evidence.
    More high-quality evidence increases confidence; absence of evidence reduces it.
    """
    if not evidence_items:
        return base_confidence * 0.5   # significant penalty for no evidence

    total_weight  = sum(
        EVIDENCE_TYPE_WEIGHTS.get(e.get("evidence_type", "retrieved_chunk"), 0.55) *
        float(e.get("relevance_score", 0.5))
        for e in evidence_items
    )
    max_possible  = sum(
        max(EVIDENCE_TYPE_WEIGHTS.values()) for _ in evidence_items
    )
    evidence_boost = min(0.15, (total_weight / max_possible) * 0.15)
    return min(1.0, base_confidence + evidence_boost)


# ── Priority scoring ───────────────────────────────────────────────────────────

def compute_priority_score(
    importance_probability: float,
    confidence: float,
    recurrence_score: float,
    trend_score: float,
    syllabus_coverage: float,
) -> float:
    """
    Compute the 0–100 priority score used in RevisionPriorityObject.
    Formula is a weighted sum of all prediction signals.
    """
    # Weight vector (must sum to 1.0)
    w_importance   = 0.40
    w_confidence   = 0.20
    w_recurrence   = 0.20
    w_trend        = 0.10
    w_syllabus     = 0.10

    # Normalize trend to [0, 1]
    norm_trend = (trend_score + 1.0) / 2.0

    raw = (
        w_importance * importance_probability +
        w_confidence * confidence +
        w_recurrence * recurrence_score +
        w_trend      * norm_trend +
        w_syllabus   * syllabus_coverage
    )
    return round(min(100.0, max(0.0, raw * 100)), 2)


def priority_score_to_urgency(score: float) -> str:
    """Convert numeric priority score to urgency label."""
    if score >= 75: return "critical"
    if score >= 55: return "high"
    if score >= 35: return "medium"
    if score >= 15: return "low"
    return "optional"
