// ─────────────────────────────────────────────────────────────
// PRAJNA Presentation Deck — 10 Slides (v2 — QA fixes applied)
// Built with pptxgenjs
// ─────────────────────────────────────────────────────────────
const pptxgen = require("pptxgenjs");
const path    = require("path");

const pres    = new pptxgen();
pres.layout   = "LAYOUT_16x9";   // 10" × 5.625"
pres.title    = "PRAJNA — AI-Powered Exam Intelligence";
pres.author   = "Prajna Team";

// ── Colour palette (NO # prefix — pptxgenjs corrupts file with #) ──
const C = {
  bg:      "0F0F1A",
  sf:      "161628",
  sf2:     "1E1E35",
  bd:      "2A2A48",
  purple:  "7C3AED",
  purpleL: "A855F7",
  cyan:    "06B6D4",
  green:   "22C55E",
  amber:   "F59E0B",
  red:     "EF4444",
  txt:     "E2E8F0",
  muted:   "94A3B8",
  white:   "FFFFFF",
  codeBg:  "0D1117",
};

// ── Shadow factory (MUST be a fresh object each call — pptxgenjs mutates in-place) ──
const mkShadow   = () => ({ type: "outer", color: "000000", blur: 12, offset: 4, angle: 135, opacity: 0.25 });
const mkShadowSm = () => ({ type: "outer", color: "000000", blur:  6, offset: 2, angle: 135, opacity: 0.15 });

// ── Reusable helpers ──────────────────────────────────────────
function accentBar(s, x, y, h, color) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.06, h, fill: { color }, line: { color, width: 0 } });
}
function topStrip(s, x, y, w, color) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.07, fill: { color }, line: { color, width: 0 } });
}
function bullets(items) {
  return items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1, paraSpaceAfter: 3 } }));
}

