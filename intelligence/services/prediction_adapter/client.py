"""
PRAJNA Prediction Adapter
==========================
Wraps the existing PRAJNA prediction engine.
Normalizes its output into the canonical MicroTopicPrediction schema.

The adapter supports two modes:
1. LOCAL  — calls prediction functions directly (same process)
2. HTTP   — calls a REST endpoint if the engine is deployed separately

This is the ONLY place that knows about PRAJNA internals.
The rest of the intelligence layer is engine-agnostic.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── Path setup for local mode ─────────────────────────────────────────────────
PRAJNA_ROOT = Path(__file__).parents[4]   # /Users/aman/exam-predictor
sys.path.insert(0, str(PRAJNA_ROOT))

from packages.schemas.prediction import (
    AppearancePattern, ExamType, MicroTopicPrediction,
    TrendDirection, WeightageBand,
)
from packages.utils.hierarchy import score_to_band, trend_score_to_direction


class PredictionAdapterConfig:
    mode:           str  = "local"     # "local" | "http"
    http_base_url:  str  = "http://localhost:8000"
    http_timeout:   int  = 30
    cache_ttl_sec:  int  = 3600        # 1 hour
    batch_size:     int  = 100


class PredictionAdapter:
    """
    Wraps the PRAJNA prediction engine and returns normalized
    MicroTopicPrediction objects.
    """

    def __init__(self, config: Optional[PredictionAdapterConfig] = None):
        self.config = config or PredictionAdapterConfig()
        self._cache: Dict[str, Any] = {}
        self._local_engine = None

    # ── Engine initialization ─────────────────────────────────────────────────

    def _init_local_engine(self):
        """Lazy-load the PRAJNA SLM and prediction modules."""
        if self._local_engine is not None:
            return

        try:
            from analysis.slm_model import PRAJNAPredictor
            from utils.db import get_questions_df
            logger.info("PRAJNA SLM loaded successfully (local mode)")
            self._local_engine = {
                "predictor_class": PRAJNAPredictor,
                "get_df": get_questions_df,
            }
        except ImportError as e:
            logger.warning(f"Could not load PRAJNA SLM: {e}. Falling back to v3 predictor.")
            try:
                from analysis.predictor_v3 import predict_topics
                self._local_engine = {"predict_v3": predict_topics}
                logger.info("Using predictor_v3 as fallback")
            except ImportError:
                logger.error("No PRAJNA predictor available. Using mock data.")
                self._local_engine = {"mock": True}

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_predictions(
        self,
        exam_type: ExamType,
        target_year: int,
        subject: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[MicroTopicPrediction]:
        """
        Fetch predictions from the PRAJNA engine and normalize them.
        Results are cached for config.cache_ttl_sec seconds.
        """
        cache_key = self._cache_key(exam_type, target_year, subject)
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["ts"] < self.config.cache_ttl_sec:
                logger.debug(f"Cache hit: {cache_key}")
                return entry["data"]

        if self.config.mode == "local":
            predictions = await self._fetch_local(exam_type, target_year, subject)
        else:
            predictions = await self._fetch_http(exam_type, target_year, subject)

        self._cache[cache_key] = {"data": predictions, "ts": time.time()}
        return predictions

    def get_predictions_sync(
        self,
        exam_type: ExamType,
        target_year: int,
        subject: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[MicroTopicPrediction]:
        """Synchronous version for scripts and tests."""
        return asyncio.get_event_loop().run_until_complete(
            self.get_predictions(exam_type, target_year, subject, force_refresh)
        )

    # ── Local fetch ───────────────────────────────────────────────────────────

    async def _fetch_local(
        self,
        exam_type: ExamType,
        target_year: int,
        subject: Optional[str],
    ) -> List[MicroTopicPrediction]:
        self._init_local_engine()

        if "mock" in self._local_engine:
            return self._generate_mock_predictions(exam_type, target_year, subject)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_local_prediction,
            exam_type, target_year, subject,
        )

    def _run_local_prediction(
        self,
        exam_type: ExamType,
        target_year: int,
        subject: Optional[str],
    ) -> List[MicroTopicPrediction]:
        """
        Calls PRAJNA's existing prediction pipeline and normalizes output.
        """
        try:
            if "predictor_class" in self._local_engine:
                return self._run_slm_prediction(exam_type, target_year, subject)
            elif "predict_v3" in self._local_engine:
                return self._run_v3_prediction(exam_type, target_year, subject)
        except Exception as e:
            logger.error(f"Local prediction failed: {e}", exc_info=True)
            return self._generate_mock_predictions(exam_type, target_year, subject)

    def _run_slm_prediction(self, exam_type, target_year, subject):
        """Calls PRAJNAPredictor (slm_model.py)."""
        PRAJNAPredictor = self._local_engine["predictor_class"]
        get_df = self._local_engine["get_df"]

        exam_map = {
            ExamType.NEET:         "NEET",
            ExamType.JEE_MAIN:     "JEE Main",
            ExamType.JEE_ADVANCED: "JEE Advanced",
        }
        exam_str = exam_map.get(exam_type, "NEET")

        predictor = PRAJNAPredictor(exam_filter=exam_str)
        df = get_df()
        predictor.train(df, target_year=target_year)
        raw_preds = predictor.predict(df, target_year=target_year, K=50)

        return [self._normalize_slm_output(r, exam_type, target_year, subject)
                for r in raw_preds if subject is None or r.get("subject","").lower() == subject.lower()]

    def _run_v3_prediction(self, exam_type, target_year, subject):
        """Calls predictor_v3.predict_topics."""
        predict_topics = self._local_engine["predict_v3"]
        raw = predict_topics(exam_type=str(exam_type), target_year=target_year, K=50)
        return [self._normalize_v3_output(r, exam_type, target_year, subject)
                for r in raw if subject is None or r.get("subject","").lower() == (subject or "").lower()]

    # ── Normalization ─────────────────────────────────────────────────────────

    def _normalize_slm_output(
        self,
        raw: Dict[str, Any],
        exam_type: ExamType,
        target_year: int,
        subject_filter: Optional[str],
    ) -> MicroTopicPrediction:
        """
        Normalize PRAJNA SLM output dict → MicroTopicPrediction.
        Field mapping is based on slm_model.py output schema.
        """
        # PRAJNA SLM returns: chapter, subject, appear_prob, exp_qs, difficulty, features
        chapter  = raw.get("chapter", raw.get("topic", "Unknown"))
        subject  = raw.get("subject", "Unknown")
        appear_p = float(raw.get("appear_prob", raw.get("importance_probability", 0.5)))
        trend_s  = float(raw.get("trend_slope",  raw.get("topic_trend_score", 0.0)))
        recur_s  = float(raw.get("recurrence",   raw.get("recurrence_score", 0.5)))
        conf_s   = float(raw.get("confidence",   appear_p * 0.9))
        freq     = float(raw.get("frequency",    raw.get("historical_frequency", 0.5)))
        gap_yrs  = int(raw.get("gap_years", 0))

        appearance_pattern = self._infer_appearance_pattern(gap_yrs)

        return MicroTopicPrediction(
            prediction_id     = str(uuid4()),
            micro_topic_id    = hashlib.md5(f"{exam_type}:{chapter}:{target_year}".encode()).hexdigest()[:12],
            micro_topic_name  = raw.get("micro_topic", chapter),
            topic             = raw.get("topic", chapter),
            chapter           = chapter,
            subject           = subject,
            exam_type         = exam_type,
            target_year       = target_year,
            importance_probability   = appear_p,
            importance_rank          = int(raw.get("rank", 999)),
            expected_weightage_band  = score_to_band(appear_p),
            recurrence_score         = recur_s,
            recent_appearance_pattern = appearance_pattern,
            historical_frequency     = freq,
            topic_trend_score        = trend_s,
            syllabus_coverage_signal = float(raw.get("syllabus_signal", 0.7)),
            confidence_score         = conf_s,
            related_topic_clusters   = [],
        )

    def _normalize_v3_output(self, raw, exam_type, target_year, subject_filter):
        """Normalize predictor_v3 output."""
        return self._normalize_slm_output(raw, exam_type, target_year, subject_filter)

    @staticmethod
    def _infer_appearance_pattern(gap_years: int) -> AppearancePattern:
        if gap_years == 0:   return AppearancePattern.APPEARED_LAST_YEAR
        if gap_years == 1:   return AppearancePattern.GAP_1_YEAR
        if gap_years == 2:   return AppearancePattern.GAP_2_YEARS
        if gap_years >= 5:   return AppearancePattern.LONG_ABSENT
        return AppearancePattern.GAP_3_PLUS

    # ── HTTP fetch ────────────────────────────────────────────────────────────

    async def _fetch_http(self, exam_type, target_year, subject):
        """Call remote prediction engine via HTTP."""
        import httpx
        params = {"exam_type": exam_type, "target_year": target_year}
        if subject:
            params["subject"] = subject
        async with httpx.AsyncClient(timeout=self.config.http_timeout) as client:
            resp = await client.get(
                f"{self.config.http_base_url}/predict",
                params=params,
            )
            resp.raise_for_status()
            raw_list = resp.json().get("predictions", [])
        return [self._normalize_slm_output(r, exam_type, target_year, subject) for r in raw_list]

    # ── Mock data (dev/test) ──────────────────────────────────────────────────

    def _generate_mock_predictions(
        self, exam_type: ExamType, target_year: int, subject: Optional[str]
    ) -> List[MicroTopicPrediction]:
        """
        Synthetic predictions for development and testing.
        Mirrors the structure the real engine produces.
        """
        import random
        rng = random.Random(42)

        MOCK_TOPICS = {
            "Physics":    ["Electrostatics", "Optics", "Rotational Motion", "Thermodynamics", "Kinematics"],
            "Chemistry":  ["Chemical Bonding", "Organic Chemistry Basics", "Equilibrium", "Electrochemistry"],
            "Biology":    ["Human Physiology", "Genetics", "Cell Biology", "Reproduction", "Ecology"],
            "Mathematics":["Calculus", "Coordinate Geometry", "Algebra", "Probability", "Vectors"],
        }
        subjects = [subject] if subject else list(MOCK_TOPICS.keys())
        mock_micros = [
            "Newton's Laws", "Wave Optics", "Photoelectric Effect",
            "Mendel's Laws", "Mole Concept", "Limit and Continuity",
        ]

        predictions = []
        rank = 1
        for subj in subjects:
            for chapter in MOCK_TOPICS.get(subj, []):
                ip = rng.uniform(0.3, 0.95)
                predictions.append(MicroTopicPrediction(
                    prediction_id    = str(uuid4()),
                    micro_topic_id   = f"mock-{subj[:3]}-{chapter[:5]}-{rank}",
                    micro_topic_name = rng.choice(mock_micros),
                    topic            = chapter,
                    chapter          = chapter,
                    subject          = subj,
                    exam_type        = exam_type,
                    target_year      = target_year,
                    importance_probability  = ip,
                    importance_rank         = rank,
                    expected_weightage_band = score_to_band(ip),
                    recurrence_score        = rng.uniform(0.4, 0.9),
                    recent_appearance_pattern = AppearancePattern.APPEARED_LAST_YEAR,
                    historical_frequency    = rng.uniform(0.3, 0.8),
                    topic_trend_score       = rng.uniform(-0.3, 0.5),
                    syllabus_coverage_signal = rng.uniform(0.5, 1.0),
                    confidence_score        = ip * rng.uniform(0.85, 1.0),
                ))
                rank += 1
        return predictions

    @staticmethod
    def _cache_key(exam_type, target_year, subject) -> str:
        return f"{exam_type}:{target_year}:{subject or 'all'}"
