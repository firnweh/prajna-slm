import os
from utils.db import init_db, insert_questions
from analysis.pattern_finder import (
    topic_cooccurrence,
    subject_weightage_over_time,
    cross_exam_correlation,
)

TEST_DB = "data/test_patterns.db"


def setup_function():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)


def teardown_function():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _q(id, year, subject, topic, micro_topic, exam="JEE Advanced"):
    return {
        "id": id, "exam": exam, "year": year, "shift": "P1",
        "subject": subject, "topic": topic, "micro_topic": micro_topic,
        "question_text": "...", "question_type": "MCQ_single",
        "difficulty": 3, "concepts_tested": [], "answer": "A", "marks": 4,
    }


def test_topic_cooccurrence():
    questions = [
        _q("Q1", 2020, "Physics", "Mechanics", "Kinematics"),
        _q("Q2", 2020, "Physics", "Mechanics", "Projectile Motion"),
        _q("Q3", 2020, "Physics", "Optics", "Refraction"),
    ]
    insert_questions(TEST_DB, questions)
    matrix = topic_cooccurrence(TEST_DB)
    assert matrix.loc["Kinematics", "Projectile Motion"] > 0
    assert matrix.loc["Kinematics", "Refraction"] > 0


def test_subject_weightage():
    questions = [
        _q(f"P{i}", 2020, "Physics", "M", "K") for i in range(3)
    ] + [
        _q(f"C{i}", 2020, "Chemistry", "O", "R") for i in range(7)
    ]
    insert_questions(TEST_DB, questions)
    weights = subject_weightage_over_time(TEST_DB)
    assert weights.loc[2020, "Physics"] < weights.loc[2020, "Chemistry"]


def test_cross_exam_correlation():
    questions = [
        _q("J1", 2020, "Physics", "Waves", "Doppler", exam="JEE Advanced"),
        _q("N1", 2021, "Physics", "Waves", "Doppler", exam="NEET"),
    ]
    insert_questions(TEST_DB, questions)
    corr = cross_exam_correlation(TEST_DB)
    doppler = [c for c in corr if c["micro_topic"] == "Doppler"]
    assert len(doppler) == 1
    assert doppler[0]["lag_years"] == 1
