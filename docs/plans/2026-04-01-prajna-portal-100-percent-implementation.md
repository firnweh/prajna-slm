# PRAJNA Portal 100% Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the PRAJNA portal to 100% feature completeness — 14 React pages replacing all Streamlit tabs, 1.14M question bank from 3 HuggingFace datasets, full AI tutor, zero iframe.

**Architecture:** Next.js 16 App Router portal (`/Users/aman/prajna-portal/`) consuming Python FastAPI backend (`/Users/aman/exam-predictor/intelligence/`). Two SQLite databases: `exam.db` (23K Qs for predictions) and new `qbg.db` (1.14M Qs for question bank + copilot). All API calls proxied through Next.js server-side routes.

**Tech Stack:** Next.js 16, TypeScript, Tailwind v4, Recharts, Zustand, Python FastAPI, SQLite FTS5, HuggingFace Hub

**Design doc:** `/Users/aman/exam-predictor/docs/plans/2026-04-01-prajna-portal-100-percent-design.md`

---

## Phase 1: Data Pipeline (qbg.db)

### Task 1: Download and merge HuggingFace datasets into qbg.db

**Files:**
- Create: `/Users/aman/exam-predictor/analysis/build_qbg_db.py`
- Create: `/Users/aman/exam-predictor/tests/test_qbg_db.py`
- Output: `/Users/aman/exam-predictor/data/qbg.db`

