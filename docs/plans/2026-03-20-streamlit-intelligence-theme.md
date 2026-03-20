# Streamlit → Intelligence Dashboard Theme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle the Streamlit dashboard to visually match the intelligence HTML dashboard — same dark theme, compact header, horizontal filter bar, card grid KPIs, and tab styling — without changing any data logic or introducing fake data.

**Architecture:** Pure CSS + layout restructure. All `@st.cache_data` prediction calls, analysis imports, DB queries, and tab logic stay identical. Only the CSS block (lines 83–426), `config.toml`, the hero HTML block (lines 447–473), and chart `update_layout` defaults change.

**Tech Stack:** Streamlit CSS injection (`st.markdown unsafe_allow_html`), Plotly `update_layout`, Python `st.columns()`, `.streamlit/config.toml`

---

### Task 1: Flip config.toml to dark theme

**Files:**
- Modify: `.streamlit/config.toml`

**Step 1: Replace config.toml content**

```toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
primaryColor            = "#6366f1"
backgroundColor         = "#0f0f1a"
secondaryBackgroundColor = "#131320"
textColor               = "#e2e8f0"
font                    = "sans serif"
```

**Step 2: Verify change saved**
Run: `cat .streamlit/config.toml`
Expected: dark backgroundColor `#0f0f1a`

**Step 3: Commit**
```bash
git add .streamlit/config.toml
git commit -m "style: flip streamlit theme to dark (#0f0f1a)"
```

---

### Task 2: Rewrite the entire CSS block (lines 83–426)

**Files:**
- Modify: `dashboard/app.py:83-426`

**Step 1: Replace the entire `st.markdown("""<style>...</style>""")` block**

The current block has duplicate conflicting rules (section-divider defined twice, metric cards defined twice with light + dark versions). Replace the entire block with the clean intelligence-dashboard-matched CSS:

