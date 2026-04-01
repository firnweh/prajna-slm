#!/usr/bin/env python3
"""
build_qbg_db.py — Build qbg.db from 3 HuggingFace datasets.

Datasets:
  1. PhysicsWallahAI/qbg-pcmr     (CSV)  — primary source with all fields
  2. PhysicsWallahAI/qbg-pcmr-1   (JSONL) — cleaned version (used for cross-ref)
  3. PhysicsWallahAI/gpt-oss      (JSONL) — GPT step-by-step analysis

Output: data/qbg.db (~2-3 GB SQLite)
"""

import ast
import json
import os
import sqlite3
import sys
import time

import pandas as pd
from huggingface_hub import hf_hub_download

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_DIR, "data", "qbg.db")
DATA_DIR = os.path.join(PROJECT_DIR, "data")

EXCLUDED_CATEGORIES = {
    "Banking", "MBA", "UPSC", "CLAT", "UGC NET", "SSC", "Railways",
}

BATCH_SIZE = 10_000

# Files to download per dataset
PCMR_FILES = {
    "Physics": "physics_clean.csv",
    "Chemistry": "chemistry_clean.csv",
    "Maths": "maths_clean.csv",
}

PCMR1_FILES = {
    "Physics": "qbg_phys_1.jsonl",
    "Chemistry": "qbg_chem_1.jsonl",
    "Maths": "qbg_math_1.jsonl",
}