**What it does:**
1. Downloads 3 HF datasets: `qbg-pcmr` (CSV, 1.14M), `qbg-pcmr-1` (JSONL, 983K), `gpt-oss` (JSONL, 983K)
2. Uses `qbg-pcmr` as the primary source (has all fields: question, answer, solution, difficulty, category, exam)
3. Joins `gpt-oss` by qbgid to add `gpt_analysis` (GPT step-by-step solutions)
4. Filters out non-NEET/JEE categories (Banking, MBA, UPSC, etc.)
5. Builds SQLite with FTS5 full-text search index on question_clean

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
    options TEXT,
    correct_options TEXT,
    text_solution TEXT,
    gpt_analysis TEXT,
    similarity_score REAL
);
CREATE VIRTUAL TABLE questions_fts USING fts5(question_clean, topic, subject, content=questions, content_rowid=rowid);
```

**Metadata parsing:** The qbgid is extracted from the `metadata` field in pcmr-1 and gpt-oss. The metadata field is a string-serialized dict — use `json.loads()` with a fallback for Python-style dict strings (replace single quotes with double quotes before parsing).

**Tests (7):** table exists, row count > 500K, schema has required columns, subjects include Physics/Chemistry, FTS search works, gpt_analysis populated for 100K+ rows, no banking data.

**Run:** `python analysis/build_qbg_db.py` (5-15 min, downloads ~3GB)
**Commit:** `feat: qbg.db build pipeline — merge 3 HF datasets (1.14M questions)`

Note: Add `data/qbg.db` to `.gitignore` (too large for git).

---

### Task 2: Question Bank API Router

**Files:**
- Create: `/Users/aman/exam-predictor/intelligence/services/api/routers/qbank.py`
- Modify: `/Users/aman/exam-predictor/intelligence/services/api/main.py` (add router import)

**Endpoints:**
- `GET /api/v1/qbank/search?query=X&subject=Y&difficulty=Z&top_n=10` — FTS5 search
- `GET /api/v1/qbank/random?subject=X&topic=Y&difficulty=Z&count=30` — random questions
- `GET /api/v1/qbank/stats` — counts by subject, difficulty, type
- `POST /api/v1/qbank/mock-test` — generate test (strips answers from response)

Each endpoint opens a connection to `data/qbg.db`, runs the query, returns JSON. Mock-test endpoint strips `answer_clean`, `correct_options`, `text_solution`, `gpt_analysis` from the response (student doesn't see answers until submission).

**Register in main.py:**
```python
from intelligence.services.api.routers.qbank import router as qbank_router
app.include_router(qbank_router)
```

**Commit:** `feat: question bank API — search, random, stats, mock-test endpoints`

---

### Task 3: Mistake Analysis API Endpoints

**Files:**
- Create: `/Users/aman/exam-predictor/intelligence/services/api/routers/mistakes.py`
- Modify: `/Users/aman/exam-predictor/intelligence/services/api/main.py` (add router)

Wraps existing `MistakeAnalyzer` and `MistakePredictor` from `analysis/`:
- `GET /api/v1/mistakes/danger-zones?exam_type=neet&error_threshold=0.4`
- `GET /api/v1/mistakes/cofailure?exam_type=neet`
- `GET /api/v1/mistakes/time-accuracy?exam_type=neet`
- `GET /api/v1/mistakes/predict?student_id=X&exam_type=neet`
- `GET /api/v1/mistakes/feature-importance?exam_type=neet`

Loads results CSV via `functools.lru_cache`. Creates MistakeAnalyzer/MistakePredictor on demand. For prediction endpoints, builds PRAJNA importance dict from `predict_chapters_v3()`.

**Commit:** `feat: mistake analysis API endpoints wrapping analyzer + predictor`

---

## Phase 2: Student Dashboard Redesign

### Task 4: Trajectory + Radar Charts

**Files:**
- Create: `/Users/aman/prajna-portal/components/charts/TrajectoryChart.tsx`
- Create: `/Users/aman/prajna-portal/components/charts/SubjectRadar.tsx`
- Modify: `/Users/aman/prajna-portal/app/student/page.tsx`

TrajectoryChart: Recharts `LineChart`, X=exam number (1-10), Y=score %, blue line + dashed gray average line. Props: `data: number[]`.
SubjectRadar: Recharts `RadarChart` with `PolarGrid`, `PolarAngleAxis`. Props: `abilities: Record<string, number>`. Maps to subjects with colors.
Insert between KPI strip and PRAJNA summary as a 2-column row.

**Commit:** `feat: student dashboard — trajectory chart + subject radar`

### Task 5: SLM Focus Panel

**Files:**
- Create: `/Users/aman/prajna-portal/components/dashboard/SlmFocusPanel.tsx`
- Modify: `/Users/aman/prajna-portal/app/student/page.tsx`

Renders `student.slm_focus` (array of `{chapter, accuracy, level, slm_importance, slm_priority_score}`). Top 5 sorted by priority_score desc. Each row: rank, chapter name, accuracy%, importance bar, priority badge.

**Commit:** `feat: student dashboard — SLM focus panel`

### Task 6: Chapter Heatmap + Weakness Zones

**Files:**
- Create: `/Users/aman/prajna-portal/components/dashboard/ChapterHeatmap.tsx`
- Create: `/Users/aman/prajna-portal/components/dashboard/WeaknessZones.tsx`
- Modify: `/Users/aman/prajna-portal/app/student/page.tsx`

ChapterHeatmap: groups `student.chapters` by subject, renders accuracy bars zone-colored, sorted weakest first within each subject group.
WeaknessZones: filters chapters to C+W zones only, shows count + action items.

**Commit:** `feat: student dashboard — chapter heatmap + weakness zones`

### Task 7: Student Dashboard — 6 KPIs + Hero Polish

Expand KPI from 4→6 cards (+best_rank, +trend_per_exam). Hero: add rank, zone badge, progress bar.

**Commit:** `feat: student dashboard — 6 KPIs + polished hero`

---

## Phase 3: Org Dashboard Redesign

### Task 8: Filter Bar

**Files:** Create `components/org/FilterBar.tsx`, modify `app/org/page.tsx`

4 dropdowns (branch, city, target, search) + clear + count. All frontend filtering via Zustand.

**Commit:** `feat: org dashboard — filter bar`

### Task 9: Zone Donut + Branch Bar Chart

**Files:** Create `components/charts/ZoneDonut.tsx`, `components/charts/BranchBarChart.tsx`, modify `app/org/page.tsx`

Recharts PieChart (innerRadius=60%) + horizontal BarChart. Zone colors. 2-column layout.

**Commit:** `feat: org dashboard — zone donut + branch bar chart`

### Task 10: Subject Matrix + Enhanced Leaderboard

**Files:** Create `components/org/SubjectMatrix.tsx`, modify `app/org/page.tsx`

Branch×subject table with zone-colored cells. Leaderboard: +consistency, +sparkline SVG, click→navigate.

**Commit:** `feat: org dashboard — subject matrix + enhanced leaderboard`

### Task 11: At-Risk Page

**Files:** Create `app/org/risk/page.tsx`

C-zone students grouped by branch, intervention recommendations.

**Commit:** `feat: at-risk students page`

---

## Phase 4: Prediction Engine Pages

### Task 12: Predictions Redesign

Add filter bar, expand to 100, subject weightage timeline AreaChart, qbank stats KPI.

**Commit:** `feat: predictions — filters, expandable, timeline`

### Task 13: Backtest Page

**Files:** Create `app/backtest/page.tsx` + layout

Config (year, K, level) → KPIs → matched/missed tables → year-by-year BarChart.
API: `GET /api/v1/data/backtest`

**Commit:** `feat: backtest page`

### Task 14: Topic Deep-Dive Page

**Files:** Create `app/deep-dive/[topic]/page.tsx` + `app/deep-dive/page.tsx` + layout

Topic selector → header → frequency BarChart + difficulty LineChart → micro-topics → sample Qs from qbg.
APIs: `/api/v1/data/topic-deep-dive` + `/api/v1/qbank/search`

**Commit:** `feat: topic deep-dive page`

### Task 15: Lesson Plan Page

**Files:** Create `app/lesson-plan/page.tsx` + layout

KPIs → priority table (band A/B/C) → subject DonutChart + band BarChart.
API: `GET /api/v1/data/lesson-plan`

**Commit:** `feat: lesson plan page`

---

## Phase 5: New Feature Pages

### Task 16: Revision Plan Page

Config (days, hours) → `POST /api/v1/reports/revision-plan` → day-by-day schedule + PieChart + priorities.

**Commit:** `feat: revision plan page`

### Task 17: Mistake Analysis Page (React)

Toggle center/student. Center: danger zones, co-failure, scatter. Student: P(miss), trajectory, features.
APIs: `/api/v1/mistakes/*`

**Commit:** `feat: mistake analysis page`

---

## Phase 6: AI Tutor + Question Bank

### Task 18: Copilot Page

Chat interface + suggestions + practice mode. Uses `/api/v1/copilot/ask` + `/api/v1/qbank/search`.

**Commit:** `feat: copilot AI tutor page`

### Task 19: Question Bank Explorer

Filter bar → question cards → collapsible answers/solutions → pagination.

**Commit:** `feat: question bank explorer`

### Task 20: Mock Test Generator

Config → generate → interactive test UI → submit → score + breakdown.

**Commit:** `feat: mock test generator`

---

## Phase 7: Cleanup

### Task 21: Update Sidebar

Add all 14 pages to nav configs. Remove Streamlit reference.

**Commit:** `feat: complete sidebar navigation`

### Task 22: Delete Streamlit

Remove StreamlitEmbed, analysis page, NEXT_PUBLIC_STREAMLIT_URL.

**Commit:** `chore: remove Streamlit — fully native`

### Task 23: API Docs Page

Links to FastAPI docs.

**Commit:** `feat: API docs page`

### Task 24: Deploy

Push both repos, Vercel deploy.

**Commit:** `chore: deploy 100% portal`

---

## Summary

| Phase | Tasks | Pages/Features |
|-------|-------|----------------|
| 1. Data | 1-3 | qbg.db, qbank API, mistakes API |
| 2. Student | 4-7 | +trajectory, +radar, +SLM, +heatmap, +6 KPIs |
| 3. Org | 8-11 | +filters, +donut, +bar, +matrix, +leaderboard, +risk |
| 4. Predictions | 12-15 | predictions, backtest, deep-dive, lesson plan |
| 5. Features | 16-17 | revision plan, mistake analysis |
| 6. AI Tutor | 18-20 | copilot, question bank, mock test |
| 7. Cleanup | 21-24 | sidebar, delete Streamlit, API docs, deploy |

**Total: 24 tasks, 7 phases, 14 pages, 1.14M question DB**