```python
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');

  /* ── Global ── */
  .stApp { background:#0f0f1a !important; font-family:'Inter',system-ui,sans-serif; }
  .block-container { padding-top:0 !important; max-width:1480px; padding-left:1.5rem; padding-right:1.5rem; }
  [data-testid="stHeader"] { background:transparent !important; }
  [data-testid="stSidebar"] { display:none !important; }
  section[data-testid="stSidebarContent"] { display:none !important; }

  /* ── Compact topbar ── */
  .prajna-topbar {
    display:flex; align-items:center; justify-content:space-between;
    background:#0f0f1a; border-bottom:1px solid rgba(255,255,255,0.06);
    padding:0 1.5rem; height:56px;
    position:sticky; top:0; z-index:200;
    margin:0 -1.5rem 0 -1.5rem;
  }
  .prajna-topbar-left { display:flex; align-items:center; gap:12px; }
  .prajna-logo-circle {
    width:36px; height:36px; border-radius:50%; background:white;
    display:flex; align-items:center; justify-content:center;
    font-size:13px; font-weight:900; color:#0f0f1a;
    font-family:'Space Grotesk',sans-serif; flex-shrink:0;
  }
  .prajna-brand { font-size:17px; font-weight:700; color:#e2e8f0; letter-spacing:-0.3px; }
  .prajna-topbar-links { display:flex; align-items:center; gap:8px; }
  .prajna-nav-link {
    font-size:12px; font-weight:600; padding:5px 12px; border-radius:20px;
    text-decoration:none; border:1px solid; transition:opacity .2s;
  }
  .prajna-nav-link:hover { opacity:.8; }
  .prajna-nav-student  { color:#a78bfa; background:rgba(167,139,250,.12); border-color:rgba(167,139,250,.4); }
  .prajna-nav-api      { color:#34d399; background:rgba(52,211,153,.12);  border-color:rgba(52,211,153,.4);  }

  /* ── Filter bar ── */
  .filter-bar-wrap {
    background:#131320; border-bottom:1px solid rgba(255,255,255,0.06);
    padding:10px 1.5rem; margin:0 -1.5rem 1rem -1.5rem;
  }
  .filter-bar-label {
    font-size:11px; font-weight:600; color:rgba(255,255,255,0.4);
    text-transform:uppercase; letter-spacing:.5px; margin-bottom:3px;
  }

  /* ── Stat chips (DB summary bar) ── */
  .stat-bar {
    display:flex; flex-wrap:wrap; gap:8px;
    background:#131320; padding:10px 1.5rem;
    margin:0 -1.5rem .5rem -1.5rem;
    border-bottom:1px solid rgba(255,255,255,0.05);
  }
  .stat-chip {
    background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);
    border-radius:10px; padding:7px 14px;
    display:flex; flex-direction:column; align-items:flex-start;
  }
  .stat-chip-val { font-size:18px; font-weight:800; color:white; font-family:'Space Grotesk',sans-serif; line-height:1; }
  .stat-chip-lbl { font-size:9px; font-weight:600; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:.5px; margin-top:2px; }

  /* ── Section headings ── */
  .section-divider {
    font-size:15px; font-weight:700; color:#e2e8f0; letter-spacing:-0.2px;
    border-left:3px solid #6366f1; padding-left:12px;
    margin:28px 0 14px 0; display:flex; align-items:center; gap:8px;
  }
  .section-badge {
    font-size:10px; font-weight:700; padding:2px 8px; border-radius:10px;
    background:rgba(99,102,241,.15); color:#a5b4fc;
    border:1px solid rgba(99,102,241,.3);
  }

  /* ── KPI / metric cards ── */
  div[data-testid="stMetric"] {
    background:#131320 !important;
    border:1px solid rgba(255,255,255,0.07) !important;
    border-radius:14px !important; padding:18px 20px !important;
    box-shadow:0 4px 20px rgba(0,0,0,0.25);
    transition:transform .2s,box-shadow .2s;
  }
  div[data-testid="stMetric"]:hover {
    transform:translateY(-2px);
    border-color:rgba(99,102,241,.35) !important;
    box-shadow:0 8px 28px rgba(99,102,241,.12);
  }
  div[data-testid="stMetric"] label {
    font-size:10px !important; font-weight:600 !important;
    color:rgba(255,255,255,0.4) !important;
    text-transform:uppercase !important; letter-spacing:.5px !important;
    white-space:normal !important;
  }
  div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size:26px !important; font-weight:800 !important; color:#ffffff !important;
  }
  div[data-testid="stMetricDelta"] span { font-size:11px !important; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    gap:2px; background:#131320;
    border-radius:12px; padding:4px;
    border:1px solid rgba(255,255,255,0.07);
  }
  .stTabs [data-baseweb="tab"] {
    border-radius:8px; padding:9px 16px;
    font-weight:600; font-size:13px; color:rgba(255,255,255,0.45);
    transition:all .2s;
  }
  .stTabs [data-baseweb="tab"][aria-selected="true"] {
    background:rgba(99,102,241,.18) !important;
    color:#a5b4fc !important;
    box-shadow:0 2px 8px rgba(99,102,241,.15);
    border-bottom:2px solid #6366f1 !important;
  }
  .stTabs [data-baseweb="tab-highlight"] { background:transparent !important; }

  /* ── Selectboxes / inputs ── */
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stNumberInput"] > div > div > input,
  [data-testid="stTextInput"] > div > div > input {
    border-radius:8px !important;
    border-color:rgba(255,255,255,0.1) !important;
    background:#131320 !important; color:#e2e8f0 !important;
    font-size:13px !important;
  }
  [data-testid="stSelectbox"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stTextInput"] label {
    font-size:11px !important; color:rgba(255,255,255,0.4) !important;
    text-transform:uppercase; letter-spacing:.5px;
  }

  /* ── Buttons ── */
  .stButton > button {
    border-radius:8px; font-weight:600; font-size:13px;
    border:1px solid rgba(255,255,255,0.12) !important;
    background:#131320 !important; color:#e2e8f0 !important;
    transition:all .2s;
  }
  .stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#6366f1,#8b5cf6) !important;
    border:none !important; color:white !important;
    box-shadow:0 4px 16px rgba(99,102,241,.35);
  }
  .stButton > button[kind="primary"]:hover {
    box-shadow:0 6px 24px rgba(99,102,241,.5); transform:translateY(-1px);
  }

  /* ── Expanders ── */
  .streamlit-expanderHeader { font-weight:600; font-size:13px; color:#cbd5e1; }
  details {
    background:#131320 !important;
    border:1px solid rgba(255,255,255,0.07) !important;
    border-radius:12px !important;
  }

  /* ── DataFrames ── */
  [data-testid="stDataFrame"] {
    border-radius:12px; overflow:hidden;
    border:1px solid rgba(255,255,255,0.07);
  }
  [data-testid="stDataFrame"] * { color:#e2e8f0 !important; }
  [data-testid="stDataFrame"] th {
    background:rgba(99,102,241,.12) !important;
    color:#a5b4fc !important; font-weight:700 !important;
  }
  [data-testid="stDataFrame"] td { background:rgba(255,255,255,0.02) !important; }
  [data-testid="stDataFrame"] tr:hover td { background:rgba(99,102,241,.06) !important; }

  /* ── Plotly containers ── */
  .stPlotlyChart {
    background:#131320; border-radius:14px; padding:4px;
    border:1px solid rgba(255,255,255,0.06);
  }

  /* ── Download buttons ── */
  .stDownloadButton > button {
    border-radius:8px; font-weight:500;
    border:1px solid rgba(255,255,255,0.12) !important;
    background:#131320 !important; color:#cbd5e1 !important;
  }
  .stDownloadButton > button:hover {
    border-color:rgba(99,102,241,.5) !important; color:#a5b4fc !important;
  }

  /* ── Badges ── */
  .badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; letter-spacing:.3px; }
  .badge-high     { background:rgba(16,185,129,.15); color:#6ee7b7; border:1px solid rgba(16,185,129,.3); }
  .badge-medium   { background:rgba(245,158,11,.15);  color:#fcd34d; border:1px solid rgba(245,158,11,.3);  }
  .badge-low      { background:rgba(239,68,68,.15);   color:#fca5a5; border:1px solid rgba(239,68,68,.3);   }
  .badge-spec     { background:rgba(148,163,184,.1);  color:#94a3b8; border:1px solid rgba(148,163,184,.2); }
  .badge-retained { background:rgba(16,185,129,.15);  color:#6ee7b7; border:1px solid rgba(16,185,129,.3);  }
  .badge-modified { background:rgba(245,158,11,.15);  color:#fcd34d; border:1px solid rgba(245,158,11,.3);  }
  .badge-new      { background:rgba(99,102,241,.15);  color:#a5b4fc; border:1px solid rgba(99,102,241,.3);  }
  .badge-removed  { background:rgba(239,68,68,.15);   color:#fca5a5; border:1px solid rgba(239,68,68,.3);   }

  /* ── Slider ── */
  .stSlider > div > div > div > div { background:linear-gradient(90deg,#6366f1,#a855f7) !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width:5px; height:5px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:rgba(99,102,241,.3); border-radius:3px; }
  ::-webkit-scrollbar-thumb:hover { background:rgba(99,102,241,.5); }

  /* ── Misc ── */
  .stApp, p, li, span { color:#cbd5e1; }
  h1,h2,h3,h4 { color:#f1f5f9 !important; }
  .stCaption,[data-testid="stCaptionContainer"] { color:rgba(255,255,255,.35) !important; font-size:12px; }
  [data-testid="stAlert"] { border-radius:12px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.1); }
  .stSpinner > div { border-top-color:#6366f1 !important; }

  /* ── Footer ── */
  .prajna-footer {
    background:linear-gradient(135deg,#0f0f1a,#131320);
    border-top:1px solid rgba(99,102,241,.2);
    padding:28px 1.5rem; margin:48px -1.5rem 0 -1.5rem;
  }
  .team-card {
    background:#131320; border:1px solid rgba(255,255,255,.07);
    border-radius:12px; padding:14px 18px; text-align:center;
  }
  .team-name  { font-size:14px; font-weight:700; color:#e2e8f0; }
  .team-org   { font-size:10px; color:rgba(255,255,255,.4); margin:2px 0; text-transform:uppercase; letter-spacing:.5px; }
  .team-code  { font-size:11px; color:#a5b4fc; font-weight:600; }
  .team-phone { font-size:10px; color:rgba(255,255,255,.3); }

  /* Hide Streamlit chrome ── */
  #MainMenu { visibility:hidden; }
  footer { visibility:hidden; }
  [data-testid="stToolbar"]     { display:none !important; }
  [data-testid="stDeployButton"]{ display:none !important; }
</style>
""", unsafe_allow_html=True)
```

