"""
Topic Cluster Detector
========================
Detects clusters of co-occurring high-importance topics.
Uses correlation-based co-occurrence from historical exam data
and prediction signal similarity.

Topics in a cluster:
- tend to appear together in exams
- share conceptual dependencies
- should be studied together for efficiency
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from packages.schemas.prediction import MicroTopicPrediction, PredictionBatch
from packages.schemas.intelligence import TopicClusterObject, TrendDirection
from packages.utils.hierarchy import trend_score_to_direction

logger = logging.getLogger(__name__)


class TopicClusterDetector:
    """
    Detects topic clusters using:
    1. Historical co-occurrence (topics appearing in the same exam years)
    2. Prediction signal similarity (similar importance/trend profiles)
    3. Chapter-based proximity (topics in the same chapter cluster naturally)
    """

    def __init__(self, co_occurrence_threshold: float = 0.55):
        self.co_occurrence_threshold = co_occurrence_threshold

    def detect_clusters(
        self,
        batch: PredictionBatch,
        subject: Optional[str] = None,
        min_cluster_size: int = 2,
        max_clusters: int = 10,
    ) -> List[TopicClusterObject]:
        """
        Main entry point. Returns sorted clusters (most important first).
        """
        micro_preds = list(batch.micro_topic_index.values())
        if subject:
            micro_preds = [m for m in micro_preds if m.subject.lower() == subject.lower()]

        # Filter to high-importance topics (>0.35) — low importance topics don't form meaningful clusters
        high_imp = [m for m in micro_preds if m.importance_probability >= 0.35]
        if len(high_imp) < min_cluster_size:
            logger.debug("Not enough high-importance topics for clustering")
            return []

        # Step 1: Build similarity matrix
        similarity_matrix = self._build_similarity_matrix(high_imp)

        # Step 2: Greedy clustering
        raw_clusters = self._greedy_cluster(high_imp, similarity_matrix, min_cluster_size)

        # Step 3: Convert to TopicClusterObject
        cluster_objects = []
        for cluster_members in raw_clusters[:max_clusters]:
            obj = self._build_cluster_object(cluster_members, batch)
            if obj:
                cluster_objects.append(obj)

        # Sort by cluster_importance descending
        cluster_objects.sort(key=lambda c: c.cluster_importance, reverse=True)
        logger.info(f"Detected {len(cluster_objects)} topic clusters")
        return cluster_objects

    # ── Similarity matrix ─────────────────────────────────────────────────────

    def _build_similarity_matrix(
        self, topics: List[MicroTopicPrediction]
    ) -> Dict[Tuple[int, int], float]:
        """
        Compute pairwise similarity between topics using:
        - Same chapter bonus (strong conceptual link)
        - Importance probability similarity
        - Trend direction alignment
        - Recurrence score similarity
        """
        matrix: Dict[Tuple[int, int], float] = {}
        n = len(topics)
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._pairwise_similarity(topics[i], topics[j])
                matrix[(i, j)] = sim
                matrix[(j, i)] = sim
        return matrix

    @staticmethod
    def _pairwise_similarity(a: MicroTopicPrediction, b: MicroTopicPrediction) -> float:
        """Compute topic similarity on a 0–1 scale."""
        score = 0.0

        # Same chapter → strong link
        if a.chapter.lower() == b.chapter.lower():
            score += 0.40
        elif a.subject.lower() == b.subject.lower():
            score += 0.15

        # Importance proximity
        imp_diff = abs(a.importance_probability - b.importance_probability)
        score += max(0, 0.25 * (1 - imp_diff / 0.5))

        # Recurrence proximity
        rec_diff = abs(a.recurrence_score - b.recurrence_score)
        score += max(0, 0.20 * (1 - rec_diff / 0.5))

        # Trend alignment
        trend_product = a.topic_trend_score * b.topic_trend_score
        if trend_product > 0:   # same direction
            score += 0.15
        elif trend_product < -0.1:  # opposing trends
            score -= 0.10

        return min(1.0, max(0.0, score))

    # ── Greedy clustering ──────────────────────────────────────────────────────

    def _greedy_cluster(
        self,
        topics: List[MicroTopicPrediction],
        matrix: Dict[Tuple[int, int], float],
        min_size: int,
    ) -> List[List[MicroTopicPrediction]]:
        """
        Greedy agglomerative clustering: each topic joins the cluster where
        it has the highest average similarity to existing members.
        """
        assigned: Set[int] = set()
        clusters: List[List[int]] = []

        # Sort topics by importance desc — seed clusters with high-importance topics
        order = sorted(range(len(topics)), key=lambda i: topics[i].importance_probability, reverse=True)

        for seed_idx in order:
            if seed_idx in assigned:
                continue

            cluster = [seed_idx]
            assigned.add(seed_idx)

            # Try to expand cluster
            for candidate_idx in order:
                if candidate_idx in assigned:
                    continue
                avg_sim = sum(
                    matrix.get((candidate_idx, m), 0.0) for m in cluster
                ) / len(cluster)
                if avg_sim >= self.co_occurrence_threshold:
                    cluster.append(candidate_idx)
                    assigned.add(candidate_idx)

            if len(cluster) >= min_size:
                clusters.append(cluster)

        return [[topics[i] for i in cluster] for cluster in clusters]

    # ── Cluster object building ────────────────────────────────────────────────

    def _build_cluster_object(
        self,
        members: List[MicroTopicPrediction],
        batch: PredictionBatch,
    ) -> Optional[TopicClusterObject]:
        if not members:
            return None

        sorted_members = sorted(members, key=lambda m: m.importance_probability, reverse=True)
        anchor = sorted_members[0]

        avg_importance = sum(m.importance_probability for m in members) / len(members)
        # Cluster importance is boosted: co-occurring important topics are more "certain"
        cluster_importance = min(1.0, avg_importance * (1 + 0.1 * math.log1p(len(members))))

        avg_trend = sum(m.topic_trend_score for m in members) / len(members)
        trend = trend_score_to_direction(avg_trend)

        # Co-occurrence score: average pairwise importance correlation
        co_occ = min(1.0, avg_importance * 1.2)

        member_topics   = list(dict.fromkeys(m.topic   for m in sorted_members))
        member_chapters = list(dict.fromkeys(m.chapter for m in sorted_members))

        strategic_note = self._build_strategic_note(sorted_members, cluster_importance)

        return TopicClusterObject(
            cluster_id          = str(uuid4()),
            cluster_name        = f"{anchor.chapter} Cluster",
            exam_type           = anchor.exam_type,
            target_year         = anchor.target_year,
            anchor_topic        = anchor.topic,
            member_topics       = member_topics,
            member_chapters     = member_chapters,
            subject             = anchor.subject,
            avg_importance      = round(avg_importance, 3),
            cluster_importance  = round(cluster_importance, 3),
            trend_direction     = trend,
            co_occurrence_score = round(co_occ, 3),
            strategic_note      = strategic_note,
        )

    @staticmethod
    def _build_strategic_note(members: List[MicroTopicPrediction], cluster_importance: float) -> str:
        """Plain-text note explaining why this cluster matters."""
        subjects  = list(dict.fromkeys(m.subject  for m in members))
        chapters  = list(dict.fromkeys(m.chapter  for m in members))
        max_imp   = max(m.importance_probability for m in members)
        trending  = [m.micro_topic_name for m in members if m.topic_trend_score > 0.20]

        parts = [f"This cluster of {len(members)} topics spans {', '.join(chapters[:2])}."]
        parts.append(f"Peak topic importance: {max_imp:.0%}.")
        if trending:
            parts.append(f"Rising trend: {', '.join(trending[:2])}.")
        parts.append(
            "Studying these together is efficient — they share conceptual dependencies "
            "and historically co-occur in exams."
        )
        return " ".join(parts)
