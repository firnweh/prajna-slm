# Exam Predictor v2: Model & Dashboard Upgrade Framework

---

## 1. Executive Summary

**Current state:** A 5-signal weighted scorer (frequency 30%, cycle 25%, gap 20%, cross-exam 15%, recency 10%) that produces a single `score` per micro-topic. No confidence intervals, no marks estimation, no question-type prediction, no syllabus-aware adjustments, no explainability breakdown.

**Target state:** A 14-signal multi-output model that predicts per micro-topic: probability of appearance, expected marks range, likely question types, likely difficulty, confidence level, and syllabus status. Dashboard redesigned around decision-making with explainability, confidence tiers, and a paper blueprint simulator.

**Key upgrades:**
- Recency-weighted frequency replaces naive frequency
- Trend slope detection (rising/stable/declining)
- Marks weightage prediction (not just topic appearance)
- Syllabus status tagging with trust decay for modified topics
- Confidence scoring separate from prediction score
- Question type and difficulty prediction per topic
- Backtesting framework with precision@k, hit rate, marks coverage
- Dashboard restructured around decisions, not just data display

---

## 2. Part A: Upgraded Model Framework

### 2.1 Prediction Objective

The model should predict, for each topic/micro-topic:

| Output | Type | Description |
|--------|------|-------------|
| `appearance_probability` | float 0-1 | Likelihood this topic appears in the target exam |
| `expected_marks` | (min, max) | Estimated marks range (e.g., 4-12) |
| `likely_question_types` | list | Ranked list of probable question formats |
| `likely_difficulty` | float 1-5 | Expected difficulty level |
| `confidence` | str | HIGH / MEDIUM / LOW / SPECULATIVE |
| `trend_direction` | str | RISING / STABLE / DECLINING / NEW |
| `syllabus_status` | str | RETAINED / MODIFIED / NEW / REMOVED |
| `reasons` | list | Human-readable explanation of each signal |

**What NOT to predict:** Exact questions. That's not reliably predictable and overpromises. Predict topic probability, marks band, and question format.

### 2.2 Metric Framework

#### Tier 1: Must-Have Metrics (strong predictive signal)

| # | Metric | Signal | Formula | Reliability |
|---|--------|--------|---------|-------------|
| 1 | `recency_weighted_freq` | Topics asked recently matter more than 20yr-old data | `sum(1/((target_year - y)^decay)) for y in years_appeared` | HIGH |
| 2 | `marks_weightage_avg` | Avg marks this topic gets per paper | `total_marks / papers_appeared_in` | HIGH |
| 3 | `marks_stability` | Is marks allocation stable or volatile? | `1 - (std_dev(marks_per_year) / mean(marks_per_year))` | HIGH |
| 4 | `recurrence_gap` | Years since last appearance | `target_year - last_appeared` | HIGH |
| 5 | `trend_slope` | Is frequency rising, stable, or declining? | Linear regression slope on last 10 years | HIGH |
| 6 | `question_type_distribution` | What format this topic is usually asked in | `Counter(question_types) per topic` | HIGH |
| 7 | `difficulty_trend` | Is this topic getting harder/easier? | `mean(difficulty in recent 5yr) - mean(difficulty in prior 5yr)` | MEDIUM |
| 8 | `syllabus_status` | retained/modified/new/removed | From syllabus change data | VERY HIGH (binary gate) |

#### Tier 2: Good-to-Have Metrics (moderate signal)

| # | Metric | Signal | Formula | Reliability |
|---|--------|--------|---------|-------------|
| 9 | `cycle_match` | Cyclical topics due to reappear | Existing cycle detection, refined | MEDIUM |
| 10 | `cross_exam_signal` | Topic asked in related exam recently | `appears_in_other_exam AND lag <= 2yr` | MEDIUM |
| 11 | `chapter_spread_need` | Paper needs coverage of this chapter's unit | `unit_representation_gap` | MEDIUM |
| 12 | `format_predictability` | Always MCQ? Always numerical? | `max(type_distribution) / total` | MEDIUM |

