# PRAJNA Portal — 100% Feature-Complete Design

**Date:** 2026-04-01
**Status:** Approved
**Repos:** `firnweh/prajna-portal` (frontend), `firnweh/prajna-slm` (backend)

## Goal

Rebuild the PRAJNA portal to 100% of its potential: 14 React pages replacing all Streamlit tabs, integrating 3 PhysicsWallahAI HuggingFace datasets (2.1M+ questions), full AI tutor chatbot, and complete prediction engine — all native React, zero iframe.

## Architecture Overview

```
Browser → Next.js Portal (14 pages)
            ├── /api/proxy/backend → Node.js (auth, students, branches)
            ├── /api/proxy/intel   → Python FastAPI
            │                        ├── exam.db (23K Qs — predictions)
            │                        └── qbg.db  (1.14M Qs — question bank + copilot)
            └── No Streamlit (fully retired)
```

## Databases

### exam.db (unchanged)
- 23K questions from 48 years of actual NEET/JEE papers
- Has year/paper metadata required for prediction engine
- Powers: predictions, backtest, hot/cold, lesson plan, topic deep-dive

### qbg.db (NEW — built from 3 HF datasets)

**Sources merged by qbgid:**
- `PhysicsWallahAI/qbg-pcmr` (1.14M) — raw questions, solutions, difficulty, exam labels
- `PhysicsWallahAI/qbg-pcmr-1` (983K) — cleaned/deduplicated with structured metadata
- `PhysicsWallahAI/gpt-oss` (983K) — GPT-generated step-by-step analysis per question

**Schema:**
```sql
CREATE TABLE questions (
  qbgid TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  topic TEXT,
  difficulty TEXT,
  type TEXT,
  category TEXT,
  exam_label TEXT,
  question_raw TEXT,
  question_clean TEXT,
  answer_clean TEXT,
  options TEXT,          -- JSON array
  correct_options TEXT,  -- JSON array
  text_solution TEXT,    -- human solution (pcmr)
  gpt_analysis TEXT,     -- GPT step-by-step (gpt-oss)
  similarity_score REAL
);
CREATE VIRTUAL TABLE questions_fts USING fts5(question_clean, topic, subject);
```

**Filter:** category IN ('NEET-JEE', 'JEE', 'Foundation'). Exclude Banking/MBA/UPSC.
**Result:** ~1.14M unique questions with merged fields from all 3 datasets.

**Powers:** copilot Q&A, question bank explorer, mock test generator, topic deep-dive samples.

## New API Endpoints (Python FastAPI)

```
GET  /api/v1/qbank/search?query=X&subject=Y&top_n=10
GET  /api/v1/qbank/random?subject=X&topic=Y&difficulty=Z&count=30&type=single_correct
GET  /api/v1/qbank/stats
POST /api/v1/qbank/mock-test  {subject, topics[], difficulty, count, type}
POST /api/v1/copilot/practice {topic, difficulty, count}
GET  /api/v1/mistakes/danger-zones?exam_type=X
GET  /api/v1/mistakes/cofailure?exam_type=X
GET  /api/v1/mistakes/predict?student_id=X&exam_type=Y
```

## Pages (14 total)

### 1. `/student` — Student Dashboard (8 sections)

| Section | Data Source | Component |
|---------|-----------|-----------|
| Hero card (name, score, rank, zone, progress bar) | Backend /api/students | Custom |
| KPI strip (6 cards: avg, best, improvement, consistency, best rank, trend/exam) | student.metrics | KpiStrip |
| Score trajectory chart (10 exams) | student.metrics.trajectory | Recharts LineChart |
| Subject radar chart (abilities spider) | student.abilities | Recharts RadarChart |
| PRAJNA study priority summary (critical/focus/ok counts) | Intel /predict + student.chapters | Custom |
| Subject cards (3-4, clickable → /student/[subject]) | Computed from predictions + chapters | SubjectCard |
| SLM Focus panel (top 5 chapters by slm_priority_score) | student.slm_focus | Custom |
| Chapter heatmap + weakness zones (C/W chapters highlighted) | student.chapters | Custom |

### 2. `/student/[subject]` — Subject Deep-Dive (4 zones)

| Zone | Content |
|------|---------|
| A: KPI strip | Accuracy, PRAJNA load, critical count, chapters predicted |
| B: Top 5 priority actions | Highest ROI micro-topics |
| C: Chapter breakdown | Collapsible ChapterRows with micro-topic table, signals, ROI badges |
| D: Subject exam history | Recharts bar chart of questions per year from this subject |

### 3. `/org` — Organisation Dashboard (7 sections)

| Section | Content |
|---------|---------|
| Filter bar | Branch, city, target dropdowns + search + student count |
| KPI strip (5 cards) | Total students, avg score, critical, mastery, top scorer |
| Zone donut chart + PRAJNA intel | Recharts PieChart + top 8 predicted chapters |
| Branch cards + comparison bar chart | Grid of branch cards + Recharts horizontal bar |
| Subject health matrix | Branch × subject accuracy table, zone-colored cells |
| Student leaderboard (enhanced) | Sortable, +consistency, +sparkline, click-to-navigate |

### 4. `/org/risk` — At-Risk Students

Filtered view: only Critical (C) zone students, grouped by branch, with intervention recommendations and trend direction.

### 5. `/predictions` — Prediction Engine (5 sections)

| Section | Content |
|---------|---------|
| Filter bar | Subject, confidence threshold, trend, level |
| KPI strip (5 cards) | High-prob, expected Qs, rising, confidence, DB count (1.14M) |
| Top predictions (expandable 30→100) | Ranked micro-topics with prob bar, trend, expected Qs |
| Hot/cold topics (15 each) | Hot = recent frequent, cold = dormant due to return |
| Subject weightage timeline | Recharts AreaChart: subject % across years |

