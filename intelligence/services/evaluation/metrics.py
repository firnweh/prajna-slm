"""
Evaluation Metrics for the Intelligence Layer
===============================================
Computes quantitative quality signals for:

1. Grounding accuracy   — are claims backed by input evidence?
2. Factual consistency  — do numbers / entities match prediction signals?
3. Ranking quality      — does priority ordering match ground truth?
4. Insight usefulness   — completeness, action-ability, persona-fit
5. Coverage             — fraction of important topics mentioned
6. Latency              — response time tracking

All metrics return a dict with a "score" key (0.0–1.0) and metadata.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any, Callable, Dict, List, Optional, Tuple

from packages.schemas.contracts import SLMInputContext, SLMOutputContract
from packages.schemas.intelligence import InsightObject, RevisionPriorityObject


# ── 1. Grounding Accuracy ─────────────────────────────────────────────────────

def grounding_accuracy(
    output: SLMOutputContract,
    context: SLMInputContext,
) -> Dict[str, Any]:
    """
    Measures what fraction of evidence_refs in the output actually exist
    in the input context (retrieved_passages or prediction_signals).

    Score = referenced evidence that exists / total evidence_refs claimed.
    Perfect score = 1.0.  0 refs → score = None (unevaluable).
    """
    if not output.evidence_refs:
        return {
            "score": None,
            "label": "unevaluable",
            "reason": "SLM cited no evidence; cannot verify grounding",
            "hallucinated_refs": [],
            "valid_refs": [],
        }

    # Build set of available evidence IDs
    available_ids: set[str] = set()
    for passage in context.retrieved_passages:
        if "evidence_id" in passage:
            available_ids.add(passage["evidence_id"])
    # Prediction signals are available by convention under "prediction_signal"
    available_ids.add("prediction_signal")
    available_ids.add("prajna_slm")

    valid_refs = [r for r in output.evidence_refs if r in available_ids]
    hallucinated = [r for r in output.evidence_refs if r not in available_ids]

    score = len(valid_refs) / len(output.evidence_refs)
    return {
        "score": round(score, 3),
        "label": "grounded" if score >= 0.8 else "partially_grounded" if score >= 0.5 else "hallucinated",
        "valid_refs": valid_refs,
        "hallucinated_refs": hallucinated,
        "total_refs_claimed": len(output.evidence_refs),
    }


# ── 2. Factual Consistency ────────────────────────────────────────────────────

def factual_consistency(
    narrative: str,
    expected_signals: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Checks whether numeric values mentioned in the narrative
    are consistent with the prediction signals provided.

    Strategy: extract numbers from text, match to signal values,
    check ±10% tolerance for floats.

    Score = correct facts / (correct + incorrect).
    """
    # Extract floats from narrative
    found_numbers = [float(n) for n in re.findall(r"\b\d+\.?\d*\b", narrative)]

    expected_numbers: list[float] = []
    for v in expected_signals.values():
        if isinstance(v, (int, float)):
            expected_numbers.append(float(v))

    if not expected_numbers:
        return {"score": None, "label": "unevaluable", "reason": "No numeric signals to verify"}

    matched = 0
    checked = 0
    for found in found_numbers:
        for expected in expected_numbers:
            if expected == 0.0:
                continue
            checked += 1
            if abs(found - expected) / abs(expected) <= 0.10:   # 10% tolerance
                matched += 1
                break

    score = matched / len(expected_numbers) if expected_numbers else 0.0
    score = min(1.0, score)  # cap at 1.0

    return {
        "score": round(score, 3),
        "label": "consistent" if score >= 0.7 else "inconsistent",
        "numbers_found_in_text": found_numbers,
        "expected_signal_values": expected_numbers,
        "matched_count": matched,
    }


# ── 3. Ranking Quality (Kendall's Tau) ────────────────────────────────────────

