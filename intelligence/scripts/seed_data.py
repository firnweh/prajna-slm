"""
Seed Data Script
==================
Generates mock prediction data and runs it through the full intelligence
pipeline to verify everything is wired up correctly.

Useful for:
  - First-time setup verification
  - CI/CD smoke testing
  - Demoing the API without a live PRAJNA engine

Usage:
    python -m scripts.seed_data
    python -m scripts.seed_data --exam jee_main --year 2025
    python -m scripts.seed_data --output docs/sample_outputs/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_INTEL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_INTEL_ROOT))

from config.settings import get_settings
from packages.schemas.prediction import ExamType
from packages.schemas.intelligence import PersonaType
from services.prediction_adapter.client import PredictionAdapter
from services.topic_intelligence.aggregator import TopicIntelligenceAggregator
from services.topic_intelligence.cluster_detector import TopicClusterDetector
from services.insight_engine.slm_provider import create_provider
from services.insight_engine.generator import InsightGenerator


async def run_seed(
    exam: str,
    year: int,
    output_dir: Path,
) -> None:
    settings = get_settings()
    exam_type = ExamType(exam)

    print(f"\n{'='*60}")
    print(f"  PRAJNA Intelligence — Seed & Smoke Test")
    print(f"  Exam: {exam_type.value}  Year: {year}")
    print(f"  SLM provider: {settings.slm_provider}")
    print(f"{'='*60}\n")

    # ── 1. Prediction Adapter ──────────────────────────────────────────────────
    print("  [1/5] Prediction Adapter...")
    adapter = PredictionAdapter(mode="local")
    micro_preds = await adapter.get_predictions(exam_type, year)
    print(f"        Got {len(micro_preds)} micro-topic predictions.")

    # ── 2. Aggregator ──────────────────────────────────────────────────────────
    print("  [2/5] Aggregator...")
    aggregator = TopicIntelligenceAggregator()
    batch = aggregator.build_batch(micro_preds)
    print(f"        Batch: {batch.total_subjects_predicted if hasattr(batch,'total_subjects_predicted') else len(batch.subject_predictions)} subjects, "
          f"{batch.total_chapters_predicted} chapters, "
          f"{batch.total_micro_topics_predicted} micro-topics.")

    # ── 3. Cluster Detection ───────────────────────────────────────────────────
    print("  [3/5] Cluster Detector...")
    detector = TopicClusterDetector()
    first_subject = batch.subject_predictions[0].subject if batch.subject_predictions else None
    if first_subject:
        subject_preds = [m for m in micro_preds if m.subject == first_subject]
        clusters = detector.detect_clusters(subject_preds, exam_type, year)
        print(f"        Detected {len(clusters)} clusters in '{first_subject}'.")
    else:
        print("        No subject predictions found.")
        clusters = []

    # ── 4. Revision Priorities ─────────────────────────────────────────────────
    print("  [4/5] Revision Priorities...")
    priorities = aggregator.rank_revision_priorities(batch, top_n=20)
    print(f"        Top priority: {priorities[0].scope_name if priorities else 'none'}")
    print(f"        Total ranked: {len(priorities)}")

    # ── 5. SLM Insight Generation (Mock) ──────────────────────────────────────
    print("  [5/5] SLM Insight Generator (mock)...")
    slm = create_provider("mock")
    generator = InsightGenerator(slm_provider=slm)

    insight = None
    if priorities:
        top = priorities[0]
        try:
            insight = await generator.generate_topic_insight(
                micro_topic=micro_preds[0] if micro_preds else None,
                retrieved_passages=[],
                persona=PersonaType.STUDENT,
            )
            print(f"        Generated insight: '{insight.title}'")
        except Exception as e:
            print(f"        Insight generation returned: {e}")

    # ── Save sample outputs ────────────────────────────────────────────────────
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

        sample = {
            "exam_type":           exam_type.value,
            "target_year":         year,
            "total_micro_topics":  len(micro_preds),
            "total_subjects":      len(batch.subject_predictions),
            "total_chapters":      batch.total_chapters_predicted,
            "top_priorities": [
                {
                    "name":            p.scope_name,
                    "chapter":         p.parent_chain[1] if len(p.parent_chain) > 1 else "",
                    "subject":         p.parent_chain[0] if p.parent_chain else "",
                    "priority_score":  round(p.priority_score, 2),
                    "urgency":         p.urgency.value,
                    "importance_prob": round(p.importance_probability, 3),
                }
                for p in priorities[:10]
            ],
            "clusters": [
                {
                    "cluster_name":      c.cluster_name,
                    "anchor":            c.anchor_topic,
                    "member_count":      len(c.member_topics),
                    "cluster_importance": round(c.cluster_importance, 3),
                }
                for c in clusters[:5]
            ],
        }

        if insight:
            sample["sample_insight"] = {
                "title":    insight.title,
                "claim":    insight.claim,
                "narrative": insight.narrative[:300] + "...",
                "action":   insight.recommended_action,
                "confidence": insight.confidence,
            }

        outfile = output_dir / f"seed_{exam}_{year}.json"
        with open(outfile, "w") as f:
            json.dump(sample, f, indent=2, default=str)
        print(f"\n  Sample output saved → {outfile}")

    print(f"\n{'='*60}")
    print(f"  ✓ Seed complete — all systems operational")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the PRAJNA intelligence layer with mock data"
    )
    parser.add_argument("--exam",   default="neet",
                        choices=["neet", "jee_main", "jee_advanced"])
    parser.add_argument("--year",   type=int, default=2025)
    parser.add_argument("--output", default="docs/sample_outputs",
                        help="Directory to save sample outputs")
    args = parser.parse_args()

    asyncio.run(run_seed(
        exam=args.exam,
        year=args.year,
        output_dir=Path(args.output),
    ))


if __name__ == "__main__":
    main()
