"""
RAG Document Indexer
=====================
Indexes curriculum, exam history, playbooks, and taxonomy docs
into the vector store for retrieval.

Chunking strategy:
- Curriculum docs: 300-token chunks with 50-token overlap
- Exam history: one chunk per (topic, year) — atomic and filterable
- Taxonomy: one chunk per chapter — filtered by subject
- Playbooks: 400-token semantic chunks
"""

from __future__ import annotations

import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

PRAJNA_ROOT = Path(__file__).parents[4]


class DocumentChunk:
    """A single indexable unit."""
    def __init__(
        self,
        chunk_id:      str,
        text:          str,
        source:        str,
        evidence_type: str,
        metadata:      Dict[str, Any],
    ):
        self.chunk_id      = chunk_id
        self.text          = text
        self.source        = source
        self.evidence_type = evidence_type
        self.metadata      = metadata


class RAGIndexer:
    """Indexes documents into ChromaDB for retrieval."""

    def __init__(
        self,
        collection_name: str = "prajna_rag",
        persist_dir:     str = "./data/rag_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        batch_size:      int = 100,
    ):
        self.collection_name = collection_name
        self.persist_dir     = persist_dir
        self.embedding_model = embedding_model
        self.batch_size      = batch_size
        self._collection     = None
        self._embedder       = None

    def _init(self):
        if self._collection is not None:
            return
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._embedder = SentenceTransformer(self.embedding_model)
            logger.info("RAG indexer initialized")
        except ImportError as e:
            logger.error(f"Missing dependency: {e}. Install: pip install chromadb sentence-transformers")
            raise

    def index_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Batch-index document chunks into the vector store."""
        self._init()
        indexed = 0
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i: i + self.batch_size]
            texts     = [c.text for c in batch]
            ids       = [c.chunk_id for c in batch]
            metadatas = [{
                "source":        c.source,
                "evidence_type": c.evidence_type,
                **{k: str(v) for k, v in c.metadata.items() if v is not None},
            } for c in batch]

            embeddings = self._embedder.encode(texts, show_progress_bar=False).tolist()
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            indexed += len(batch)
            logger.info(f"Indexed batch {i//self.batch_size + 1}: {len(batch)} chunks")
        return indexed

    # ── Source-specific indexers ───────────────────────────────────────────────

    def index_syllabus(self) -> int:
        """Index the official NEET/JEE syllabus from data/syllabus.py."""
        sys.path.insert(0, str(PRAJNA_ROOT))
        try:
            from data.syllabus import NEET_SYLLABUS, JEE_SYLLABUS
        except ImportError:
            logger.error("Could not import syllabus. Check PRAJNA_ROOT path.")
            return 0

        chunks = []
        for exam_name, syllabus in [("neet", NEET_SYLLABUS), ("jee_main", JEE_SYLLABUS)]:
            for subject, chapters in syllabus.items():
                for chapter, micro_topics in chapters.items():
                    micro_list = micro_topics if isinstance(micro_topics, list) else \
                                 [t for sublist in micro_topics.values() for t in sublist]
                    text = (
                        f"Chapter: {chapter}\n"
                        f"Subject: {subject}\n"
                        f"Exam: {exam_name.upper()}\n\n"
                        f"Key Micro-Topics:\n" +
                        "\n".join(f"- {mt}" for mt in micro_list)
                    )
                    chunks.append(DocumentChunk(
                        chunk_id      = f"syllabus-{exam_name}-{subject[:3]}-{chapter[:10]}-{uuid4().hex[:6]}",
                        text          = text,
                        source        = f"Official {exam_name.upper()} Syllabus",
                        evidence_type = "curriculum_doc",
                        metadata      = {
                            "exam_type": exam_name,
                            "subject":   subject,
                            "chapter":   chapter,
                            "doc_type":  "syllabus",
                        },
                    ))
        return self.index_chunks(chunks)

    def index_historical_exam_data(self, exam_db_path: Optional[str] = None) -> int:
        """Index historical exam question patterns from SQLite DB."""
        import sqlite3
        db_path = exam_db_path or str(PRAJNA_ROOT / "data" / "exam.db")
        if not Path(db_path).exists():
            logger.warning(f"exam.db not found at {db_path}")
            return 0

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("""
            SELECT subject, topic, micro_topic, exam, year, COUNT(*) as qs,
                   AVG(difficulty) as avg_diff
            FROM questions
            GROUP BY subject, topic, micro_topic, exam, year
            ORDER BY year DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        chunks = []
        for subject, topic, micro_topic, exam, year, qs, avg_diff in rows:
            text = (
                f"Historical Pattern: {exam.upper()} {year}\n"
                f"Subject: {subject} | Chapter/Topic: {topic}\n"
                f"Micro-Topic: {micro_topic or topic}\n"
                f"Questions asked: {qs}\n"
                f"Average difficulty: {avg_diff:.1f}/5\n"
            )
            chunks.append(DocumentChunk(
                chunk_id      = f"hist-{exam}-{year}-{subject[:3]}-{(topic or '')[:8]}-{uuid4().hex[:6]}",
                text          = text,
                source        = f"{exam.upper()} {year} Question Analysis",
                evidence_type = "historical_exam",
                metadata      = {
                    "exam_type": exam.lower().replace(" ", "_"),
                    "subject":   subject,
                    "chapter":   topic,
                    "year":      str(year),
                    "qs_count":  str(qs),
                    "doc_type":  "exam_history",
                },
            ))
        return self.index_chunks(chunks)

    def index_student_performance(self, csv_path: Optional[str] = None) -> int:
        """Index aggregated student performance data as evidence."""
        default_csv = str(PRAJNA_ROOT / "data" / "student_data" / "neet_results_v2.csv")
        path = csv_path or default_csv
        if not Path(path).exists():
            logger.warning(f"Student data CSV not found: {path}")
            return 0

        # Aggregate by subject + chapter
        from collections import defaultdict
        agg: Dict[str, Dict] = defaultdict(lambda: {"accs": [], "subject": "", "chapter": ""})

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['subject']}|{row['chapter']}"
                agg[key]["accs"].append(float(row.get("accuracy_pct", 0)))
                agg[key]["subject"] = row["subject"]
                agg[key]["chapter"] = row["chapter"]

        chunks = []
        for key, data in agg.items():
            accs = data["accs"]
            avg  = sum(accs) / len(accs) if accs else 0
            text = (
                f"Student Performance Data\n"
                f"Subject: {data['subject']} | Chapter: {data['chapter']}\n"
                f"Average accuracy across 200 students: {avg:.1f}%\n"
                f"Sample size: {len(accs)} observations\n"
                f"Performance band: {'Strong' if avg >= 65 else 'Developing' if avg >= 45 else 'Weak'}\n"
            )
            chunks.append(DocumentChunk(
                chunk_id      = f"student-{key[:20]}-{uuid4().hex[:6]}",
                text          = text,
                source        = "PRAJNA Student Mock Exam Data (200 students, 10 exams)",
                evidence_type = "student_performance",
                metadata      = {
                    "subject":   data["subject"],
                    "chapter":   data["chapter"],
                    "avg_acc":   str(round(avg, 1)),
                    "doc_type":  "student_performance",
                },
            ))
        return self.index_chunks(chunks)

    def index_playbook(self, playbook_text: str, title: str, exam_type: str) -> int:
        """Index a revision playbook document (chunked by 400 tokens)."""
        chunks_text = self._chunk_text(playbook_text, chunk_size=400, overlap=50)
        chunks = [
            DocumentChunk(
                chunk_id      = f"playbook-{title[:10]}-{i}-{uuid4().hex[:6]}",
                text          = chunk,
                source        = title,
                evidence_type = "benchmark_pattern",
                metadata      = {
                    "exam_type": exam_type,
                    "doc_type":  "playbook",
                    "chunk_idx": str(i),
                },
            )
            for i, chunk in enumerate(chunks_text)
        ]
        return self.index_chunks(chunks)

    # ── Chunking ───────────────────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
        """Split text into overlapping word-count chunks."""
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks

    def index_all(self) -> Dict[str, int]:
        """Index all available data sources."""
        results = {}
        logger.info("Starting full RAG indexing…")

        results["syllabus"]   = self.index_syllabus()
        results["exam_history"] = self.index_historical_exam_data()
        results["students"]   = self.index_student_performance()

        total = sum(results.values())
        logger.info(f"RAG indexing complete: {total} chunks indexed")
        logger.info(f"  Breakdown: {results}")
        return results