def ranking_quality(
    predicted_ranking: List[str],
    ground_truth_ranking: List[str],
) -> Dict[str, Any]:
    """
    Measures how well the predicted ranking matches a ground truth order
    using Kendall's Tau-b.

    predicted_ranking: list of topic names in predicted order (best first)
    ground_truth_ranking: list of topic names in ground truth order

    Returns tau in [-1, 1]; score is normalized to [0, 1].
    """
    # Keep only items present in both lists
    common = [t for t in predicted_ranking if t in ground_truth_ranking]
    if len(common) < 2:
        return {"score": None, "label": "unevaluable", "reason": "Too few common items"}

    gt_rank = {t: i for i, t in enumerate(ground_truth_ranking)}
    pred_order = [gt_rank[t] for t in common]   # ground-truth positions in predicted order

    # Count concordant and discordant pairs
    concordant = discordant = 0
    n = len(pred_order)
    for i in range(n):
        for j in range(i + 1, n):
            if pred_order[i] < pred_order[j]:
                concordant += 1
            elif pred_order[i] > pred_order[j]:
                discordant += 1

    total_pairs = n * (n - 1) / 2
    tau = (concordant - discordant) / total_pairs if total_pairs > 0 else 0.0
    score = (tau + 1) / 2   # normalize to [0, 1]

    return {
        "score": round(score, 3),
        "tau":   round(tau, 3),
        "label": "excellent" if score >= 0.85 else "good" if score >= 0.70 else "fair" if score >= 0.55 else "poor",
        "concordant_pairs": concordant,
        "discordant_pairs": discordant,
        "total_pairs": int(total_pairs),
        "common_items": len(common),
    }


# ── 4. Insight Usefulness ─────────────────────────────────────────────────────

def insight_usefulness(
    output: SLMOutputContract,
    context: SLMInputContext,
) -> Dict[str, Any]:
    """
    Rule-based rubric to assess insight quality:
    - Completeness: all required fields filled
    - Action-ability: recommended_action is specific (>20 chars, not generic)
    - Persona fit: narrative uses persona-appropriate vocabulary
    - Conciseness: narrative within 100–500 words
    """
    scores: Dict[str, float] = {}

    # 1. Completeness
    required = ["title", "claim", "narrative", "recommended_action"]
    filled = sum(1 for f in required if getattr(output, f, "").strip())
    scores["completeness"] = filled / len(required)

    # 2. Action-ability
    action = output.recommended_action.strip()
    is_generic = action.lower() in {
        "study this topic", "revise this", "review", "practice",
        "n/a", "none", "", "see above",
    }
    is_specific = len(action) > 20 and not is_generic
    scores["action_ability"] = 1.0 if is_specific else 0.4 if len(action) > 10 else 0.0

    # 3. Persona vocabulary fit
    persona_keywords = {
        "student": ["revise", "practice", "marks", "study", "focus", "score", "hours"],
        "teacher": ["curriculum", "emphasize", "class", "question type", "coverage"],
        "academic_planner": ["allocation", "tier", "risk", "trend", "resource"],
        "content_team": ["gap", "micro-topic", "content", "coverage", "backlog"],
        "exam_analyst": ["signal", "confidence", "anomaly", "statistical", "year-over-year"],
    }
    persona = context.persona.value if hasattr(context.persona, "value") else str(context.persona)
    kws = persona_keywords.get(persona, persona_keywords["student"])
    narrative_lower = output.narrative.lower()
    hits = sum(1 for kw in kws if kw in narrative_lower)
    scores["persona_fit"] = min(1.0, hits / max(len(kws), 1))

    # 4. Conciseness
    word_count = len(output.narrative.split())
    if 80 <= word_count <= 500:
        scores["conciseness"] = 1.0
    elif word_count < 30 or word_count > 800:
        scores["conciseness"] = 0.3
    else:
        scores["conciseness"] = 0.7

    overall = mean(scores.values())
    return {
        "score": round(overall, 3),
        "label": "excellent" if overall >= 0.85 else "good" if overall >= 0.65 else "needs_improvement",
        "breakdown": {k: round(v, 3) for k, v in scores.items()},
        "word_count": word_count,
    }