#### Tier 3: Advanced Metrics (weak/supplementary signal)

| # | Metric | Signal | Formula | Reliability |
|---|--------|--------|---------|-------------|
| 13 | `concept_density` | How many sub-concepts does this topic touch? | `unique_questions / years_appeared` | LOW |
| 14 | `inter_topic_linkage` | Foundational topic that enables others | `co-occurrence count with other topics` | LOW |

### 2.3 Scoring Framework

#### Composite Score Formula

```
appearance_score = (
    W1 * recency_weighted_freq_norm    +  # 0.25
    W2 * trend_slope_norm              +  # 0.15
    W3 * gap_return_probability        +  # 0.15
    W4 * cycle_match_score             +  # 0.10
    W5 * marks_stability_norm          +  # 0.10
    W6 * cross_exam_signal             +  # 0.08
    W7 * chapter_spread_need           +  # 0.07
    W8 * syllabus_modifier             +  # (multiplier, not additive)
) * syllabus_gate
```

**Syllabus gate:** `0.0` if topic is REMOVED, `1.0` if RETAINED, `0.7` if MODIFIED (partial trust), `0.5` if NEW (proxy scoring).

**Syllabus modifier:** For MODIFIED topics, decay historical trust by `0.7`. For NEW topics, use proxy score (see 2.4).

#### Marks Prediction

```
expected_marks_min = percentile_25(marks_per_appearance)
expected_marks_max = percentile_75(marks_per_appearance)
expected_marks_mid = median(marks_per_appearance)
```

#### Difficulty Prediction

```
likely_difficulty = weighted_mean(difficulty, weights=recency_weights)
```
Recent years get higher weight in difficulty estimation.

#### Confidence Scoring (separate from prediction score)

```
data_richness = min(total_appearances / 10, 1.0)
recency_confidence = 1.0 if appeared_in_last_5yr else 0.5
stability = marks_stability
syllabus_certainty = 1.0 if RETAINED, 0.7 if MODIFIED, 0.3 if NEW

confidence_raw = 0.35*data_richness + 0.25*recency_confidence + 0.20*stability + 0.20*syllabus_certainty
```

| Range | Label |
|-------|-------|
| > 0.75 | HIGH |
| 0.50 - 0.75 | MEDIUM |
| 0.25 - 0.50 | LOW |
| < 0.25 | SPECULATIVE |

### 2.4 Syllabus Change Logic

**Problem:** When syllabus changes (like 2024), historical data becomes partially unreliable.

**Solution: Three-tier trust decay**

| Syllabus Status | Historical Trust | Scoring Approach |
|----------------|-----------------|------------------|
| RETAINED | 1.0 | Full historical scoring |
| MODIFIED | 0.7 | Reduce historical weight by 30%, flag changed scope |
| NEW (added) | 0.0 history | Proxy score only (see below) |
| REMOVED | 0.0 | Zero score, explicitly flagged |

**Proxy scoring for NEW topics:**

Since new topics have no exam history, score them using:
```
proxy_score = (
    0.40 * textbook_emphasis      +  # How many pages/weight in NCERT
    0.30 * conceptual_centrality  +  # Is this a foundational concept?
    0.20 * examinability          +  # Can multiple question types be made?
    0.10 * sample_paper_signal       # Appeared in any official sample paper?
)
```

For our implementation, we assign manual proxy scores to newly added topics since we have the syllabus data.

### 2.5 Output Schema