### 6. `/backtest` — Model Accuracy Validation

Config: test year, top K, level (chapter/micro). Shows hit rate, coverage, matched vs missed topics, year-by-year accuracy bar chart.
API: `GET /api/v1/data/backtest`

### 7. `/deep-dive/[topic]` — Topic Intelligence

Topic selector → header (prob, expected Qs, history) → frequency timeline (BarChart) + difficulty trend (LineChart) → micro-topic breakdown → sample questions from qbg.db.
APIs: `GET /api/v1/data/topic-deep-dive` + `GET /api/v1/qbank/search`

### 8. `/lesson-plan` — Syllabus-Mapped Study Plan

KPIs (total chapters, band A/B/C counts) → priority table (band, chapter, subject, prob, expected Qs) → subject split donut + band distribution bar.
API: `GET /api/v1/data/lesson-plan`

### 9. `/revision-plan` — Spaced Repetition Schedule

Config: days until exam, hours/day → day-by-day schedule with time blocks → subject hours pie chart + priority chapters.
API: `POST /api/v1/reports/revision-plan`

### 10. `/mistakes` — Mistake Analysis

Toggle: Center View / Student View.
Center: danger zones table, co-failure patterns, time-vs-accuracy scatter (Recharts).
Student: P(miss) table, personal danger zones, improvement trajectory (LineChart), feature importance (BarChart).
APIs: New `/api/v1/mistakes/*` endpoints wrapping MistakeAnalyzer + MistakePredictor.

### 11. `/copilot` — Full AI Tutor

Left: chat interface with conversation history. Right: suggested topics (from student weak areas), quick actions (practice, explain, strategy, deep-dive), practice mode (pull Qs from qbg.db, show Q → wait for answer → reveal solution + gpt_analysis).
APIs: `POST /api/v1/copilot/ask` + `POST /api/v1/copilot/practice` + `GET /api/v1/qbank/search`

### 12. `/question-bank` — Question Explorer (1.14M Qs)

Filters: subject, topic, difficulty, type → question cards with show/hide answer and solution → load more pagination.
API: `GET /api/v1/qbank/search` + `GET /api/v1/qbank/random`

### 13. `/mock-test` — Practice Test Generator

Config: subject, question count, time limit, difficulty, focus (weak topics / all). Generates test from qbg.db → interactive question-by-question UI with timer → submission → score + topic-wise breakdown + solutions.
API: `POST /api/v1/qbank/mock-test`

### 14. `/api-docs` — API Documentation

Links to FastAPI auto-generated docs for all three API groups (intelligence, qbank, backend).

## Sidebar Navigation

```
STUDENT:                    ORG:
────────                    ────
📊 My Dashboard             📊 Organisation
⚡ Physics                   🏢 Branches
🧪 Chemistry                👥 Student List
🧬 Biology / 📐 Math        ⚠ At-Risk Students
────────                    ────
🔮 Predictions              🔮 Predictions
📚 Lesson Plan              📚 Lesson Plan
📅 Revision Plan            📅 Revision Plan
🎯 Backtest                 🎯 Backtest
🧪 Mistake Analysis         🧪 Mistake Analysis
────────                    ────
🤖 Ask PRAJNA               🤖 Ask PRAJNA
📝 Question Bank            📝 Question Bank
📄 Mock Test                📄 Mock Test
🔬 Topic Deep Dive          🔬 Topic Deep Dive
────────                    ────
🔌 API Docs                 🔌 API Docs
```

## Retired

- `StreamlitEmbed.tsx` — deleted
- `app/analysis/` — deleted
- Streamlit iframe — no longer referenced
- All 11 Streamlit tabs replaced by native React pages

## Visual Design

Dark theme (unchanged): --bg #0f0f1a, --surface #131320, --card #1a1d2e, --accent #6366f1.
Subject colors: Physics=#f59e0b, Chemistry=#6366f1, Biology=#22c55e, Mathematics=#a855f7.
Charts: Recharts with dark theme (fill opacity, grid color #1e1e3a, label color #64748b).
Font: Inter. Responsive: desktop-first, sidebar collapses at 768px.

## Implementation Phases

### Phase 1: Data Pipeline (qbg.db build)
- Download 3 HF datasets
- Merge by qbgid, filter, extract topics
- Build qbg.db with FTS5
- New FastAPI router /api/v1/qbank/

### Phase 2: Student Dashboard Redesign
- Add trajectory chart, radar chart, SLM focus, heatmap, weakness zones
- 8 sections total

### Phase 3: Org Dashboard Redesign
- Add filter bar, donut chart, branch bar chart, subject matrix, enhanced leaderboard
- 7 sections total

### Phase 4: Prediction Engine Pages
- Predictions redesign (5 sections)
- Backtest page
- Lesson plan page
- Topic deep-dive page
- Subject timeline

### Phase 5: New Feature Pages
- Revision plan
- Mistake analysis (React native)
- At-risk cohort

### Phase 6: AI Tutor + Question Bank
- Copilot full page
- Question bank explorer
- Mock test generator
- Practice mode integration

### Phase 7: Cleanup
- Delete StreamlitEmbed, analysis page, Streamlit references
- Update sidebar navigation
- Final testing across all 14 pages

## Success Criteria

- All 14 pages render with real data
- Zero Streamlit references remaining
- qbg.db built with 1M+ questions from 3 HF datasets
- Copilot answers questions using pre-baked GPT analysis
- Mock test generates valid tests from qbg.db
- Student dashboard shows trajectory, radar, SLM focus, heatmap
- Org dashboard has filters, donut chart, subject matrix
- All existing prediction features accessible without iframe
