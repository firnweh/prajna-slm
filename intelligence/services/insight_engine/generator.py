"""
SLM Insight Generator
======================
Orchestrates the full insight generation pipeline:
1. Build SLM input context from prediction data + RAG evidence
2. Choose the correct prompt template
3. Call the SLM provider
4. Parse and validate the output
5. Attach evidence and grounding metadata
6. Return typed InsightObject

This is the ONLY service that calls the SLM.
All inputs are structured. No free-form text goes in unfiltered.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from packages.schemas.contracts import (
    CopilotRequest, InsightRequest, SLMInputContext, SLMOutputContract,
)
from packages.schemas.intelligence import (
    EvidenceObject, EvidenceType, InsightObject, InsightType,
    PersonaType, RevisionUrgency,
)
from packages.schemas.prediction import ExamType, HierarchyScope, PredictionBatch
from packages.prompts.system import build_system_prompt, build_anti_hallucination_block
from packages.prompts.templates import build_prompt
from packages.utils.confidence import evidence_weighted_confidence
from .slm_provider import SLMProvider

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Core insight generation service.
    Stateless — each call is independent.
    """

    def __init__(
        self,
        slm_provider: SLMProvider,
        rag_retriever=None,   # Optional RAGRetriever instance
        min_evidence_for_grounding: int = 1,
    ):
        self.slm          = slm_provider
        self.rag          = rag_retriever
        self.min_evidence = min_evidence_for_grounding

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_topic_insight(
        self,
        micro_topic_name: str,
        prediction_signals: Dict[str, Any],
        exam_type: ExamType,
        target_year: int,
        persona: PersonaType,
        subject: str,
        chapter: str,
    ) -> InsightObject:
        """Explain why a micro-topic is important."""
        evidence  = await self._retrieve_evidence(micro_topic_name, exam_type, subject, chapter)
        ranked    = self._signals_to_ranked_list(prediction_signals)
        ctx       = self._build_context(
            task="topic_importance",
            scope=HierarchyScope.MICRO_TOPIC,
            scope_name=micro_topic_name,
            exam_type=exam_type,
            target_year=target_year,
            persona=persona,
            prediction_signals=prediction_signals,
            ranked_items=ranked,
            retrieved_passages=evidence,
            subject=subject,
            chapter=chapter,
        )
        return await self._generate_insight(
            ctx=ctx,
            insight_type=InsightType.TOPIC_IMPORTANCE,
            scope=HierarchyScope.MICRO_TOPIC,
            scope_name=micro_topic_name,
            parent_chain=[subject, chapter],
            evidence_objects=self._passages_to_evidence(evidence),
            persona=persona,
        )

    async def generate_chapter_insight(
        self,
        chapter: str,
        subject: str,
        prediction_signals: Dict[str, Any],
        ranked_topics: List[Dict[str, Any]],
        exam_type: ExamType,
        target_year: int,
        persona: PersonaType,
    ) -> InsightObject:
        """Generate chapter intelligence summary."""
        evidence = await self._retrieve_evidence(chapter, exam_type, subject, chapter)
        ctx = self._build_context(
            task="chapter_summary",
            scope=HierarchyScope.CHAPTER,
            scope_name=chapter,
            exam_type=exam_type,
            target_year=target_year,
            persona=persona,
            prediction_signals=prediction_signals,
            ranked_items=ranked_topics,
            retrieved_passages=evidence,
            subject=subject,
            chapter=chapter,
        )
        return await self._generate_insight(
            ctx=ctx,
            insight_type=InsightType.CHAPTER_SUMMARY,
            scope=HierarchyScope.CHAPTER,
            scope_name=chapter,
            parent_chain=[subject],
            evidence_objects=self._passages_to_evidence(evidence),
            persona=persona,
        )

    async def generate_subject_strategy(
        self,
        subject: str,
        prediction_signals: Dict[str, Any],
        ranked_chapters: List[Dict[str, Any]],
        cluster_summary: str,
        trend_summary: str,
        exam_type: ExamType,
        target_year: int,
        persona: PersonaType,
        available_days: Optional[int] = None,
    ) -> InsightObject:
        """Generate full subject revision strategy."""
        evidence = await self._retrieve_evidence(subject, exam_type, subject)
        ctx = self._build_context(
            task="subject_strategy",
            scope=HierarchyScope.SUBJECT,
            scope_name=subject,
            exam_type=exam_type,
            target_year=target_year,
            persona=persona,
            prediction_signals=prediction_signals,
            ranked_items=ranked_chapters,
            retrieved_passages=evidence,
            subject=subject,
            cluster_summary=cluster_summary,
            trend_summary=trend_summary,
            available_days=available_days,
        )
        return await self._generate_insight(
            ctx=ctx,
            insight_type=InsightType.SUBJECT_STRATEGY,
            scope=HierarchyScope.SUBJECT,
            scope_name=subject,
            parent_chain=[],
            evidence_objects=self._passages_to_evidence(evidence),
            persona=persona,
        )

    async def generate_exam_brief(
        self,
        exam_type: ExamType,
        target_year: int,
        ranked_items: List[Dict[str, Any]],
        trend_summary: str,
        cluster_summary: str,
        prediction_signals: Dict[str, Any],
        persona: PersonaType,
        compare_year: Optional[int] = None,
    ) -> InsightObject:
        """Generate cross-subject exam brief."""
        evidence = await self._retrieve_evidence(
            f"{exam_type} exam brief", exam_type
        )
        ctx = self._build_context(
            task="exam_brief",
            scope=HierarchyScope.SUBJECT,
            scope_name=f"{exam_type.upper()} {target_year}",
            exam_type=exam_type,
            target_year=target_year,
            persona=persona,
            prediction_signals=prediction_signals,
            ranked_items=ranked_items,
            retrieved_passages=evidence,
            trend_summary=trend_summary,
            cluster_summary=cluster_summary,
            compare_year=compare_year or (target_year - 1),
            subjects_covered="All subjects",
        )
        return await self._generate_insight(
            ctx=ctx,
            insight_type=InsightType.EXAM_BRIEF,
            scope=HierarchyScope.SUBJECT,
            scope_name=f"{exam_type.upper()} {target_year} Exam Brief",
            parent_chain=[],
            evidence_objects=self._passages_to_evidence(evidence),
            persona=persona,
        )

    async def answer_copilot_question(
        self,
        request: CopilotRequest,
        batch: PredictionBatch,
    ) -> InsightObject:
        """Answer a natural language question grounded in prediction data."""
        from packages.utils.hierarchy import get_top_n_micro_topics
        # Fetch more topics then deduplicate by name, keeping the highest-probability entry
        top_micros_raw = get_top_n_micro_topics(batch, n=40)
        seen: dict = {}
        for m in top_micros_raw:
            key = m.micro_topic_name.lower().strip()
            if key not in seen or m.importance_probability > seen[key].importance_probability:
                seen[key] = m
        top_micros = sorted(seen.values(), key=lambda x: x.importance_probability, reverse=True)[:15]

        prediction_signals = {
            "avg_importance": sum(m.importance_probability for m in top_micros) / max(len(top_micros), 1),
            "top_topics":     [m.micro_topic_name for m in top_micros[:5]],
            "exam_type":      request.exam_type,
            "target_year":    request.target_year,
        }

        ranked = [
            {
                "name":                   m.micro_topic_name,
                "importance_probability": m.importance_probability,
                "confidence_score":       m.confidence_score,
                "trend_direction":        m.topic_trend_score,
                "chapter":                m.chapter,
                "subject":                m.subject,
            }
            for m in top_micros
        ]

        evidence = await self._retrieve_evidence(
            request.question, request.exam_type,
            subject=request.subject_filter,
        )

        ctx = self._build_context(
            task="copilot_answer",
            scope=HierarchyScope.SUBJECT,
            scope_name="General Query",
            exam_type=request.exam_type,
            target_year=request.target_year,
            persona=request.persona,
            prediction_signals=prediction_signals,
            ranked_items=ranked,
            retrieved_passages=evidence,
            question=request.question,
            conversation_history=request.conversation_history,
            subject_filter=request.subject_filter,
        )

        return await self._generate_insight(
            ctx=ctx,
            insight_type=InsightType.EXAM_BRIEF,   # generic insight for copilot
            scope=HierarchyScope.SUBJECT,
            scope_name="Copilot Answer",
            parent_chain=[],
            evidence_objects=self._passages_to_evidence(evidence),
            persona=request.persona,
        )

    # ── Core generation pipeline ───────────────────────────────────────────────

    async def _generate_insight(
        self,
        ctx:            Dict[str, Any],
        insight_type:   InsightType,
        scope:          HierarchyScope,
        scope_name:     str,
        parent_chain:   List[str],
        evidence_objects: List[EvidenceObject],
        persona:        PersonaType,
    ) -> InsightObject:
        """
        The core pipeline:
        1. Build system + user prompts
        2. Call SLM
        3. Parse output
        4. Attach evidence and metadata
        5. Return InsightObject
        """
        t_start = time.time()

        system_prompt = build_system_prompt(persona.value)
        # Add anti-hallucination block
        forbidden = ctx.get("forbidden_topics", [])
        system_prompt += build_anti_hallucination_block(forbidden)

        user_prompt = build_prompt(ctx["task"], ctx)

        # Check if evidence is sufficient for grounding
        is_grounded = len(evidence_objects) >= self.min_evidence

        logger.info(
            f"Generating insight: type={insight_type}, scope={scope_name}, "
            f"evidence={len(evidence_objects)}, grounded={is_grounded}"
        )

        try:
            raw_output = await self.slm.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1200,
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"SLM generation failed: {e}", exc_info=True)
            raw_output = self._fallback_response(scope_name, str(e))

        # Parse and validate
        slm_out = SLMOutputContract(**raw_output)

        # Compute final confidence with evidence weighting
        base_conf = slm_out.confidence
        evidence_dicts = [e.dict() for e in evidence_objects]
        final_conf = evidence_weighted_confidence(base_conf, evidence_dicts)

        latency_ms = round((time.time() - t_start) * 1000)
        logger.info(f"Insight generated in {latency_ms}ms, confidence={final_conf:.2f}")

        # Determine urgency
        urgency = None
        if final_conf >= 0.70 and scope in (HierarchyScope.MICRO_TOPIC, HierarchyScope.TOPIC):
            urgency = RevisionUrgency.HIGH
        elif final_conf >= 0.50:
            urgency = RevisionUrgency.MEDIUM

        return InsightObject(
            insight_id          = str(uuid.uuid4()),
            insight_type        = insight_type,
            persona             = persona,
            title               = slm_out.title,
            scope               = scope,
            scope_name          = scope_name,
            parent_chain        = parent_chain,
            claim               = slm_out.claim,
            narrative           = slm_out.narrative,
            recommended_action  = slm_out.recommended_action,
            evidence            = evidence_objects,
            confidence          = final_conf,
            is_grounded         = slm_out.is_grounded and is_grounded,
            supporting_metrics  = {"latency_ms": latency_ms, **ctx.get("prediction_signals", {})},
            urgency             = urgency,
            tags                = slm_out.tags,
            slm_model_id        = getattr(self.slm, "model", "unknown"),
            prompt_version      = "v1",
        )

    # ── Context builder ────────────────────────────────────────────────────────

    @staticmethod
    def _build_context(task: str, **kwargs) -> Dict[str, Any]:
        ctx = {"task": task}
        ctx.update(kwargs)
        # Ensure exam_type and persona are strings for template rendering
        if hasattr(ctx.get("exam_type"), "value"):
            ctx["exam_type"] = ctx["exam_type"].value
        if hasattr(ctx.get("persona"), "value"):
            ctx["persona"] = ctx["persona"].value
        return ctx

    # ── RAG retrieval ──────────────────────────────────────────────────────────

    async def _retrieve_evidence(
        self,
        query: str,
        exam_type: ExamType,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant evidence from RAG store."""
        if self.rag is None:
            return []
        try:
            results = await self.rag.retrieve(
                query=query,
                exam_type=str(exam_type),
                subject=subject,
                chapter=chapter,
                top_k=top_k,
            )
            return results
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return []

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _signals_to_ranked_list(signals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert flat prediction signals dict to a ranked list for templates."""
        return [{"name": k, "value": v} for k, v in signals.items()]

    @staticmethod
    def _passages_to_evidence(passages: List[Dict]) -> List[EvidenceObject]:
        """Convert RAG passages to EvidenceObject list."""
        evidence = []
        for i, p in enumerate(passages):
            evidence.append(EvidenceObject(
                evidence_id     = p.get("id", f"E{i+1}"),
                evidence_type   = EvidenceType(p.get("evidence_type", "retrieved_chunk")),
                source_name     = p.get("source", "Retrieved Document"),
                source_url      = p.get("url"),
                excerpt         = p.get("text", p.get("content", ""))[:500],
                relevance_score = float(p.get("score", p.get("relevance_score", 0.5))),
                metadata        = {k: v for k, v in p.items()
                                   if k not in ("id", "text", "content", "score", "source")},
            ))
        return evidence

    @staticmethod
    def _fallback_response(scope_name: str, error: str) -> Dict[str, Any]:
        return {
            "title":              f"Analysis Unavailable: {scope_name}",
            "claim":              "The insight engine encountered an error.",
            "narrative":          f"Could not generate insight: {error[:200]}",
            "recommended_action": "Retry the request or contact support.",
            "confidence":         0.0,
            "is_grounded":        False,
            "evidence_refs":      [],
            "tags":               ["error", "fallback"],
            "fallback_triggered": True,
            "fallback_message":   error[:200],
        }