// ─────────────────────────────────────────────────────────────
// SLIDE 1 — TITLE COVER
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Decorative glow blobs (moved so they don't overlap text)
  s.addShape(pres.shapes.OVAL, {
    x: -1.2, y: -0.8, w: 5, h: 5,
    fill: { color: C.purple, transparency: 88 }, line: { color: C.purple, width: 0 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 7.8, y: 2.0, w: 3.5, h: 3.5,
    fill: { color: C.cyan, transparency: 92 }, line: { color: C.cyan, width: 0 },
  });

  // Left vertical accent bar (clear of slide edge)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.35, w: 0.07, h: 2.8,
    fill: { color: C.purple }, line: { color: C.purple, width: 0 },
  });

  // PRAJNA wordmark
  s.addText("PRAJNA", {
    x: 0.85, y: 1.25, w: 8, h: 1.35,
    fontSize: 76, fontFace: "Arial Black", bold: true,
    color: C.purpleL, align: "left", margin: 0,
  });

  // Full name subtitle
  s.addText("Personalized Revision & Academic Journey Navigation Assistant", {
    x: 0.85, y: 2.65, w: 7.2, h: 0.5,
    fontSize: 14, fontFace: "Calibri", italic: true, color: C.cyan, align: "left", margin: 0,
  });

  // Tagline
  s.addText("AI-Powered Exam Intelligence for NEET · JEE Main · JEE Advanced", {
    x: 0.85, y: 3.22, w: 7.2, h: 0.38,
    fontSize: 13, fontFace: "Calibri", color: C.muted, align: "left", margin: 0,
  });

  // Badge chips — with enough gap above footer
  const badges = ["40 Years of PYQs", "8,000+ Questions", "SLM + RAG Intelligence"];
  badges.forEach((b, i) => {
    const bx = 0.85 + i * 2.75;
    s.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 3.78, w: 2.55, h: 0.36,
      fill: { color: C.sf2 }, line: { color: C.bd, width: 1 },
    });
    s.addText(b, {
      x: bx, y: 3.78, w: 2.55, h: 0.36,
      fontSize: 10.5, fontFace: "Calibri", color: C.muted, align: "center", valign: "middle", margin: 0,
    });
  });

  // Footer bar (with breathing room above badges)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.22, w: 10, h: 0.405,
    fill: { color: C.purple, transparency: 85 }, line: { color: C.purple, width: 0 },
  });
  s.addText("v2.0  ·  2026  ·  Open-weight models  ·  Zero ongoing API cost", {
    x: 0, y: 5.22, w: 10, h: 0.405,
    fontSize: 10, fontFace: "Calibri", color: C.muted, align: "center", valign: "middle", margin: 0,
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 2 — THE PROBLEM
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("The Challenge Every Aspirant Faces", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // Stat cards — evenly spaced with right margin (FIX: step 3.05, w 2.82, start 0.48)
  const stats = [
    ["18M+",  "Students appear annually\nfor ~90,000 NEET seats",    C.red    ],
    ["40 yrs","Of exam papers rarely\nanalysed systematically",       C.amber  ],
    ["59+",   "Chapters per student\nno clear priority framework",    C.purpleL],
  ];
  stats.forEach(([val, lbl, color], i) => {
    const x = 0.48 + i * 3.05;   // last card ends at 0.48+6.10+2.82 = 9.40 ✅
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 0.96, w: 2.82, h: 1.7, fill: { color: C.sf2 }, line: { color, width: 2 }, shadow: mkShadow(),
    });
    topStrip(s, x, 0.96, 2.82, color);
    s.addText(val, {
      x, y: 1.08, w: 2.82, h: 0.9, fontSize: 46, fontFace: "Arial Black", bold: true,
      color, align: "center", valign: "middle", margin: 0,
    });
    s.addText(lbl, {
      x, y: 2.0, w: 2.82, h: 0.58, fontSize: 11, fontFace: "Calibri", color: C.muted, align: "center", valign: "middle",
    });
  });

  // Pain-point card — height trimmed to avoid excess empty space (FIX: h 2.18)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.48, y: 2.88, w: 9.04, h: 2.18, fill: { color: C.sf }, line: { color: C.bd, width: 1 }, shadow: mkShadowSm(),
  });
  accentBar(s, 0.48, 2.88, 2.18, C.purpleL);

  s.addText("What's Missing Today", {
    x: 0.68, y: 2.96, w: 8.7, h: 0.34,
    fontSize: 13, fontFace: "Calibri", bold: true, color: C.purpleL, align: "left", margin: 0,
  });

  const pains = [
    "Students study from intuition — missing high-probability topics that repeat cyclically in PYQs",
    "No visibility into which chapters need 6h of focus vs. 30 min quick revision",
    "40 years of PYQs contain clear patterns — but they're locked in scanned PDFs",
    "Teachers cannot deliver personalised guidance across hundreds of students simultaneously",
  ];
  s.addText(bullets(pains), {
    x: 0.72, y: 3.34, w: 8.62, h: 1.6,
    fontSize: 12.5, fontFace: "Calibri", color: C.txt, align: "left", valign: "top",
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 3 — SYSTEM ARCHITECTURE
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("System Architecture", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // Pipeline — FIX: reduced boxW and gap so last box stays within slide
  const boxW = 1.56, gap = 0.3, startX = 0.33, boxY = 1.12;
  // last box x = startX + 4*(boxW+gap) = 0.33 + 4*1.86 = 7.77; ends at 7.77+1.56 = 9.33 ✅
  const boxes = [
    { label: "PDF\nPapers",          sub: "40 yrs · 3 exams",         color: C.amber   },
    { label: "Claude AI\nExtract",   sub: "One-time structured\nJSON", color: C.purple  },
    { label: "SQLite\nDatabase",     sub: "8,000+ questions\nindexed", color: C.cyan    },
    { label: "Prajna\nIntelligence", sub: "SLM + RAG\n+ Predictions",  color: C.purpleL },
    { label: "Dashboards\n& API",    sub: "Students · Teachers",       color: C.green   },
  ];
  const boxH = 1.5;
  boxes.forEach(({ label, sub, color }, i) => {
    const x = startX + i * (boxW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: boxY, w: boxW, h: boxH, fill: { color: C.sf2 }, line: { color, width: 2 }, shadow: mkShadow(),
    });
    topStrip(s, x, boxY, boxW, color);
    s.addText(label, { x, y: boxY + 0.12, w: boxW, h: 0.7, fontSize: 11, fontFace: "Calibri", bold: true, color, align: "center", valign: "middle" });
    s.addText(sub,   { x, y: boxY + 0.86, w: boxW, h: 0.56, fontSize: 9, fontFace: "Calibri", color: C.muted, align: "center", valign: "top" });
    if (i < boxes.length - 1) {
      const ax = x + boxW + 0.04;
      s.addShape(pres.shapes.LINE, { x: ax, y: boxY + boxH / 2, w: gap - 0.08, h: 0, line: { color: C.bd, width: 1.5 } });
      s.addText("›", { x: ax + gap - 0.24, y: boxY + boxH / 2 - 0.22, w: 0.22, h: 0.44, fontSize: 18, color: C.muted, align: "center", margin: 0 });
    }
  });

  // Principle cards — FIX: h 2.12 so bottom margin ≥ 0.4"  (3.08 + 2.12 = 5.20; margin = 0.425")
  const principles = [
    { title: "One-time cost",  body: "Claude extracts questions once. All analysis runs fully offline — no recurring API costs." },
    { title: "Offline-first",  body: "SQLite + Python run on any local machine. No cloud dependency after extraction." },
    { title: "SLM-powered",    body: "Open-weight models (Ollama / HuggingFace) generate RAG-grounded insights locally." },
    { title: "Multi-exam",     body: "JEE Main, JEE Advanced, and NEET share one unified pipeline, DB schema, and API." },
  ];
  principles.forEach(({ title, body }, i) => {
    const x = 0.33 + i * 2.35;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.08, w: 2.22, h: 2.12, fill: { color: C.sf }, line: { color: C.bd, width: 1 }, shadow: mkShadowSm(),
    });
    accentBar(s, x, 3.08, 2.12, C.purpleL);
    s.addText(title, { x: x + 0.14, y: 3.16, w: 2.0, h: 0.35, fontSize: 12, fontFace: "Calibri", bold: true, color: C.purpleL, align: "left", margin: 0 });
    s.addText(body,  { x: x + 0.14, y: 3.55, w: 2.0, h: 1.55, fontSize: 11, fontFace: "Calibri", color: C.txt, align: "left", valign: "top" });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 4 — DATA LAYER
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("40 Years of Question Intelligence", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  const exams = [
    { name: "NEET / AIPMT", range: "1988–2025 · 37 years", qs: "~3,200 Qs", subjects: "Biology  ·  Chemistry  ·  Physics", color: C.green },
    { name: "JEE Main",     range: "2002–2025 · 23 years", qs: "~2,800 Qs", subjects: "Mathematics  ·  Chemistry  ·  Physics", color: C.cyan  },
    { name: "JEE Advanced", range: "1985–2025 · 40 years", qs: "~2,100 Qs", subjects: "Mathematics  ·  Chemistry  ·  Physics", color: C.amber },
  ];
  exams.forEach(({ name, range, qs, subjects, color }, i) => {
    const x = 0.42 + i * 3.08;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 0.96, w: 2.9, h: 2.1, fill: { color: C.sf }, line: { color, width: 1.5 }, shadow: mkShadow(),
    });
    topStrip(s, x, 0.96, 2.9, color);
    s.addText(name,     { x: x + 0.14, y: 1.08, w: 2.65, h: 0.4,  fontSize: 14, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(range,    { x: x + 0.14, y: 1.5,  w: 2.65, h: 0.28, fontSize: 10, fontFace: "Calibri", color: C.muted, align: "left", margin: 0 });
    s.addText(qs,       { x: x + 0.14, y: 1.78, w: 2.65, h: 0.5,  fontSize: 24, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0 });
    s.addText(subjects, { x: x + 0.14, y: 2.3,  w: 2.65, h: 0.65, fontSize: 10, fontFace: "Calibri", color: C.muted, align: "left", margin: 0 });
  });

  // JSON code block — FIX: h reduced so bottom margin ≥ 0.4" (3.22+1.95=5.17; margin 0.455")
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.42, y: 3.22, w: 4.55, h: 1.95, fill: { color: C.codeBg }, line: { color: C.bd, width: 1 }, shadow: mkShadowSm(),
  });
  s.addText("Structured Question Schema (per-question extraction)", {
    x: 0.57, y: 3.3, w: 4.25, h: 0.28, fontSize: 9.5, fontFace: "Calibri", bold: true, color: C.muted, align: "left", margin: 0,
  });
  s.addText(
    '{ "exam": "NEET",  "year": 2024,\n  "subject": "Chemistry",\n  "topic": "Electrochemistry",\n  "micro_topic": "Nernst Equation",\n  "difficulty": 3,  "marks": 4 }',
    { x: 0.57, y: 3.62, w: 4.25, h: 1.45, fontSize: 9.5, fontFace: "Consolas", color: C.green, align: "left", valign: "top" }
  );

  // Stat rows — FIX: y positions adjusted to stay within slide
  const rightStats = [
    ["8,000+",    "Total questions indexed",                 C.purpleL],
    ["4 signals", "Per question for ML difficulty model",    C.amber  ],
    ["100% offline","After one-time Claude extraction",      C.green  ],
    ["3 tables",  "questions · topics · patterns (SQLite)",  C.cyan   ],
  ];
  rightStats.forEach(([val, lbl, color], i) => {
    const y = 3.22 + i * 0.48;   // last row ends at 3.22+3*0.48+0.4 = 5.06 ✅
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.18, y, w: 4.4, h: 0.4, fill: { color: C.sf }, line: { color: C.bd, width: 1 },
    });
    accentBar(s, 5.18, y, 0.4, color);
    s.addText(val, { x: 5.32, y, w: 1.5,  h: 0.4, fontSize: 15, fontFace: "Arial Black", bold: true, color, align: "left", valign: "middle", margin: 0 });
    s.addText(lbl, { x: 6.82, y, w: 2.65, h: 0.4, fontSize: 10.5, fontFace: "Calibri", color: C.muted, align: "left", valign: "middle" });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 5 — PREDICTION ENGINE
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("The Prajna Prediction Engine", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // FIX v2: shortened variable names so both lines fit without soft-wrapping to a 3rd line
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 0.95, w: 9.1, h: 1.0, fill: { color: C.codeBg }, line: { color: C.purple, width: 1.5 }, shadow: mkShadow(),
  });
  s.addText(
    [
      { text: "score  =  (w_trend × freq)  +  (w_cycle × cycle_match)", options: { breakLine: true } },
      { text: "       +  (w_gap × years_since_last)  +  (w_cross × other_exam)" },
    ],
    { x: 0.62, y: 0.99, w: 8.82, h: 0.93, fontSize: 13, fontFace: "Consolas", color: C.txt, align: "left", valign: "middle" }
  );

  // Four factor cards
  const factors = [
    { label: "Trend Analyzer",    body: "Topic frequency over time. Autocorrelation detects repeating cycles. Hot/cold identification.",  color: C.cyan,    icon: "📈" },
    { label: "Cycle Detector",    body: "Topics recurring every 3–5 years flagged with high cycle weight via time-series analysis.",       color: C.purpleL, icon: "🔄" },
    { label: "Gap Scorer",        body: "Topics absent many years gain weight. 'Due to appear' heuristic from historical absence data.",   color: C.amber,   icon: "⏱" },
    { label: "Cross-Exam Signal", body: "Topics appearing in both JEE and NEET weighted higher. Inter-exam correlation boosts confidence.",color: C.green,   icon: "🔗" },
  ];
  factors.forEach(({ label, body, color, icon }, i) => {
    const x = 0.4 + i * 2.34;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.1, w: 2.2, h: 1.98, fill: { color: C.sf }, line: { color, width: 1 }, shadow: mkShadowSm(),
    });
    topStrip(s, x, 2.1, 2.2, color);
    s.addText(icon + "  " + label, { x: x + 0.1, y: 2.2,  w: 2.02, h: 0.42, fontSize: 12, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(body,               { x: x + 0.1, y: 2.65, w: 2.02, h: 1.35, fontSize: 11, fontFace: "Calibri", color: C.txt, align: "left", valign: "top" });
  });

  // Bottom row — FIX: priority box narrower (4.7"), urgency tiles start at 5.55"
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.25, w: 4.82, h: 1.08, fill: { color: C.sf2 }, line: { color: C.bd, width: 1 },
  });
  accentBar(s, 0.4, 4.25, 1.08, C.purpleL);
  s.addText("Student Priority Score:", {
    x: 0.56, y: 4.33, w: 4.6, h: 0.28, fontSize: 10, fontFace: "Calibri", bold: true, color: C.muted, align: "left", margin: 0,
  });
  s.addText("priority  =  (100 − accuracy)  ×  (slm_importance ÷ 100)", {
    x: 0.56, y: 4.62, w: 4.6, h: 0.6, fontSize: 12, fontFace: "Consolas", color: C.purpleL, align: "left", margin: 0,
  });

  // Urgency tier boxes — 4 × 1.05" = 4.2" starting at 5.55" → ends at 9.75" ✅
  const tiers = [
    { label: "Critical", color: C.red    },
    { label: "High",     color: C.amber  },
    { label: "Medium",   color: "6366F1" },
    { label: "Low",      color: C.muted  },
  ];
  tiers.forEach(({ label, color }, i) => {
    const x = 5.55 + i * 1.06;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.25, w: 0.98, h: 1.08, fill: { color: C.sf }, line: { color, width: 1.5 },
    });
    s.addText(label, { x, y: 4.25, w: 0.98, h: 1.08, fontSize: 11, fontFace: "Calibri", bold: true, color, align: "center", valign: "middle" });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 6 — SLM INTELLIGENCE LAYER
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("The Prajna SLM Intelligence Layer", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // FIX: reduced to 3 bullets per layer card + smaller font to prevent overflow
  const layers = [
    {
      label: "API Layer",          sub: "FastAPI · 4 Routers",
      items: ["GET /predictions/rank-all — global topic ranking", "POST /copilot/ask — conversational NL interface", "POST /reports/revision-plan — full study plan"],
      color: C.cyan,    y: 0.9,
    },
    {
      label: "Intelligence Layer", sub: "SLM + RAG Engine",
      items: ["Ollama (Mistral 7B, Phi-3 — runs locally)", "HuggingFace (MPS/CUDA device support)", "ChromaDB vector store for PYQ evidence retrieval"],
      color: C.purpleL, y: 2.35,
    },
    {
      label: "Data Layer",         sub: "Storage & Embeddings",
      items: ["SQLite — 8,000+ structured questions", "PyTorch .pt embedding files per exam", "Metadata-filtered RAG retrieval pipeline"],
      color: C.amber,   y: 3.8,
    },
  ];
  layers.forEach(({ label, sub, items, color, y }) => {
    const h = 1.33;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y, w: 4.55, h, fill: { color: C.sf }, line: { color, width: 1.5 }, shadow: mkShadow(),
    });
    accentBar(s, 0.4, y, h, color);
    s.addText(label, { x: 0.6, y: y + 0.1,  w: 4.22, h: 0.36, fontSize: 14, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(sub,   { x: 0.6, y: y + 0.43, w: 4.22, h: 0.24, fontSize: 10, fontFace: "Calibri", color: C.muted, align: "left", margin: 0 });
    s.addText(bullets(items), {
      x: 0.62, y: y + 0.68, w: 4.2, h: h - 0.72,
      fontSize: 9.5, fontFace: "Calibri", color: C.txt, align: "left", valign: "top",
    });
  });

  // Right column capability cards
  const rightCards = [
    {
      title: "Anti-Hallucination Guards",
      body: "All SLM outputs grounded in retrieved PYQ evidence. Confidence scores gated by source quality. Automatic fallback to pure prediction when RAG quality is low.",
      color: C.red, y: 0.9,
    },
    {
      title: "4-Stage Evaluation Pipeline",
      body: "Grounding accuracy ≥ 85%  ·  Factual consistency ≥ 75%\nRanking quality (Kendall τ) ≥ 0.70  ·  P95 latency ≤ 3,000ms\nFallback rate ≤ 10%  ·  Insight usefulness ≥ 80%",
      color: C.green, y: 2.35,
    },
    {
      title: "Zero-Code Provider Switching",
      body: "Single abstraction layer switches between Ollama, HuggingFace (MPS/CUDA), and OpenAI. Zero code changes — swap via .env. Mock provider for CI.",
      color: C.amber, y: 3.8,
    },
  ];
  rightCards.forEach(({ title, body, color, y }) => {
    const h = 1.33;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.15, y, w: 4.5, h, fill: { color: C.sf2 }, line: { color, width: 1 }, shadow: mkShadowSm(),
    });
    accentBar(s, 5.15, y, h, color);
    s.addText(title, { x: 5.3, y: y + 0.1, w: 4.22, h: 0.33, fontSize: 12, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(body,  { x: 5.3, y: y + 0.46, w: 4.22, h: h - 0.52, fontSize: 10.5, fontFace: "Calibri", color: C.txt, align: "left", valign: "top" });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 7 — STUDENT INTELLIGENCE DASHBOARD
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("Student Intelligence Dashboard", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });
  // FIX: subtitle with larger font + slightly higher contrast colour
  s.addText("A per-student window into performance, prediction alignment, and AI-guided revision — client-side, zero backend cost.", {
    x: 0.5, y: 0.84, w: 9, h: 0.3,
    fontSize: 12, fontFace: "Calibri", italic: true, color: "6E82A0", align: "left", margin: 0,
  });

  // 2×3 feature grid — FIX chapter perf text to avoid comma wrap
  const features = [
    { icon: "🏆", title: "Hero Performance Card",  body: "Latest score, rank, improvement %, consistency score — all at a glance with trajectory context.",                                               color: C.amber   },
    { icon: "📈", title: "Score Trajectory",       body: "Line chart across 10 mock exams. Per-exam trend line. Multi-subject accuracy overlay on one canvas.",                                           color: C.cyan    },
    { icon: "📊", title: "Chapter Performance",    body: "59 chapters grouped by subject. Sorted weakest-first with level badges M / S / D / W / C for each chapter.",                                   color: C.purpleL },
    { icon: "🎯", title: "Priority Focus Areas",   body: "Top 5 Prajna-ranked chapters: high gap AND high exam-appearance probability. Sorted by priority score.",                                        color: C.red     },
    { icon: "⚡", title: "Live Intelligence Feed", body: "Real-time top-18 ranked topic predictions from the Intelligence API. Student weak-zone matches highlighted with ★.",                            color: C.green   },
    { icon: "🤖", title: "Student Copilot",        body: "NL Q&A grounded in the student's actual performance data. Multi-turn memory with pre-seeded question suggestions.",                            color: C.cyan    },
  ];
  features.forEach(({ icon, title, body, color }, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.42 + col * 3.07, y = 1.28 + row * 2.1;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.9, h: 2.0, fill: { color: C.sf }, line: { color, width: 1 }, shadow: mkShadowSm(),
    });
    topStrip(s, x, y, 2.9, color);
    s.addText(icon + "  " + title, { x: x + 0.12, y: y + 0.12, w: 2.68, h: 0.44, fontSize: 12, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(body,               { x: x + 0.12, y: y + 0.60, w: 2.68, h: 1.3,  fontSize: 11, fontFace: "Calibri", color: C.txt, align: "left", valign: "top" });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 8 — PRAJNA STUDY GUIDE
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("Prajna-Powered Subject-Wise Study Guide", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 25, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });
  s.addText("Interactive advisor for ALL chapters — not just top 5. Tells students what to study, how long, in what order, and why.", {
    x: 0.5, y: 0.84, w: 9, h: 0.3,
    fontSize: 12, fontFace: "Calibri", italic: true, color: "6E82A0", align: "left", margin: 0,
  });

  // FIX: cap indentation at 0.22" per level (was 0.3") so deepest card stays readable
  const levels = [
    { label: "Subject Panel",       sub: "Sorted by urgency (avg priority score desc)",               color: C.red,     indent: 0    },
    { label: "Chapter Row",         sub: "Ranked #1, #2… · dual bars: accuracy + importance",        color: C.amber,   indent: 0.22 },
    { label: "Chapter Detail Card", sub: "Study hours · Trend arrow · Gap to next mastery level",    color: C.purpleL, indent: 0.44 },
    { label: "Micro-Topic Chips",   sub: "Lazy API fetch per chapter · cached in Map · top 3 topics",color: C.cyan,    indent: 0.66 },
    { label: "Revision Strategy",   sub: "5 levels × 3 trend directions = 13 unique templates",      color: C.green,   indent: 0.88 },
  ];
  levels.forEach(({ label, sub, color, indent }, i) => {
    const x = 0.4 + indent, w = 4.3 - indent, y = 1.22 + i * 0.76;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h: 0.67, fill: { color: C.sf }, line: { color, width: 1.5 }, shadow: mkShadowSm(),
    });
    accentBar(s, x, y, 0.67, color);
    s.addText(label, { x: x + 0.12, y,        w: w - 0.15, h: 0.32, fontSize: 11.5, fontFace: "Calibri", bold: true, color, align: "left", valign: "middle", margin: 0 });
    s.addText(sub,   { x: x + 0.12, y: y+0.34, w: w - 0.15, h: 0.28, fontSize: 9.5,  fontFace: "Calibri", color: C.muted, align: "left", valign: "middle", margin: 0 });
  });

  // Right formula cards
  const rightItems = [
    { label: "Priority Score Formula", val: "priority  =  (100 − acc)  ×  (slmImp ÷ 100)",                      color: C.purpleL, isCode: true  },
    { label: "Study Hours by Level",   val: "C → 6h   W → 4h   D → 2.5h   S → 1h   M → 0.5h",                  color: C.amber,   isCode: true  },
    { label: "Urgency Thresholds",     val: "Urgent > 35  ·  Moderate 20–35  ·  On Track < 20",                  color: C.red,     isCode: false },
    { label: "Lazy Loading + Cache",   val: "Micro-topics fetched only on chapter expand. Map prevents duplicate API calls.", color: C.cyan, isCode: false },
    { label: "Next Level Gap",         val: "gap = pctLevel() boundary − accuracy (C→25, W→45, D→65, S→80)",     color: C.green,   isCode: false },
  ];
  rightItems.forEach(({ label, val, color, isCode }, i) => {
    const y = 1.22 + i * 0.8;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.95, y, w: 4.7, h: 0.7, fill: { color: C.sf2 }, line: { color, width: 1 },
    });
    accentBar(s, 4.95, y, 0.7, color);
    s.addText(label, { x: 5.08, y: y + 0.06, w: 4.48, h: 0.26, fontSize: 10,   fontFace: "Calibri",                  bold: true, color, align: "left", margin: 0 });
    s.addText(val,   { x: 5.08, y: y + 0.34, w: 4.48, h: 0.3,  fontSize: 10,   fontFace: isCode ? "Consolas" : "Calibri", color: C.txt, align: "left", valign: "top", margin: 0 });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 9 — 4-PHASE ROADMAP
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("Development Roadmap", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // FIX: circles moved up to y:1.22 (was 1.55) to reduce gap after title; cards at y:2.32
  s.addShape(pres.shapes.LINE, {
    x: 0.88, y: 1.73, w: 8.3, h: 0, line: { color: C.bd, width: 1.5 },
  });

  const phases = [
    {
      num: "01", title: "MVP API",             sub: "3–5 days  ·  ✅ Complete", color: C.green,
      items: ["Prediction + ranking API (no SLM)", "FastAPI with 4 core routers", "Priority scoring + urgency tiers", "Topic cluster detection engine"],
    },
    {
      num: "02", title: "SLM Insights",        sub: "1–2 wks  ·  ✅ Complete",  color: C.cyan,
      items: ["Open-weight SLM (Ollama / HF)", "RAG with ChromaDB vector store", "Anti-hallucination prompt guards", "Revision plan + trend endpoints"],
    },
    {
      num: "03", title: "Copilot & Dashboard", sub: "1–2 wks  ·  🔵 Active",   color: C.purpleL,
      items: ["Multi-turn conversational copilot", "Student-personalised recommendations", "Subject-wise interactive guide", "Teacher class-level intelligence"],
    },
    {
      num: "04", title: "Eval & CI",           sub: "2–3 wks  ·  Planned",     color: C.amber,
      items: ["Grounding accuracy ≥ 85%", "A/B prompt testing harness", "Feedback (thumbs up/down)", "Auto-regression in CI pipeline"],
    },
  ];

  phases.forEach(({ num, title, sub, color, items }, i) => {
    const x = 0.38 + i * 2.35;

    // Number circle on timeline
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.48, y: 1.27, w: 0.93, h: 0.93, fill: { color }, line: { color, width: 0 },
    });
    s.addText(num, {
      x: x + 0.48, y: 1.27, w: 0.93, h: 0.93, fontSize: 18, fontFace: "Arial Black", bold: true,
      color: C.bg, align: "center", valign: "middle", margin: 0,
    });

    // Phase card — FIX: y:2.32, h:2.9 → ends at 5.22; margin 0.405" ✅
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.32, w: 2.2, h: 2.9, fill: { color: C.sf }, line: { color, width: 1.5 }, shadow: mkShadow(),
    });
    topStrip(s, x, 2.32, 2.2, color);
    s.addText(title, { x: x + 0.12, y: 2.42, w: 2.0, h: 0.42, fontSize: 14, fontFace: "Calibri", bold: true, color, align: "left", margin: 0 });
    s.addText(sub,   { x: x + 0.12, y: 2.85, w: 2.0, h: 0.26, fontSize: 9,  fontFace: "Calibri", color: C.muted, align: "left", margin: 0 });
    s.addText(bullets(items), {
      x: x + 0.12, y: 3.16, w: 2.0, h: 1.93, fontSize: 10, fontFace: "Calibri", color: C.txt, align: "left", valign: "top",
    });
  });
}