**Step 2: Verify no syntax errors**
Run: `python3 -c "import ast; ast.parse(open('dashboard/app.py').read()); print('OK')"` from repo root
Expected: `OK`

**Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "style: rewrite streamlit CSS to match intelligence dashboard dark theme"
```

---

### Task 3: Replace hero banner with compact topbar + stat bar

**Files:**
- Modify: `dashboard/app.py:428-473`

**Current block (lines 428–473):**
```python
# Fixed PW logo top-right
st.markdown("""<div class="pw-topbar">...</div>""", unsafe_allow_html=True)
...
st.markdown("""<div class="pw-hero">...<div class="stat-grid">...</div></div>""", unsafe_allow_html=True)
```

**Step 1: Replace those two st.markdown blocks with:**

```python
# ── Compact Topbar ───────────────────────────────────────────────────────────
st.markdown("""
<div class="prajna-topbar">
  <div class="prajna-topbar-left">
    <div class="prajna-logo-circle">PW</div>
    <span class="prajna-brand">PRAJNA Intelligence</span>
  </div>
  <div class="prajna-topbar-links">
    <a class="prajna-nav-link prajna-nav-student"
       href="http://localhost:8765/student-dashboard.html" target="_blank">Student IQ ↗</a>
    <a class="prajna-nav-link prajna-nav-api"
       href="http://localhost:8765/intelligence-dashboard.html" target="_blank">Intelligence ↗</a>
  </div>
</div>
""", unsafe_allow_html=True)

