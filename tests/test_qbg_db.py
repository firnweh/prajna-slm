"""Tests for qbg.db — merged question bank from 3 HuggingFace datasets."""

import os
import sqlite3
import pytest

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "qbg.db")


@pytest.fixture(scope="module")
def conn():
    assert os.path.exists(DB_PATH), f"qbg.db not found at {DB_PATH}"
    connection = sqlite3.connect(DB_PATH)
    yield connection
    connection.close()


def test_table_exists(conn):
    """The 'questions' table must exist."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
    )
    assert cur.fetchone() is not None, "Table 'questions' does not exist"


def test_row_count(conn):
    """DB should contain more than 500K questions."""
    (count,) = conn.execute("SELECT COUNT(*) FROM questions").fetchone()
    assert count > 500_000, f"Expected >500K rows, got {count}"


def test_schema(conn):
    """Required columns must be present."""
    cur = conn.execute("PRAGMA table_info(questions)")
    columns = {row[1] for row in cur.fetchall()}
    required = {
        "qbgid",
        "subject",
        "difficulty",
        "type",
        "category",
        "question",
        "option1",
        "option2",
        "option3",
        "option4",
        "correct_answer",
        "text_solution",
        "exam",
        "gpt_analysis",
    }
    missing = required - columns
    assert not missing, f"Missing columns: {missing}"


def test_subjects(conn):
    """Physics and Chemistry must both be present."""
    cur = conn.execute("SELECT DISTINCT subject FROM questions")
    subjects = {row[0] for row in cur.fetchall()}
    assert "Physics" in subjects, f"Physics not in subjects: {subjects}"
    assert "Chemistry" in subjects, f"Chemistry not in subjects: {subjects}"


def test_fts_search(conn):
    """FTS5 search for 'newton' should return results."""
    cur = conn.execute(
        "SELECT COUNT(*) FROM questions_fts WHERE questions_fts MATCH 'newton'"
    )
    (count,) = cur.fetchone()
    assert count > 0, "FTS search for 'newton' returned 0 results"


def test_gpt_analysis_present(conn):
    """More than 100K rows should have non-null gpt_analysis."""
    cur = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE gpt_analysis IS NOT NULL AND gpt_analysis != ''"
    )
    (count,) = cur.fetchone()
    assert count > 100_000, f"Expected >100K rows with gpt_analysis, got {count}"


def test_no_excluded_categories(conn):
    """Banking, MBA, UPSC etc. must not appear in the DB."""
    excluded = ["Banking", "MBA", "UPSC", "CLAT", "UGC NET", "SSC", "Railways"]
    placeholders = ",".join("?" for _ in excluded)
    cur = conn.execute(
        f"SELECT COUNT(*) FROM questions WHERE category IN ({placeholders})",
        excluded,
    )
    (count,) = cur.fetchone()
    assert count == 0, f"Found {count} rows with excluded categories"
