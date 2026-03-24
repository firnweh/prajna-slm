# Design: Per-Subject Deep Analysis Pages

## Problem

The current PRAJNA Deep Analysis section renders 200 micro-topics in a single collapsible tree (subject → chapter → micro-topic). With 68 chapters across 3 subjects, this creates a wall of text with minimal spacing, no visual hierarchy, and no actionable summary. Users must scroll through everything to find what matters.

## Solution

Replace the deep analysis tree with **clickable subject cards** on the main dashboard. Each card opens a **full-page subject view** (JS view switch, no page reload) with 4 structured zones: KPI strip, priority actions, chapter breakdown, and exam history.

- **NEET:** 4 subject pages (Physics, Chemistry, Botany, Zoology)
- **JEE:** 3 subject pages (Physics, Chemistry, Mathematics)

## Architecture: Single-Page View Switching

All content stays in `student-dashboard.html`. No new files.

```
State: G.subjectView = null | "Physics" | "Chemistry" | ...

openSubject("Physics"):
  1. G.subjectView = "Physics"
  2. Hide #dash
  3. Show #subject-view (created if needed)
  4. Render buildSubjectView(student, "Physics")

closeSubject():
  1. G.subjectView = null
  2. Hide #subject-view
  3. Show #dash
```

## Data Flow (No New API Calls)

```
Already in memory:
  G.microPreds[exam]   →  200 micro-topic predictions (fetched on student pick)
  s.chapters            →  per-chapter accuracy [acc, level, maxMarks]
  s.subjects            →  per-subject {acc, level, trend, exams}

On openSubject(subjectName):
  preds = G.microPreds[exam].filter(p => p.subject === subjectName)
  tree  = group preds by chapter
  For each chapter:
    chAcc = s.chapters[chapter] or s.subjects[subject].acc (fallback)
    For each micro-topic:
      roi = (1 - stuAcc/100) × appearance_prob × max(confidence, 0.5)
  Sort chapters by max(micro ROI) descending
```

## Layout: Subject Page Zones

### Main Dashboard — Subject Cards (replaces deep analysis tree)

```
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│ ⚡ Physics │  │ 🧪 Chem   │  │ 🌿 Botany │  │ 🧬 Zoology│
│ Your: 40% │  │ Your: 55% │  │ Your: 80% │  │ Your: 85% │
│ PRAJNA:99%│  │ PRAJNA:92%│  │ PRAJNA:88%│  │ PRAJNA:85%│
│ ⚠ 23 CRIT │  │ ⚡ 12 FOCUS│  │ ✓ 3 CRIT │  │ ✓ 2 CRIT │
│ Explore → │  │ Explore → │  │ Explore → │  │ Explore → │
└───────────┘  └───────────┘  └───────────┘  └───────────┘
```

### Subject View — 4 Zones

**Zone A: Subject KPI Strip**
4 cards — student accuracy, PRAJNA exam load, critical micro-topic count, chapter count

**Zone B: Top 5 Priority Actions**
Highest-ROI micro-topics sorted descending. Each row: chapter → micro-topic, student %, PRAJNA %, ROI badge. These are "do this TODAY" items.

**Zone C: Chapter Breakdown (collapsible)**
Each chapter as `<details>` (collapsed by default):
- Header: chapter name, student acc, PRAJNA prob, expected Qs, trend icon
- Body: signal badges + micro-topic table (proper columns: Name, Your %, PRAJNA %, ROI)
- Generous padding (16px), clear section dividers

**Zone D: Subject Exam History**
Bar showing total predicted questions per chapter (from expected_questions field). Visual overview of where exam weight falls within this subject.

## ROI Classification

```
roi = (1 - student_accuracy/100) × appearance_probability × max(confidence_score, 0.5)

ROI > 0.4  → ⚠ CRITICAL (red)    — weak + high probability + high confidence
ROI > 0.25 → ⚡ FOCUS (amber)     — moderate gap + likely to appear
ROI > 0.1  → 📘 REVIEW (blue)    — small gap or lower probability
ROI ≤ 0.1  → ✓ OK (green)        — strong or low probability
```

## CSS Classes (New)

### Subject Cards (main dashboard)
- `.subj-cards` — grid container (auto-fit, minmax 220px)
- `.subj-card` — clickable card with subject color border-left
- `.subj-card-name`, `.subj-card-acc`, `.subj-card-prajna`, `.subj-card-crit`, `.subj-card-explore`

### Subject View
- `#subject-view` — full-width container (hidden by default)
- `.sv-header` — back button + subject name + exam badge
- `.sv-kpi-row` — 4-card KPI strip
- `.sv-kpi` — individual KPI card
- `.sv-priority` — top-5 priority actions container
- `.sv-priority-row` — individual action row
- `.sv-chapter` — `<details>` chapter card
- `.sv-ch-header` — chapter summary row
- `.sv-micro-table` — proper table for micro-topics
- `.sv-micro-row` — table row
- `.sv-history` — exam history bar chart container

## Functions (New/Modified)

### Modified
- `buildDeepAnalysis(s)` → renamed to `buildSubjectCards(s)` — renders subject card grid instead of tree
- `render(s)` — calls `buildSubjectCards` instead of `buildDeepAnalysis`

### New
- `openSubject(name)` — switches view to subject page
- `closeSubject()` — returns to main dashboard
- `buildSubjectView(s, subj)` — renders the full subject page (zones A-D)
- `_buildSVKPI(s, subj, preds)` — Zone A
- `_buildSVPriority(s, subj, preds)` — Zone B
- `_buildSVChapters(s, subj, preds)` — Zone C
- `_buildSVHistory(subj, preds)` — Zone D

## Verification

1. Start pm2 services (prajna-intelligence on 8001, prajna backend on 4000)
2. Login as student, select a NEET student
3. See 4 subject cards (Physics, Chemistry, Botany, Zoology) — NOT the old wall-of-text tree
4. Click Physics → full subject page with 4 zones
5. Zone B shows top 5 actionable micro-topics
6. Zone C chapters are collapsed by default, expand to see micro-topic table
7. Click "← Back to Dashboard" → returns to main dashboard
8. Switch to JEE → see 3 subject cards (Physics, Chemistry, Mathematics)
9. Check mobile: cards stack vertically, table scrolls horizontally