// ─────────────────────────────────────────────────────────────
// SLIDE 10 — TECH STACK & MISSION
// ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // FIX v2: circle removed entirely — kept overlapping Cost column; clean table looks better

  s.addText("Built on a Zero-Cost Stack", {
    x: 0.5, y: 0.28, w: 9, h: 0.52,
    fontSize: 28, fontFace: "Arial Black", bold: true, color: C.txt, align: "left", margin: 0,
  });

  // Table — columns fit within 9.6" to ensure right margin
  const colX = [0.42, 3.35, 6.28], colW = [2.75, 2.75, 1.38];

  // Header row
  ["Component", "Tool / Framework", "Cost"].forEach((h, i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: colX[i], y: 0.95, w: colW[i] - 0.04, h: 0.4, fill: { color: C.purple }, line: { color: C.purple, width: 0 },
    });
    s.addText(h, { x: colX[i] + 0.1, y: 0.95, w: colW[i] - 0.14, h: 0.4, fontSize: 11, fontFace: "Calibri", bold: true, color: C.white, align: "left", valign: "middle", margin: 0 });
  });

  const tech = [
    ["Data Extraction",   "Claude AI (one-time)",         "Free tier"   ],
    ["Database",          "SQLite",                        "Free"        ],
    ["ML Classifier",     "Scikit-learn + PyTorch",        "Free"        ],
    ["Embeddings",        "Sentence Transformers",          "Free"        ],
    ["SLM Inference",     "Ollama (Mistral 7B, Phi-3)",    "Free (local)"],
    ["Vector Store",      "ChromaDB",                      "Free"        ],
    ["API Server",        "FastAPI + Uvicorn",             "Free"        ],
    ["Dashboards",        "Streamlit + HTML / JS",          "Free"        ],
  ];
  tech.forEach(([component, tool, cost], i) => {
    const y = 1.38 + i * 0.348;
    const bg = i % 2 === 0 ? C.sf : C.sf2;
    colX.forEach((x, ci) => {
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: colW[ci] - 0.04, h: 0.32, fill: { color: bg }, line: { color: C.bd, width: 0.5 } });
    });
    [[component, C.txt], [tool, C.purpleL], [cost, C.green]].forEach(([cell, color], ci) => {
      s.addText(cell, { x: colX[ci] + 0.1, y, w: colW[ci] - 0.14, h: 0.32, fontSize: 10.5, fontFace: "Calibri", color, align: "left", valign: "middle", margin: 0 });
    });
  });

  // Mission statement — FIX: more top/bottom margin (y:4.42, leaves 0.44" below at 5.625)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.42, y: 4.42, w: 9.16, h: 0.95, fill: { color: C.sf2 }, line: { color: C.purple, width: 1.5 }, shadow: mkShadow(),
  });
  accentBar(s, 0.42, 4.42, 0.95, C.purpleL);
  s.addText(
    "PRAJNA's mission: democratize exam intelligence. Every student — regardless of coaching budget — deserves the same data-driven edge previously available only to the most well-resourced.",
    { x: 0.62, y: 4.48, w: 8.82, h: 0.82, fontSize: 12.5, fontFace: "Calibri", italic: true, color: C.txt, align: "left", valign: "middle" }
  );
}

// ─────────────────────────────────────────────────────────────
// OUTPUT
// ─────────────────────────────────────────────────────────────
const outPath = path.resolve("/Users/aman/exam-predictor/docs/prajna-deck/prajna-deck.pptx");
pres.writeFile({ fileName: outPath })
  .then(() => console.log("✅  Deck saved →", outPath))
  .catch(err => { console.error("❌  Error:", err); process.exit(1); });