# ── DB stat bar ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="stat-bar">
  <div class="stat-chip"><div class="stat-chip-val">23,119</div><div class="stat-chip-lbl">Questions</div></div>
  <div class="stat-chip"><div class="stat-chip-val">292</div><div class="stat-chip-lbl">Papers</div></div>
  <div class="stat-chip"><div class="stat-chip-val">48 yrs</div><div class="stat-chip-lbl">1978–2026</div></div>
  <div class="stat-chip"><div class="stat-chip-val">36</div><div class="stat-chip-lbl">NEET Papers</div></div>
  <div class="stat-chip"><div class="stat-chip-val">178</div><div class="stat-chip-lbl">JEE Main</div></div>
  <div class="stat-chip"><div class="stat-chip-val">78</div><div class="stat-chip-lbl">JEE Adv.</div></div>
  <div class="stat-chip"><div class="stat-chip-val">755</div><div class="stat-chip-lbl">Micro-Topics</div></div>
  <div class="stat-chip"><div class="stat-chip-val">143</div><div class="stat-chip-lbl">Chapters</div></div>
  <div class="stat-chip"><div class="stat-chip-val">82.1%</div><div class="stat-chip-lbl">Backtest</div></div>
</div>
""", unsafe_allow_html=True)
```

**Step 2: Verify parse**
Run: `python3 -c "import ast; ast.parse(open('dashboard/app.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "style: replace hero banner with compact topbar + stat chips"
```

---

### Task 4: Style the filter bar row

**Files:**
- Modify: `dashboard/app.py:475-498`

**Current (lines 475–498):**
```python
f1, f2, f3, f4, f5, f6 = st.columns([1.2, 1, 0.9, 0.9, 0.7, 0.7])
...
```

**Step 1: Wrap the filter columns in the styled filter-bar div**

Replace lines 475–498 with:

```python
# ── Filter Bar ───────────────────────────────────────────────────────────────
st.markdown('<div class="filter-bar-wrap">', unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([1.3, 1.1, 0.8, 0.8, 0.7])
with f1:
    exams = ["All"] + sorted(df["exam"].unique().tolist())
    selected_exam = st.selectbox("Exam", exams, key="gx_exam", label_visibility="visible")
with f2:
    subjects = ["All"] + sorted(df["subject"].unique().tolist())
    selected_subject = st.selectbox("Subject", subjects, key="gx_subj", label_visibility="visible")
with f3:
    target_year = st.number_input("Year", value=2026, min_value=2010, max_value=2035, key="gx_yr")
with f4:
    top_n = st.selectbox("Top K", [20, 40, 60, 80, 100], index=1, key="gx_topn")
with f5:
    pred_level = st.selectbox("Level", ["Chapter", "Micro-Topic"], key="gx_level")
st.markdown('</div>', unsafe_allow_html=True)

exam_filter = selected_exam if selected_exam != "All" else None
```

**Step 2: Verify parse**
Run: `python3 -c "import ast; ast.parse(open('dashboard/app.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "style: wrap filter bar in styled div, clean up layout"
```

---

### Task 5: Update all Plotly chart defaults

**Files:**
- Modify: `dashboard/app.py:58-76`

**Step 1: Update `PLOT_LAYOUT` and `_GRID` constants to match intelligence dashboard**

Replace lines 58–70 with:

```python
PLOT_LAYOUT = dict(
    plot_bgcolor  = "#0f0f1a",
    paper_bgcolor = "#131320",
    font = dict(family="Inter, system-ui, sans-serif", size=12, color="#8888aa"),
    margin  = dict(l=10, r=10, t=36, b=10),
    legend  = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8888aa", size=11)),
    hoverlabel = dict(bgcolor="#1e1e30", font_color="#e2e8f0", font_size=12),
)
_GRID = dict(
    gridcolor     = "rgba(255,255,255,0.05)",
    zerolinecolor = "rgba(255,255,255,0.08)",
    linecolor     = "rgba(255,255,255,0.06)",
    tickfont      = dict(color="#8888aa", size=11),
)
```

**Step 2: Verify parse**
Run: `python3 -c "import ast; ast.parse(open('dashboard/app.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "style: update plotly PLOT_LAYOUT and grid to intelligence dashboard dark palette"
```

---

### Task 6: Replace all section heading `st.markdown` dividers throughout all 8 tabs

**Files:**
- Modify: `dashboard/app.py` — all occurrences of `class="section-divider"`

**Step 1: Find all section-divider usages**
Run: `grep -n "section-divider" dashboard/app.py`

**Step 2: Replace each one to use the new format with badge support**

Old pattern:
```python
st.markdown('<div class="section-divider">📊 Some Heading</div>', unsafe_allow_html=True)
```

New pattern (adds optional badge, keeps same content):
```python
st.markdown('<div class="section-divider">📊 Some Heading <span class="section-badge">Real DB</span></div>', unsafe_allow_html=True)
```

Update the most visible ones in Tab 1 (Predictions), Tab 2 (Backtest), Tab 3 (Deep Dive). Use sed or manual edit:
```bash
# Preview what will change
grep -n "section-divider" dashboard/app.py | head -20
```

**Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "style: update section dividers with badge support across all tabs"
```

---

### Task 7: Visual verification in browser

**Step 1: Restart the Streamlit server to pick up config.toml change**
```bash
# Kill existing and restart
pkill -f "streamlit run" 2>/dev/null; sleep 1
cd /Users/aman/exam-predictor && source venv/bin/activate && streamlit run dashboard/app.py --server.port 8501 --server.headless true &
sleep 4
```

**Step 2: Check it loads**
Run: `curl -s http://localhost:8501 | grep -o "PRAJNA\|streamlit" | head -3`
Expected: Output includes `streamlit`

**Step 3: Verify in preview browser**
Navigate to `http://localhost:8501` and take screenshot. Verify:
- Background is `#0f0f1a` dark (not white/light blue)
- Compact topbar with PW logo visible at top
- Stat chip bar below topbar
- Filter bar with Exam/Subject/Year/Top K/Level inline
- Tabs have dark background with indigo active state
- No sidebar visible

**Step 4: Final commit**
```bash
git add -A
git commit -m "style: complete streamlit intelligence dashboard theme - verified in browser"
```

---

## Summary of Changes

| File | Lines Changed | What Changes |
|---|---|---|
| `.streamlit/config.toml` | All | Dark theme colors |
| `dashboard/app.py:58-70` | 13 lines | `PLOT_LAYOUT` + `_GRID` dark palette |
| `dashboard/app.py:83-426` | 343 lines | Full CSS rewrite (no duplicates, dark-only) |
| `dashboard/app.py:428-473` | 46 lines | Hero → compact topbar + stat bar |
| `dashboard/app.py:475-490` | 16 lines | Filter bar wrapped in styled div |
| All section-divider calls | ~20 occurrences | Badge-style headings |

**Nothing else changes.** All data calls, `@st.cache_data` functions, prediction logic, backtest code, PDF generator, chatbot, tab structure — identical.
