# Subject Pages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the wall-of-text deep analysis tree with clickable subject cards that open full-page subject views with 4 structured zones (KPIs, priority actions, chapter breakdown, exam history).

**Architecture:** Single-page JS view switching inside `student-dashboard.html`. New state `G.subjectView` controls which view is visible. `openSubject(name)` hides `#dash` and renders a subject page in `#subject-view`. `closeSubject()` reverses. All data (student + predictions) is already in memory — zero new API calls.

**Tech Stack:** Vanilla JS, CSS variables matching existing design system, Chart.js (already loaded)

---

### Task 1: Add Subject View CSS

**Files:**
- Modify: `docs/student-dashboard.html` — CSS section (lines 110-147)

**Step 1: Replace deep analysis CSS with subject cards + subject view CSS**

Find and replace the entire `/* DEEP ANALYSIS */` CSS block (lines 110-147, from `/* DEEP ANALYSIS */` through `.roi-ok{color:#22c55e}`) with new CSS for subject cards grid, subject view layout, KPI strip, priority table, chapter cards, micro-topic table, and history bars. Keep `.roi-crit`, `.roi-focus`, `.roi-review`, `.roi-ok` classes.

**Step 2: Commit**

Run: `git add docs/student-dashboard.html && git commit -m "style: subject cards + subject view CSS (replaces deep analysis styles)"`

---

### Task 2: Add Subject View HTML Container

**Files:**
- Modify: `docs/student-dashboard.html` — line 316

**Step 1: Add `#subject-view` div after `#dash`**

Find:
```html
    <div class="dash" id="dash" style="display:none"></div>
```

Add immediately after:
```html
    <div id="subject-view"></div>
```

**Step 2: Commit**

Run: `git add docs/student-dashboard.html && git commit -m "chore: add #subject-view container to HTML"`

---

### Task 3: Replace buildDeepAnalysis with buildSubjectCards

**Files:**
- Modify: `docs/student-dashboard.html` — JS functions (lines 597-810)

**Step 1: Delete `_refreshDeepAnalysis`, `buildDeepAnalysis`, and `_buildDeepContent`**

Remove everything from line 597 (`function _refreshDeepAnalysis`) through the closing `}` of `_buildDeepContent` (just before `/* ── Main render ── */`).

**Step 2: Add shared utilities and buildSubjectCards**

Insert at the same location:

- Constants: `SUBJ_COL`, `SUBJ_ICO`, `TREND_ICO` color/icon maps
- `_stuAccFor(s, name)` — student accuracy lookup (chapters dict -> subjects dict fallback)
- `_roiCalc(stuAcc, prob, conf)` — ROI formula: `(1 - acc/100) * prob * max(conf, 0.5)`
- `_roiCls(r)` / `_roiLbl(r)` — ROI classification (CRITICAL/FOCUS/REVIEW/OK)
- `_buildSubjectTree(s, preds, subjectFilter)` — groups predictions by chapter, computes ROI for all micro-topics, returns `{tree, allMicros}` sorted by ROI descending
- `buildSubjectCards(s)` — renders subject card grid. Each card shows: subject icon+name, student accuracy bar, PRAJNA exam load, CRITICAL/FOCUS count, chapter+micro count, "Explore →" link. Clicking calls `openSubject(subj)`.

**Step 3: Update render() call**

Find: `dash.appendChild(buildDeepAnalysis(s));`
Replace: `dash.appendChild(buildSubjectCards(s));`

**Step 4: Update pick() to re-render on prediction load instead of refreshing old deep analysis**

Find in pick(): `_refreshDeepAnalysis(s)`
Replace: `render(s)`

**Step 5: Commit**

Run: `git add docs/student-dashboard.html && git commit -m "feat: subject cards grid — replaces deep analysis tree with clickable cards"`

---

### Task 4: Build Subject View (openSubject / closeSubject / buildSubjectView)

**Files:**
- Modify: `docs/student-dashboard.html` — add after buildSubjectCards, before `/* ── Main render ── */`

**Step 1: Add view switching functions**

- `openSubject(subj)` — sets `G.subjectView`, hides `#dash`, shows `#subject-view`, renders subject page, scrolls to top
- `closeSubject()` — clears `G.subjectView`, hides `#subject-view`, shows `#dash`

**Step 2: Add buildSubjectView(s, subj)**

Renders 4 zones using DOM creation (el() helper, createElement, createDocumentFragment):

**Zone A — KPI Strip** (4 cards in grid):
- Student accuracy + level classification
- PRAJNA exam load (avg probability) + total expected questions
- Critical micro-topic count + focus/on-track breakdown
- Chapters predicted + total micro-topic count

**Zone B — Top 5 Priority Actions** (table):
- Header row: Micro-Topic | Chapter | Your % | PRAJNA | Priority
- 5 rows from allMicros.slice(0,5) — highest ROI first
- Each cell: name, chapter name, colored accuracy, colored probability, ROI badge

**Zone C — Chapter Breakdown** (collapsible details):
- Each chapter as `<details>` (collapsed by default)
- Summary: arrow icon, chapter name, pills (Your %, PRAJNA %, expected Qs + trend)
- Body: signal badges row, history metadata line (years appeared, expected Qs, confidence), proper `<table>` for micro-topics (Name | Your % | PRAJNA | Priority)
- Chapters sorted by max micro ROI descending

**Zone D — Question Distribution** (bar chart):
- Top 12 chapters by expected questions
- Vertical bars with labels and values
- Uses CSS flexbox bars (no Chart.js dependency for this)

**Step 3: Update state initialization**

Find: `const G = { exam:'neet', data:{neet:null,jee:null}, stu:null, charts:{}, microPreds:{} };`
Add: `subjectView:null` to the object

**Step 4: Close subject view on student/exam switch**

Add `if(G.subjectView) closeSubject();` at top of both `pick(s)` and `switchExam(exam)`.

**Step 5: Commit**

Run: `git add docs/student-dashboard.html && git commit -m "feat: subject view — full-page per-subject analysis with 4 zones"`

---

### Task 5: Verify and Push

**Step 1: Start services**

Run: `pm2 status` — ensure `prajna-intelligence` (8001) and `prajna` (4000) are online.

**Step 2: Test in browser**

1. Navigate to `http://localhost:4000/student-dashboard.html?exam=neet`
2. Login, select a student
3. Scroll to "PRAJNA Deep Analysis" — verify 3-4 subject cards (not old tree)
4. Click Physics card → full subject view opens
5. Verify Zone A: 4 KPI cards with correct data
6. Verify Zone B: Top 5 micro-topics in proper table
7. Verify Zone C: Collapsed chapters, expand one → micro-topic table with aligned columns
8. Verify Zone D: Bar chart of expected questions
9. Click "← Back to Dashboard" → returns to main view
10. Switch to JEE → verify 3 cards (Physics, Chemistry, Mathematics)

**Step 3: Push and deploy**

Run: `git push origin main && vercel --prod --yes`
