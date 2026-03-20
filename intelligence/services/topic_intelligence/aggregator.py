"""
Topic Intelligence Aggregator
==============================
Takes raw MicroTopicPredictions from the adapter and produces the full
intelligence tree: ranked topics, chapter summaries, subject strategies.

This is pure analytics — no SLM calls here.
The output of this layer feeds the SLM Insight Engine.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from packages.schemas.prediction import (
    ExamType, MicroTopicPrediction, PredictionBatch,
)
from packages.schemas.intelligence import (
    ChapterSummaryObject, RevisionPriorityObject, RevisionUrgency,
    SubjectStrategySummary, TrendShiftReport,
)
from packages.utils.hierarchy import (
    build_prediction_batch, get_top_n_micro_topics,
    score_to_band, trend_score_to_direction,
)
from packages.utils.confidence import (
    compute_priority_score, priority_score_to_urgency,
    evidence_weighted_confidence,
)

logger = logging.getLogger(__name__)


class TopicIntelligenceAggregator:
    """
    Core intelligence aggregation service.
    All methods are synchronous and deterministic — no LLM calls.
    """

    def __init__(self):
        self._batch_cache: Dict[str, PredictionBatch] = {}

    # ── Batch building ────────────────────────────────────────────────────────

    def build_batch(
        self,
        micro_predictions: List[MicroTopicPrediction],
        batch_id: Optional[str] = None,
    ) -> PredictionBatch:
        """Aggregate flat micro-topic predictions into the full hierarchy."""
        bid = batch_id or str(uuid4())
        batch = build_prediction_batch(micro_predictions, bid)
        self._batch_cache[bid] = batch
        logger.info(
            f"Built batch {bid}: "
            f"{len(batch.subject_predictions)} subjects, "
            f"{batch.total_chapters_predicted} chapters, "
            f"{batch.total_micro_topics_predicted} micro-topics"
        )
        return batch

    # ── Revision priority ranking ─────────────────────────────────────────────

    def rank_revision_priorities(
        self,
        batch: PredictionBatch,
        subject: Optional[str] = None,
        top_n: int = 30,
    ) -> List[RevisionPriorityObject]:
        """
        Produce a ranked list of revision priorities across all hierarchy levels.
        Uses compute_priority_score for consistent, signal-based ranking.
        """
        priorities: List[RevisionPriorityObject] = []

        target_subjects = [
            s for s in batch.subject_predictions
            if subject is None or s.subject.lower() == subject.lower()
        ]

        for sp in target_subjects:
            for cp in sp.chapter_predictions:
                for tp in cp.topic_predictions:
                    for mp in tp.micro_topic_predictions:
                        prio_score = compute_priority_score(
                            importance_probability = mp.importance_probability,
                            confidence             = mp.confidence_score,
                            recurrence_score       = mp.recurrence_score,
                            trend_score            = mp.topic_trend_score,
                            syllabus_coverage      = mp.syllabus_coverage_signal,
                        )
                        urgency = priority_score_to_urgency(prio_score)

                        reasons = self._build_key_reasons(mp)
                        risk    = self._estimate_risk(mp, cp.chapter)

                        priorities.append(RevisionPriorityObject(
                            scope        = "micro_topic",
                            scope_name   = mp.micro_topic_name,
                            parent_chain = [mp.subject, mp.chapter, mp.topic],
                            exam_type    = mp.exam_type,
                            target_year  = mp.target_year,
                            urgency      = RevisionUrgency(urgency),
                            priority_score = prio_score,
                            importance_probability = mp.importance_probability,
                            confidence   = mp.confidence_score,
                            expected_weightage_band = mp.expected_weightage_band,
                            trend_direction = trend_score_to_direction(mp.topic_trend_score),
                            key_reasons  = reasons,
                            risk_if_skipped = risk,
                            estimated_study_hours = self._estimate_study_hours(mp),
                        ))

        priorities.sort(key=lambda p: p.priority_score, reverse=True)
        return priorities[:top_n]

    # ── Chapter summary building ───────────────────────────────────────────────

    def build_chapter_summary(
        self,
        batch: PredictionBatch,
        subject: str,
        chapter: str,
    ) -> Optional[ChapterSummaryObject]:
        """Build a structured chapter intelligence summary (pre-SLM)."""
        from packages.utils.hierarchy import get_chapter_from_batch

        cp = get_chapter_from_batch(batch, subject, chapter)
        if cp is None:
            logger.warning(f"Chapter '{chapter}' not found in batch for subject '{subject}'")
            return None

        importance_tier = "A" if cp.composite_importance >= 0.65 else \
                          "B" if cp.composite_importance >= 0.35 else "C"

        expected_qs = self._estimate_expected_questions(cp.composite_importance)
        urgency = RevisionUrgency(priority_score_to_urgency(cp.composite_importance * 100))

        top_priority_topics = self.rank_revision_priorities(
            batch=batch, subject=subject, top_n=50
        )
        chapter_priorities = [
            p for p in top_priority_topics
            if len(p.parent_chain) >= 2 and p.parent_chain[1] == chapter
        ][:5]

        key_micro_topics = [p.scope_name for p in chapter_priorities[:5]]

        return ChapterSummaryObject(
            chapter       = chapter,
            subject       = subject,
            exam_type     = batch.exam_type,
            target_year   = batch.target_year,
            importance_tier = importance_tier,
            composite_importance = cp.composite_importance,
            expected_questions   = expected_qs,
            revision_priority    = urgency,
            trend_direction      = cp.trend_direction,
            top_priority_topics  = chapter_priorities,
            key_micro_topics     = key_micro_topics,
            confidence           = cp.composite_confidence,
        )

    # ── Subject strategy building ─────────────────────────────────────────────

    def build_subject_strategy(
        self,
        batch: PredictionBatch,
        subject: str,
        available_days: Optional[int] = None,
    ) -> Optional[SubjectStrategySummary]:
        """Build structured subject strategy (pre-SLM)."""
        sp = next(
            (s for s in batch.subject_predictions if s.subject.lower() == subject.lower()),
            None
        )
        if sp is None:
            logger.warning(f"Subject '{subject}' not found in batch")
            return None

        sorted_chapters = sorted(
            sp.chapter_predictions, key=lambda c: c.composite_importance, reverse=True
        )

        must_revise    = [c.chapter for c in sorted_chapters if c.composite_importance >= 0.65]
        should_revise  = [c.chapter for c in sorted_chapters if 0.35 <= c.composite_importance < 0.65]
        optional       = [c.chapter for c in sorted_chapters if c.composite_importance < 0.35]

        top_5_micros = [
            m.micro_topic_name
            for m in get_top_n_micro_topics(batch, subject=subject, n=5)
        ]

        study_hours = self._recommend_study_hours(sp.composite_importance, available_days)
        expected_marks = self._estimate_marks_coverage(sp)

        priorities = self.rank_revision_priorities(batch, subject=subject, top_n=20)

        chapter_summaries = []
        for cp in sorted_chapters[:8]:   # top 8 chapters get full summaries
            cs = self.build_chapter_summary(batch, subject, cp.chapter)
            if cs:
                chapter_summaries.append(cs)

        return SubjectStrategySummary(
            subject       = subject,
            exam_type     = batch.exam_type,
            target_year   = batch.target_year,
            subject_rank  = sp.subject_rank,
            overall_importance = sp.composite_importance,
            recommended_study_hours = study_hours,
            expected_marks_coverage = expected_marks,
            must_revise_chapters   = must_revise,
            should_revise_chapters = should_revise,
            optional_chapters      = optional,
            top_5_micro_topics     = top_5_micros,
            priority_objects       = priorities,
            chapter_summaries      = chapter_summaries,
            confidence             = sp.composite_confidence,
        )

    # ── Trend shift analysis ───────────────────────────────────────────────────

    def detect_trend_shifts(
        self,
        current_batch: PredictionBatch,
        previous_batch: PredictionBatch,
        subject: Optional[str] = None,
        delta_threshold: float = 0.15,
    ) -> TrendShiftReport:
        """
        Compare two prediction batches to detect significant topic shifts.
        """
        curr_idx = {
            mt_id: pred
            for mt_id, pred in current_batch.micro_topic_index.items()
            if subject is None or pred.subject.lower() == (subject or "").lower()
        }
        prev_idx = {
            mt_id: pred
            for mt_id, pred in previous_batch.micro_topic_index.items()
            if subject is None or pred.subject.lower() == (subject or "").lower()
        }

        rising, declining = [], []
        new_topics, dropped_topics = [], []

        for mt_id, curr_pred in curr_idx.items():
            if mt_id in prev_idx:
                prev_pred = prev_idx[mt_id]
                delta = curr_pred.importance_probability - prev_pred.importance_probability
                if delta >= delta_threshold:
                    rising.append({
                        "name":          curr_pred.micro_topic_name,
                        "chapter":       curr_pred.chapter,
                        "subject":       curr_pred.subject,
                        "current":       curr_pred.importance_probability,
                        "previous":      prev_pred.importance_probability,
                        "delta":         round(delta, 3),
                        "trend_score":   curr_pred.topic_trend_score,
                    })
                elif delta <= -delta_threshold:
                    declining.append({
                        "name":     curr_pred.micro_topic_name,
                        "chapter":  curr_pred.chapter,
                        "subject":  curr_pred.subject,
                        "current":  curr_pred.importance_probability,
                        "previous": prev_pred.importance_probability,
                        "delta":    round(delta, 3),
                    })
            else:
                new_topics.append(curr_pred.micro_topic_name)

        for mt_id, prev_pred in prev_idx.items():
            if mt_id not in curr_idx:
                dropped_topics.append(prev_pred.micro_topic_name)

        rising.sort(key=lambda x: x["delta"], reverse=True)
        declining.sort(key=lambda x: x["delta"])

        return TrendShiftReport(
            report_id     = str(uuid4()),
            exam_type     = current_batch.exam_type,
            current_year  = current_batch.target_year,
            compare_year  = previous_batch.target_year,
            rising_topics = rising,
            declining_topics = declining,
            new_topics    = new_topics,
            dropped_topics = dropped_topics,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_key_reasons(mp: MicroTopicPrediction) -> List[str]:
        reasons = []
        if mp.importance_probability >= 0.75:
            reasons.append(f"High appearance probability ({mp.importance_probability:.0%})")
        if mp.recurrence_score >= 0.70:
            reasons.append(f"Strong recurrence pattern ({mp.recurrence_score:.0%} recurrence score)")
        if mp.topic_trend_score > 0.20:
            reasons.append(f"Rising trend in recent exams")
        if mp.recent_appearance_pattern in ("appeared_last_year", "appeared_last_2_years"):
            reasons.append(f"Appeared in {mp.recent_appearance_pattern.replace('_', ' ')}")
        if mp.recent_appearance_pattern in ("gap_3_plus_years", "long_absent"):
            reasons.append(f"Long gap — due for return ({mp.recent_appearance_pattern.replace('_', ' ')})")
        if mp.syllabus_coverage_signal >= 0.80:
            reasons.append(f"High syllabus coverage signal ({mp.syllabus_coverage_signal:.0%})")
        return reasons[:3]

    @staticmethod
    def _estimate_risk(mp: MicroTopicPrediction, chapter: str) -> str:
        marks_est = mp.importance_probability * 5  # rough estimate
        if marks_est >= 3:
            return f"Skipping this micro-topic risks ~{marks_est:.0f} marks from {chapter}"
        return f"Low risk if skipped — estimated <2 marks from {chapter}"

    @staticmethod
    def _estimate_study_hours(mp: MicroTopicPrediction) -> float:
        base = mp.importance_probability * 4.0
        if mp.topic_trend_score > 0.2:
            base *= 1.2
        return round(max(0.5, min(6.0, base)), 1)

    @staticmethod
    def _estimate_expected_questions(importance: float) -> str:
        if importance >= 0.80: return "5+ questions"
        if importance >= 0.60: return "3–5 questions"
        if importance >= 0.35: return "1–3 questions"
        return "0–1 questions"

    @staticmethod
    def _recommend_study_hours(importance: float, available_days: Optional[int]) -> float:
        base = importance * 40  # max 40 hours for most important subject
        if available_days and available_days < 30:
            # Scale down for compressed timeline
            base *= (available_days / 30)
        return round(max(5.0, min(40.0, base)), 1)

    @staticmethod
    def _estimate_marks_coverage(sp) -> str:
        import random
        rng = random.Random(hash(sp.subject))
        base = int(sp.composite_importance * 60)
        lo = max(1, base - rng.randint(3, 7))
        hi = base + rng.randint(2, 5)
        return f"{lo}–{hi} marks"