```python
{
    "topic": "Thermodynamics",
    "micro_topic": "Carnot Engine",
    "subject": "Physics",

    # Prediction outputs
    "appearance_probability": 0.82,
    "expected_marks": {"min": 4, "mid": 8, "max": 12},
    "likely_question_types": ["MCQ_single", "numerical"],
    "likely_difficulty": 3.4,
    "trend_direction": "STABLE",       # RISING / STABLE / DECLINING / NEW
    "syllabus_status": "RETAINED",     # RETAINED / MODIFIED / NEW / REMOVED
    "confidence": "HIGH",              # HIGH / MEDIUM / LOW / SPECULATIVE
    "confidence_score": 0.81,

    # Explainability
    "signal_breakdown": {
        "recency_weighted_freq": {"value": 0.72, "weight": 0.25, "contribution": 0.180},
        "trend_slope":           {"value": 0.60, "weight": 0.15, "contribution": 0.090},
        "gap_return":            {"value": 0.30, "weight": 0.15, "contribution": 0.045},
        "cycle_match":           {"value": 0.00, "weight": 0.10, "contribution": 0.000},
        "marks_stability":       {"value": 0.85, "weight": 0.10, "contribution": 0.085},
        "cross_exam":            {"value": 0.50, "weight": 0.08, "contribution": 0.040},
        "chapter_spread":        {"value": 0.40, "weight": 0.07, "contribution": 0.028},
    },
    "syllabus_modifier": 1.0,
    "reasons": [
        "High recency-weighted frequency (appeared 18 times, strong in recent years)",
        "Stable trend — consistent presence over last decade",
        "Marks allocation stable at 4-8 marks per paper",
        "Retained in current syllabus with no modifications",
    ],

    # Historical context
    "total_appearances": 18,
    "last_appeared": 2023,
    "training_years": "2000–2023",
    "marks_history": [4, 4, 8, 4, 8, 4, 4],
}
```

### 2.6 Evaluation / Backtesting Framework

**Method:** Train on years <= Y-1, predict for year Y, compare against actual paper.

| Metric | Definition | Target |
|--------|-----------|--------|
| **Topic Hit Rate** | % of predicted top-K topics that actually appeared | > 60% for top-20 |
| **Marks Coverage** | % of total marks covered by predicted topics | > 70% |
| **Precision@K** | Of top K predictions, how many appeared? | > 0.5 at K=20 |
| **Recall@K** | Of topics that appeared, how many were in top K? | > 0.6 at K=30 |
| **Weightage Error** | |predicted_marks - actual_marks| per topic | < 4 marks avg |
| **Rank Quality (NDCG)** | Are high-probability topics ranked higher? | > 0.7 |
| **Calibration** | Do topics scored 0.8 actually appear 80% of the time? | Plot calibration curve |
| **Confidence Accuracy** | Do HIGH confidence predictions hit more than LOW? | HIGH > 70%, LOW < 40% |

**Backtesting loop:**
```
for test_year in [2019, 2020, 2021, 2022, 2023]:
    train on years < test_year
    predict for test_year
    compare predictions against actual test_year paper
    compute all metrics
    report per-year and averaged
```

### 2.7 Data Model / Table Design

#### Enhanced `questions` table (add columns)

```sql
ALTER TABLE questions ADD COLUMN marks_awarded INTEGER;  -- actual marks for this Q
ALTER TABLE questions ADD COLUMN section TEXT;            -- Section A/B/C if applicable
ALTER TABLE questions ADD COLUMN is_optional INTEGER DEFAULT 0;
```

#### New `topic_predictions` table

```sql
CREATE TABLE topic_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    target_year INTEGER NOT NULL,
    exam TEXT NOT NULL,
    subject TEXT,
    topic TEXT NOT NULL,
    micro_topic TEXT NOT NULL,
    appearance_probability REAL,
    expected_marks_min INTEGER,
    expected_marks_mid INTEGER,
    expected_marks_max INTEGER,
    likely_question_types TEXT,   -- JSON array
    likely_difficulty REAL,
    trend_direction TEXT,
    syllabus_status TEXT,
    confidence TEXT,
    confidence_score REAL,
    signal_breakdown TEXT,        -- JSON object
    reasons TEXT,                 -- JSON array
    training_years TEXT
);
```

#### New `syllabus_status` table

```sql
CREATE TABLE syllabus_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam TEXT NOT NULL,
    effective_year INTEGER NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    micro_topic TEXT,
    status TEXT NOT NULL,         -- RETAINED, MODIFIED, NEW, REMOVED
    change_description TEXT,
    trust_multiplier REAL DEFAULT 1.0,
    proxy_score REAL DEFAULT 0.0
);
```