# ── 5. Topic Coverage ─────────────────────────────────────────────────────────

def topic_coverage(
    insight: InsightObject,
    important_topics: List[str],
    min_importance_rank: int = 10,
) -> Dict[str, Any]:
    """
    Measures what fraction of the top-N important topics are mentioned
    in the insight narrative (by name substring match).

    important_topics: list of topic names ordered by importance
    min_importance_rank: only check the top-N topics
    """
    target = important_topics[:min_importance_rank]
    if not target:
        return {"score": None, "label": "unevaluable"}

    text = (insight.narrative + " " + insight.claim + " " + insight.title).lower()
    mentioned = [t for t in target if t.lower() in text]

    score = len(mentioned) / len(target)
    return {
        "score": round(score, 3),
        "label": "high" if score >= 0.6 else "medium" if score >= 0.3 else "low",
        "topics_checked": len(target),
        "topics_mentioned": mentioned,
        "topics_missed": [t for t in target if t not in mentioned],
    }


# ── 6. Latency Tracker ────────────────────────────────────────────────────────

@dataclass
class LatencyTracker:
    """
    Records end-to-end latency for insight generation calls.
    Call .start() before the SLM call, .stop() after the response.
    """
    samples: List[float] = field(default_factory=list)
    _start: Optional[float] = field(default=None, repr=False)

    def start(self) -> None:
        self._start = time.perf_counter()

    def stop(self) -> float:
        if self._start is None:
            return 0.0
        elapsed = (time.perf_counter() - self._start) * 1000  # ms
        self.samples.append(elapsed)
        self._start = None
        return elapsed

    def summary(self) -> Dict[str, Any]:
        if not self.samples:
            return {"count": 0}
        return {
            "count":  len(self.samples),
            "mean_ms":   round(mean(self.samples), 1),
            "p50_ms":    round(sorted(self.samples)[len(self.samples) // 2], 1),
            "p95_ms":    round(sorted(self.samples)[int(len(self.samples) * 0.95)], 1),
            "max_ms":    round(max(self.samples), 1),
            "stddev_ms": round(stdev(self.samples), 1) if len(self.samples) > 1 else 0.0,
        }


# ── 7. Composite Evaluation Report ────────────────────────────────────────────

def evaluate_insight(
    output: SLMOutputContract,
    context: SLMInputContext,
    insight: Optional[InsightObject] = None,
    important_topics: Optional[List[str]] = None,
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run all applicable metrics and return a composite evaluation report.
    """
    grounding   = grounding_accuracy(output, context)
    factual     = factual_consistency(output.narrative, context.prediction_signals)
    usefulness  = insight_usefulness(output, context)

    scores = [
        v for v in [
            grounding.get("score"),
            factual.get("score"),
            usefulness.get("score"),
        ]
        if v is not None
    ]

    coverage_result = None
    if insight and important_topics:
        coverage_result = topic_coverage(insight, important_topics)
        cs = coverage_result.get("score")
        if cs is not None:
            scores.append(cs)

    composite = round(mean(scores), 3) if scores else None
    label = (
        "excellent" if composite and composite >= 0.85 else
        "good"      if composite and composite >= 0.70 else
        "acceptable" if composite and composite >= 0.55 else
        "poor"
    )

    report = {
        "composite_score": composite,
        "composite_label": label,
        "fallback_triggered": output.fallback_triggered,
        "is_grounded": output.is_grounded,
        "metrics": {
            "grounding":  grounding,
            "factual":    factual,
            "usefulness": usefulness,
        },
    }
    if coverage_result:
        report["metrics"]["coverage"] = coverage_result
    if latency_ms is not None:
        report["latency_ms"] = round(latency_ms, 1)

    return report
