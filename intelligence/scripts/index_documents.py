"""
RAG Document Indexing Script
==============================
Indexes all knowledge sources into ChromaDB for the intelligence layer's RAG system.

Sources indexed:
  1. Official syllabi (NEET + JEE)
  2. Historical exam question data (from exam.db)
  3. Student performance summaries
  4. Strategy playbooks (if available)

Usage:
    python -m scripts.index_documents
    python -m scripts.index_documents --source syllabus --exam neet
    python -m scripts.index_documents --source all --reset
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure intelligence package is on path
_INTEL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_INTEL_ROOT))

from config.settings import get_settings
from services.rag.indexer import RAGIndexer
from packages.schemas.prediction import ExamType


async def run_indexing(
    source: str,
    exam_type: str,
    reset: bool,
) -> None:
    settings = get_settings()

    print(f"\n{'='*60}")
    print(f"  PRAJNA Intelligence — RAG Indexer")
    print(f"  Collection : {settings.chroma_collection}")
    print(f"  ChromaDB   : {settings.chroma_host}:{settings.chroma_port}")
    print(f"  Source     : {source}")
    print(f"  Exam       : {exam_type}")
    print(f"  Reset      : {reset}")
    print(f"{'='*60}\n")

    indexer = RAGIndexer(
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port,
        collection_name=settings.chroma_collection,
        embedding_model=settings.embedding_model,
        embedding_device=settings.embedding_device,
    )

    await indexer.connect()

    if reset:
        print("  ⚠  Resetting collection (deleting all existing documents)...")
        await indexer.reset_collection()
        print("  ✓  Collection reset.\n")

    exam_enum = None
    if exam_type != "all":
        exam_enum = ExamType(exam_type)

    if source in ("syllabus", "all"):
        print("  → Indexing syllabi...")
        count = await indexer.index_syllabus(exam_type=exam_enum)
        print(f"     Indexed {count} syllabus chunks.\n")

    if source in ("historical", "all"):
        print("  → Indexing historical exam data...")
        count = await indexer.index_historical_exam_data(exam_type=exam_enum)
        print(f"     Indexed {count} historical exam records.\n")

    if source in ("student", "all"):
        print("  → Indexing student performance data...")
        count = await indexer.index_student_performance(
            data_dir=settings.student_data_dir,
        )
        print(f"     Indexed {count} student performance summaries.\n")

    if source in ("playbook", "all"):
        playbook_dir = _INTEL_ROOT / "docs" / "playbooks"
        if playbook_dir.exists():
            print("  → Indexing strategy playbooks...")
            count = await indexer.index_playbook(playbook_dir)
            print(f"     Indexed {count} playbook chunks.\n")
        else:
            print("  ℹ  No playbooks directory found — skipping.\n")

    stats = await indexer.collection_stats()
    print(f"{'='*60}")
    print(f"  Indexing complete!")
    print(f"  Total documents in collection: {stats.get('total_documents', '?')}")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index documents into ChromaDB for PRAJNA RAG"
    )
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "syllabus", "historical", "student", "playbook"],
        help="Which document source to index (default: all)",
    )
    parser.add_argument(
        "--exam",
        default="all",
        choices=["all", "neet", "jee_main", "jee_advanced"],
        help="Filter by exam type (default: all)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing documents before indexing",
    )
    args = parser.parse_args()

    asyncio.run(run_indexing(
        source=args.source,
        exam_type=args.exam,
        reset=args.reset,
    ))


if __name__ == "__main__":
    main()