#### New `backtest_results` table

```sql
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_year INTEGER NOT NULL,
    exam TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    k_value INTEGER,             -- for precision@k, recall@k
    run_date TEXT
);
```

---

## 3. Part B: Dashboard Framework

### 3.1 Design Goals

1. **Decision-oriented:** Every widget answers "what should I do?"
2. **Explainable:** No black-box scores — every number has a "why"
3. **Confidence-layered:** Users see how much to trust each prediction
4. **Role-appropriate:** Students see study priorities; teachers see blueprint patterns
5. **Actionable:** Every insight connects to a preparation action (study this, skip that, practice this format)

### 3.2 Layout Structure (7 Pages)

```
Page 1: COMMAND CENTER (Overview + KPIs)
Page 2: PREDICTION DEEP DIVE (Ranked topics + explainability)
Page 3: TOPIC INTELLIGENCE (Click-to-explore topic analysis)
Page 4: SYLLABUS & LESSON PLAN (Coverage + study priorities)
Page 5: HISTORICAL TIMELINE (Events + pattern correlation)
Page 6: QUESTION EXPLORER (Search + filter + browse)
Page 7: PAPER SIMULATOR (Blueprint generator + PDF export)
```

### 3.3 Widgets and Visuals

#### Page 1: COMMAND CENTER

| Widget | Type | Data |
|--------|------|------|
| **Model Confidence** | Gauge card | Overall model confidence for this exam |
| **Top 5 Predicted Topics** | Metric cards | Highest-probability topics with scores |
| **Expected Marks Coverage** | Progress bar | % of paper marks our top-30 predictions cover |
| **Syllabus Impact** | Alert card | "18 chapters removed, 9 topics added" |
| **Pattern Shift** | Delta card | "Difficulty up 12% vs last 3yr average" |
| **Subject Weightage Trend** | Stacked area chart | % per subject over time |
| **Difficulty Evolution** | Line chart with markers | Mean difficulty per subject per year |
| **Question Type Mix** | Stacked bar (historical) + predicted bar | MCQ/numerical/assertion-reason trend |

#### Page 2: PREDICTION DEEP DIVE

| Widget | Type | Data |
|--------|------|------|
| **Main Prediction Table** | Sortable data table | See column design below |
| **Probability Bar Chart** | Horizontal bars, color=confidence | Top-N topics ranked |
| **Score vs Confidence Scatter** | Scatter plot | x=probability, y=confidence, size=marks |
| **Signal Waterfall** | Waterfall chart (on topic click) | Per-signal contribution breakdown |
| **Download Buttons** | CSV + PDF | Export predictions |

**Main Prediction Table Columns:**

| Column | Type |
|--------|------|
| Rank | int |
| Subject | text |
| Chapter | text |
| Micro-Topic | text |
| Appearance Probability | bar-in-cell |
| Expected Marks | range (e.g., "4-8") |
| Trend | arrow icon (↑ ↗ → ↘ ↓) |
| Last Asked | year |
| Likely Format | icon chips (MCQ, NUM, etc.) |
| Difficulty | colored dots (1-5) |
| Syllabus Status | badge (RETAINED/NEW/etc.) |
| Confidence | colored badge (HIGH/MED/LOW) |

#### Page 3: TOPIC INTELLIGENCE (existing Deep Topic Analysis, enhanced)

Keep existing + add:
- **Signal waterfall** when topic is selected
- **Similar topics** (co-occurrence based)
- **"Generate practice for this topic" button**

#### Page 4: SYLLABUS & LESSON PLAN (existing, enhanced)

Add:
- **Retained/Modified/New/Removed** filter tabs
- **Estimated study hours** per chapter (based on question density)
- **Priority matrix** scatter: x=probability, y=marks potential, color=confidence

#### Page 5: HISTORICAL TIMELINE (keep as-is)

#### Page 6: QUESTION EXPLORER (keep as-is)

#### Page 7: PAPER SIMULATOR (enhanced Paper Generator)