GPTOSS_FILES = {
    "Physics": "qbg_phys_1_gptoss_low_0.6_eval.jsonl",
    "Chemistry": "qbg_chem_1_gptoss_low_0.6_eval.jsonl",
    "Maths": "qbg_math_1_gptoss_low_0.6_eval.jsonl",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_metadata(raw: str) -> dict:
    """Parse metadata string that looks like a Python dict.

    Try json.loads first, then with quote replacement, then ast.literal_eval.
    Does NOT use the built-in eval() — only safe alternatives.
    """
    if not raw or not isinstance(raw, str):
        return {}
    raw = raw.strip()
    if not raw:
        return {}

    # Attempt 1: direct json.loads
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 2: replace single quotes with double quotes
    try:
        fixed = raw.replace("'", '"')
        return json.loads(fixed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 3: ast.literal_eval (safe parser, no arbitrary code execution)
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    return {}


def download_file(repo_id: str, filename: str, repo_type: str = "dataset") -> str:
    """Download a single file from HF and return its local path."""
    print(f"  Downloading {repo_id}/{filename} ...")
    path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type=repo_type)
    print(f"    -> {path}")
    return path


def download_all():
    """Download all 9 files from the 3 datasets. Returns dict of local paths."""
    paths = {"pcmr": {}, "pcmr1": {}, "gptoss": {}}

    print("\n=== Downloading qbg-pcmr (CSV) ===")
    for subject, fname in PCMR_FILES.items():
        paths["pcmr"][subject] = download_file("PhysicsWallahAI/qbg-pcmr", fname)

    print("\n=== Downloading qbg-pcmr-1 (JSONL) ===")
    for subject, fname in PCMR1_FILES.items():
        paths["pcmr1"][subject] = download_file("PhysicsWallahAI/qbg-pcmr-1", fname)

    print("\n=== Downloading gpt-oss (JSONL) ===")
    for subject, fname in GPTOSS_FILES.items():
        paths["gptoss"][subject] = download_file("PhysicsWallahAI/gpt-oss", fname)

    return paths


# ---------------------------------------------------------------------------
# GPT-OSS lookup builder
# ---------------------------------------------------------------------------

def build_gpt_lookup(gptoss_paths: dict) -> dict:
    """Build qbgid -> gpt_analysis lookup from gpt-oss JSONL files."""
    print("\n=== Building GPT analysis lookup ===")
    lookup = {}
    total = 0
    for subject, path in gptoss_paths.items():
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract qbgid from metadata
                meta_raw = record.get("metadata", "")
                if isinstance(meta_raw, dict):
                    meta = meta_raw
                else:
                    meta = parse_metadata(str(meta_raw))
                qbgid = meta.get("qbgid", "")
                if not qbgid:
                    continue

                # Extract GPT analysis from completions.correct[0]
                completions = record.get("completions", {})
                if isinstance(completions, str):
                    try:
                        completions = json.loads(completions)
                    except (json.JSONDecodeError, ValueError):
                        completions = {}
                correct_list = completions.get("correct", [])
                if correct_list and isinstance(correct_list, list):
                    gpt_text = correct_list[0]
                    lookup[str(qbgid)] = gpt_text
                    count += 1

        print(f"  {subject}: {count} GPT analyses loaded")
        total += count

    print(f"  Total GPT analyses: {total}")
    return lookup


# ---------------------------------------------------------------------------
# DB creation
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qbgid TEXT,
    subject TEXT,
    difficulty TEXT,
    type TEXT,
    category TEXT,
    question TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    option4 TEXT,
    option5 TEXT,
    correct_answer TEXT,
    text_solution TEXT,
    exam TEXT,
    question_clean TEXT,
    answer_clean TEXT,
    option_dependent TEXT,
    diagram_dependent TEXT,
    language TEXT,
    reason TEXT,
    response TEXT,
    gpt_analysis TEXT
);
"""

INSERT_SQL = """
INSERT INTO questions (
    qbgid, subject, difficulty, type, category,
    question, option1, option2, option3, option4, option5,
    correct_answer, text_solution, exam,
    question_clean, answer_clean, option_dependent, diagram_dependent,
    language, reason, response, gpt_analysis
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

FTS_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(
    qbgid,
    subject,
    question,
    text_solution,
    gpt_analysis,
    content='questions',
    content_rowid='id'
);
"""

FTS_POPULATE_SQL = """
INSERT INTO questions_fts (rowid, qbgid, subject, question, text_solution, gpt_analysis)
SELECT id, qbgid, subject, question, text_solution, gpt_analysis FROM questions;
"""


def safe_str(val):
    """Convert to string, return None for NaN/None."""
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    return str(val)


def process_and_insert(conn, pcmr_paths: dict, gpt_lookup: dict):
    """Load CSVs, filter, enrich with GPT analysis, insert into DB."""
    print("\n=== Processing and inserting into DB ===")
    cursor = conn.cursor()

    total_inserted = 0
    total_skipped = 0
    total_gpt_matched = 0

    for subject, csv_path in pcmr_paths.items():
        print(f"\n  Loading {subject} CSV...")
        df = pd.read_csv(csv_path, low_memory=False)
        print(f"    Raw rows: {len(df)}")

        # Filter out excluded categories
        if "category" in df.columns:
            mask = df["category"].isin(EXCLUDED_CATEGORIES)
            skipped = mask.sum()
            df = df[~mask]
            total_skipped += skipped
            print(f"    After filtering excluded categories: {len(df)} (skipped {skipped})")

        batch = []
        gpt_matched = 0

        for _, row in df.iterrows():
            qbgid = safe_str(row.get("qbgid", ""))

            # Look up GPT analysis
            gpt_analysis = gpt_lookup.get(qbgid) if qbgid else None
            if gpt_analysis:
                gpt_matched += 1

            record = (
                qbgid,
                subject,
                safe_str(row.get("difficulty")),
                safe_str(row.get("type")),
                safe_str(row.get("category")),
                safe_str(row.get("question")),
                safe_str(row.get("option1")),
                safe_str(row.get("option2")),
                safe_str(row.get("option3")),
                safe_str(row.get("option4")),
                safe_str(row.get("option5")),
                safe_str(row.get("correct_answer")),
                safe_str(row.get("text_solution")),
                safe_str(row.get("exam")),
                safe_str(row.get("question_clean")),
                safe_str(row.get("answer_clean")),
                safe_str(row.get("option_dependent")),
                safe_str(row.get("diagram_dependent")),
                safe_str(row.get("language")),
                safe_str(row.get("reason")),
                safe_str(row.get("response")),
                gpt_analysis,
            )
            batch.append(record)

            if len(batch) >= BATCH_SIZE:
                cursor.executemany(INSERT_SQL, batch)
                conn.commit()
                total_inserted += len(batch)
                batch = []

        # Flush remaining
        if batch:
            cursor.executemany(INSERT_SQL, batch)
            conn.commit()
            total_inserted += len(batch)

        total_gpt_matched += gpt_matched
        print(f"    Inserted: {len(df)}, GPT matches: {gpt_matched}")

    print(f"\n  TOTAL inserted: {total_inserted}")
    print(f"  TOTAL skipped (excluded categories): {total_skipped}")
    print(f"  TOTAL with GPT analysis: {total_gpt_matched}")
    return total_inserted


def build_fts(conn):
    """Create and populate the FTS5 virtual table."""
    print("\n=== Building FTS5 index ===")
    cursor = conn.cursor()
    cursor.execute(FTS_TABLE_SQL)
    cursor.execute(FTS_POPULATE_SQL)
    conn.commit()
    print("  FTS5 index built.")


def create_indexes(conn):
    """Create useful indexes."""
    print("\n=== Creating indexes ===")
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_qbgid ON questions(qbgid);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subject ON questions(subject);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON questions(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty);")
    conn.commit()
    print("  Indexes created.")


def print_stats(conn):
    """Print final statistics."""
    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)

    (total,) = conn.execute("SELECT COUNT(*) FROM questions").fetchone()
    print(f"  Total questions: {total:,}")

    print("\n  By subject:")
    for row in conn.execute(
        "SELECT subject, COUNT(*) as cnt FROM questions GROUP BY subject ORDER BY cnt DESC"
    ):
        print(f"    {row[0]}: {row[1]:,}")

    print("\n  By category (top 10):")
    for row in conn.execute(
        "SELECT category, COUNT(*) as cnt FROM questions GROUP BY category ORDER BY cnt DESC LIMIT 10"
    ):
        print(f"    {row[0]}: {row[1]:,}")

    (gpt_count,) = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE gpt_analysis IS NOT NULL AND gpt_analysis != ''"
    ).fetchone()
    print(f"\n  Rows with GPT analysis: {gpt_count:,}")

    # Check for excluded categories (should be 0)
    excluded_list = list(EXCLUDED_CATEGORIES)
    placeholders = ",".join("?" for _ in excluded_list)
    (exc_count,) = conn.execute(
        f"SELECT COUNT(*) FROM questions WHERE category IN ({placeholders})",
        excluded_list,
    ).fetchone()
    print(f"  Rows with excluded categories: {exc_count}")

    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n  DB size: {db_size:.1f} MB")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start = time.time()

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Remove existing DB
    if os.path.exists(DB_PATH):
        print(f"Removing existing {DB_PATH}")
        os.remove(DB_PATH)

    # Step 1: Download all datasets
    print("STEP 1: Download datasets")
    paths = download_all()

    # Step 2: Build GPT lookup
    print("\nSTEP 2: Build GPT analysis lookup")
    gpt_lookup = build_gpt_lookup(paths["gptoss"])

    # Step 3: Create DB and insert
    print("\nSTEP 3: Create DB and insert questions")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-2000000;")  # ~2GB cache
    conn.execute(CREATE_TABLE_SQL)

    total = process_and_insert(conn, paths["pcmr"], gpt_lookup)

    # Step 4: Build FTS index
    print("\nSTEP 4: Build FTS5 index")
    build_fts(conn)

    # Step 5: Create indexes
    print("\nSTEP 5: Create indexes")
    create_indexes(conn)

    # Step 6: Stats
    print_stats(conn)

    conn.close()

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
