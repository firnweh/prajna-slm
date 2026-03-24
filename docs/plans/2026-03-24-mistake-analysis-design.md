# Design: Student Mistake Analysis — Model + Streamlit Tab

## Context
Build a new Streamlit tab ("Mistake Analysis") that learns from student mistakes across all test data. Two views: Center View (aggregate patterns for org managers) and Student View (per-student predictions using logistic regression). Cross-references PRAJNA exam predictions to surface "danger zones" — topics students consistently get wrong that are also likely to appear.

## Architecture: Statistical Aggregation (A) + Logistic Regression (B)

### Data Sources
- `data/student_data/neet_results_v2.csv` (118K rows) — per-student per-micro-topic per-exam results
- `data/student_data/jee_results_v2.csv` (162K rows) — same for JEE
- `data/student_data/students_v2.csv` — student profiles with ability scores
- `data/exam.db` — question bank with difficulty, concepts, micro_topic
- PRAJNA predictions — appearance_probability per topic (from predictor_v3/v4)

### Tab Layout
```
Toggle: [Center View] [Student View]
Filters: [Exam: NEET/JEE] [Subject: All/Phy/Chem/Bio] [Branch: All/PW Kota/...]
```

## Center View (Approach A — Pure Pandas)

### Panel 1: Danger Zones
Cross-reference: topics where error_rate > 50% AND PRAJNA appearance_probability > 70%.
Ranked table: Topic | Subject | Student Error% | PRAJNA Prob | Danger Score.
`danger_score = error_rate * appearance_probability`
Top 15 with red/amber badges. "Teach these NOW" list.

### Panel 2: Co-failure Patterns
Per-student binary pass/fail per topic → pairwise conditional probability.
Top 15 correlated pairs: "Students who fail X also fail Y (82% co-failure)".
Actionable: "If weak in X, proactively intervene on Y."

### Panel 3: Time vs Accuracy
Scatter plot: X = avg time_min, Y = avg accuracy_pct, color = subject.
"High time + low accuracy" quadrant = conceptual gaps needing teaching method change.

## Student View (Approach B — Logistic Regression)

### Panel 1: Predicted Miss Probability
Table sorted by P(miss) desc: Topic | Subject | Past Accuracy | P(Miss) | Risk Badge.
Logistic regression output per topic.

### Panel 2: Personal Danger Zones
Student's weak topics filtered by PRAJNA appearance_probability > 70%.
"You're weak here AND PRAJNA says it's coming." Top 8 items.

### Panel 3: Improvement Trajectory
Line chart: X = exam number (1-10), Y = accuracy per topic.
5 most-improved and 5 most-declining topics.

### Panel 4: Model Explanation
Bar chart of logistic regression feature importances.
"Past accuracy explains 45%, topic difficulty 22%, time pressure 18%..."

## Logistic Regression Model

### Features (7)
1. `rolling_accuracy` — avg accuracy on this topic across prior exams
2. `ability_score` — from students_v2.csv (subject-level baseline 0-1)
3. `topic_difficulty` — avg difficulty from exam.db (1-5 normalized)
4. `exam_importance` — PRAJNA appearance_probability (0-1)
5. `avg_time_spent` — normalized time_min on this topic
6. `streak` — consecutive correct/wrong streak on this topic
7. `exam_number` — temporal position (1-10)

### Label
`1 = mistake (accuracy < 50% on that topic in that exam), 0 = OK`

### Training
- Per exam type (NEET / JEE separately)
- Train on exams 1-8, validate on 9, test on 10
- Cache as `analysis/mistake_model_neet.pkl` / `_jee.pkl`
- Retrain button in Streamlit sidebar

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `analysis/mistake_analyzer.py` | Center-view: danger zones, co-failure matrix, time-vs-accuracy |
| `analysis/mistake_predictor.py` | Logistic regression: feature engineering, training, prediction |
| `dashboard/app.py` | New "Mistake Analysis" nav tab with toggle between center/student view |

## Success Criteria
- Center view loads in < 3s for all 280K rows
- Logistic regression achieves > 65% AUC on held-out exam 10
- Danger zones correctly identify topics with both high error rate and high PRAJNA probability
- Co-failure matrix surfaces non-obvious topic correlations
- Student view shows personalized predicted miss probabilities