New features:
- **Blueprint mode:** Auto-generate a realistic paper matching exam blueprint
- **Section-wise view:** Section A (MCQs), Section B (numerical), etc.
- **Difficulty slider:** Target difficulty level
- **Predicted vs historical:** Option to generate from predicted-likely topics only
- **Download as PDF** (existing)

### 3.4 Explainability and Trust Design

Every prediction must answer three questions:
1. **What?** — The prediction itself (probability, marks, format)
2. **Why?** — Signal breakdown waterfall showing contribution of each metric
3. **How sure?** — Confidence badge + supporting evidence count

**Waterfall chart format:**
```
Base score:          0.00
+ Recency frequency: +0.18  [████████░░]
+ Trend slope:       +0.09  [████░░░░░░]
+ Gap return:        +0.05  [██░░░░░░░░]
+ Marks stability:   +0.09  [████░░░░░░]
+ Cross-exam:        +0.04  [██░░░░░░░░]
+ Chapter spread:    +0.03  [█░░░░░░░░░]
× Syllabus gate:     ×1.0   [RETAINED]
= Final score:       0.48
```

### 3.5 User-Specific Views

| User | Primary Page | Key Metrics | Actions |
|------|-------------|-------------|---------|
| **Student** | Lesson Plan → Predictions | "What to study", priority, difficulty | Generate practice PDF, study plan |
| **Teacher** | Predictions → Paper Simulator | Blueprint, marks distribution, trend | Generate mock paper, topic coverage report |
| **Management** | Command Center | Model accuracy, pattern shifts, coverage | Backtest results, year-over-year comparison |

### 3.6 MVP Dashboard (what we implement now)

1. Enhanced prediction table with all new columns
2. Signal breakdown waterfall per topic
3. Confidence tiers (HIGH/MEDIUM/LOW/SPECULATIVE)
4. Trend direction arrows
5. Marks range prediction
6. Question type prediction
7. Syllabus status badges
8. Backtest results display
9. Paper blueprint simulator
10. CSV/PDF downloads everywhere

### 3.7 Advanced Dashboard (future)

1. Bayesian calibration curves
2. "What-if" simulator (what if syllabus changes X?)
3. Personalized study plan (based on student's weak areas)
4. Collaborative filtering (students who scored well focused on these topics)
5. Real-time model retraining when new paper data arrives

---

## 4. Final Recommendations

1. **Strongest signals:** Recency-weighted frequency and syllabus status are the two most reliable predictors. Optimize these first.
2. **Weakest signals:** News correlation and concept density are speculative. Include but weight low.
3. **Critical gate:** Syllabus status should be a multiplicative gate, not additive. A removed topic must score 0 regardless of history.
4. **Confidence ≠ Probability:** A topic can have high probability but low confidence (e.g., new topic expected to appear but no historical evidence). Display both.
5. **Backtest religiously:** Run backtesting on 2019-2023 before trusting the model. If precision@20 < 0.4, the model needs more tuning before deployment.
6. **Marks > Appearance:** Predicting marks weightage is more useful than binary appearance. A topic appearing for 4 marks vs 12 marks changes study priority entirely.

---

## 5. Implementation Roadmap

### Phase 1 (Now): Core Model Upgrade
- [ ] Implement recency-weighted frequency
- [ ] Add trend slope calculation
- [ ] Add marks weightage prediction
- [ ] Add question type prediction
- [ ] Add confidence scoring (separate from probability)
- [ ] Add syllabus status gate
- [ ] Implement new output schema
- [ ] Build backtesting framework
- [ ] Update dashboard: prediction table, waterfall, confidence

### Phase 2 (Next): Dashboard Polish
- [ ] Paper blueprint simulator
- [ ] Priority matrix scatter plot
- [ ] Estimated study hours
- [ ] User role views
- [ ] Export everywhere (CSV, PDF)

### Phase 3 (Future): Advanced
- [ ] Calibration curves
- [ ] What-if simulator
- [ ] Auto-retrain on new data
- [ ] Personalized study plans
