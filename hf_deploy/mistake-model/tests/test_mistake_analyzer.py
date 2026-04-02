import pytest
import pandas as pd
from analysis.mistake_analyzer import MistakeAnalyzer

@pytest.fixture
def sample_results():
    return pd.DataFrame({
        "student_id": ["S1","S1","S1","S2","S2","S2"],
        "coaching": ["PW Kota"]*3 + ["PW Delhi"]*3,
        "subject": ["Physics","Physics","Chemistry","Physics","Physics","Chemistry"],
        "chapter": ["Kinematics","Optics","Bonding","Kinematics","Optics","Bonding"],
        "micro_topic": ["1D Motion","Refraction","Ionic","1D Motion","Refraction","Ionic"],
        "total_qs": [5,4,3,5,4,3],
        "correct": [1,3,2,2,1,1],
        "wrong": [4,1,1,3,3,2],
        "accuracy_pct": [20.0,75.0,66.7,40.0,25.0,33.3],
        "time_min": [8.0,5.0,4.0,6.0,7.0,5.0],
        "exam_no": [1]*6,
    })

@pytest.fixture
def analyzer(sample_results):
    return MistakeAnalyzer(sample_results)

def test_error_rates(analyzer):
    er = analyzer.error_rates()
    assert "micro_topic" in er.columns
    assert "error_rate" in er.columns
    row = er[er["micro_topic"] == "1D Motion"].iloc[0]
    assert abs(row["error_rate"] - 0.70) < 0.01

def test_danger_zones(analyzer):
    prajna = {"1D Motion": 0.90, "Refraction": 0.80, "Ionic": 0.50}
    dz = analyzer.danger_zones(prajna, error_threshold=0.5)
    assert len(dz) >= 1
    assert "danger_score" in dz.columns
    top = dz.iloc[0]
    assert top["micro_topic"] == "1D Motion"
    assert abs(top["danger_score"] - 0.63) < 0.01

def test_cofailure_matrix(analyzer):
    cf = analyzer.cofailure_pairs(fail_threshold=50)
    assert isinstance(cf, list)
    for pair in cf:
        assert "topic_a" in pair
        assert "topic_b" in pair
        assert "cofailure_pct" in pair

def test_time_vs_accuracy(analyzer):
    tva = analyzer.time_vs_accuracy()
    assert "micro_topic" in tva.columns
    assert "avg_time" in tva.columns
    assert "avg_accuracy" in tva.columns
    assert "subject" in tva.columns
