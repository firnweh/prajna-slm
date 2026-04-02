'use strict';
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');

// ─── react-icons ─────────────────────────────────────────────────────────────
const { FaDatabase, FaBrain, FaServer, FaCode, FaChartBar, FaRocket,
        FaLayerGroup, FaSearch, FaShieldAlt, FaCogs } = require('react-icons/fa');

async function iconPng(Icon, color = '#FFFFFF', size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

// ─── Palette ──────────────────────────────────────────────────────────────────
const C = {
  bg:       '0A0A1A',   // deepest dark
  navy:     '0F0F2E',   // slide bg
  surface:  '161638',   // card bg
  card:     '1C1C45',   // elevated card
  purple:   '7C3AED',   // primary brand
  purpleM:  '5B21B6',   // darker purple
  purpleLt: 'A78BFA',   // light purple
  teal:     '0891B2',   // secondary
  tealLt:   '67E8F9',   // light teal
  green:    '16A34A',
  greenLt:  '4ADE80',
  amber:    'D97706',
  amberLt:  'FCD34D',
  red:      'DC2626',
  white:    'FFFFFF',
  offWhite: 'E2E8F0',
  muted:    '64748B',
  slate:    '94A3B8',
};

// ─── Shadow factory ───────────────────────────────────────────────────────────
const mkShadow = () => ({ type: 'outer', color: '000000', blur: 12, offset: 3, angle: 135, opacity: 0.35 });
const mkShadowSm = () => ({ type: 'outer', color: '000000', blur: 6, offset: 2, angle: 135, opacity: 0.2 });

// ─── Helpers ──────────────────────────────────────────────────────────────────
function statBox(slide, x, y, w, h, num, label, accent) {
  slide.addShape('rect', { x, y, w, h, fill: { color: C.surface }, shadow: mkShadow(),
    line: { color: accent, width: 1.5 } });
  slide.addShape('rect', { x, y, w, h: 0.07, fill: { color: accent }, line: { color: accent, width: 0 } });
  slide.addText(num, { x, y: y + 0.18, w, h: 0.75, align: 'center', valign: 'middle',
    fontSize: 36, bold: true, color: C.white, fontFace: 'Calibri' });
  slide.addText(label, { x, y: y + 0.85, w, h: 0.42, align: 'center', valign: 'top',
    fontSize: 11, color: C.slate, fontFace: 'Calibri' });
}

function card(slide, x, y, w, h, accentColor) {
  slide.addShape('rect', { x, y, w, h, fill: { color: C.surface }, shadow: mkShadow(),
    line: { color: C.card, width: 1 } });
  slide.addShape('rect', { x, y, w: 0.07, h, fill: { color: accentColor }, line: { color: accentColor, width: 0 } });
}

function sectionLabel(slide, text, x, y) {
  slide.addShape('rect', { x, y, w: 1.8, h: 0.28, fill: { color: C.purple },
    line: { color: C.purple, width: 0 } });
  slide.addText(text, { x, y, w: 1.8, h: 0.28, align: 'center', valign: 'middle',
    fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 1.5 });
}

function divLine(slide, x1, y, x2) {
  slide.addShape('line', { x: x1, y, w: x2 - x1, h: 0,
    line: { color: C.purpleM, width: 0.8, dashType: 'solid' } });
}

// ─── Build ────────────────────────────────────────────────────────────────────
async function buildDeck() {
  const pres = new pptxgen();
  pres.layout  = 'LAYOUT_16x9';
  pres.title   = 'PRAJNA — Technical Architecture';
  pres.author  = 'PRAJNA Team';

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 01  Cover
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Left accent bar
    s.addShape('rect', { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: C.purple }, line: { color: C.purple, width: 0 } });

    // Diagonal decorative band
    s.addShape('rect', { x: 6.2, y: 0, w: 5, h: 5.625, fill: { color: C.navy }, line: { color: C.navy, width: 0 } });
    s.addShape('rect', { x: 5.5, y: 0, w: 0.9, h: 5.625, fill: { color: C.purpleM, transparency: 60 }, line: { color: C.purpleM, width: 0 } });

    // Grid dots decoration (right side)
    for (let r = 0; r < 5; r++) for (let c = 0; c < 8; c++) {
      s.addShape('ellipse', {
        x: 6.8 + c * 0.38, y: 0.4 + r * 0.9, w: 0.06, h: 0.06,
        fill: { color: C.purpleLt, transparency: 75 }, line: { color: C.purpleLt, width: 0 }
      });
    }

    // Logo text
    s.addText('PRAJNA', { x: 0.4, y: 1.0, w: 5, h: 1.1,
      fontSize: 72, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 8 });
    s.addText('Exam Intelligence Platform', { x: 0.4, y: 2.1, w: 5.5, h: 0.5,
      fontSize: 20, color: C.purpleLt, fontFace: 'Calibri', italics: true });

    // Divider
    s.addShape('line', { x: 0.4, y: 2.75, w: 4.8, h: 0,
      line: { color: C.purple, width: 2 } });

    s.addText('Technical Architecture Document', { x: 0.4, y: 2.95, w: 5.5, h: 0.4,
      fontSize: 15, color: C.slate, fontFace: 'Calibri' });
    s.addText('v1.0  ·  March 2026', { x: 0.4, y: 3.45, w: 5, h: 0.35,
      fontSize: 12, color: C.muted, fontFace: 'Calibri' });

    // Bottom metadata strip
    s.addShape('rect', { x: 0, y: 4.9, w: 10, h: 0.725, fill: { color: C.purpleM }, line: { color: C.purpleM, width: 0 } });
    const meta = ['NEET  ·  JEE Main  ·  JEE Advanced', '23,119 Questions  ·  2000–2025', '23 M-param SLM  ·  FastAPI  ·  RAG'];
    meta.forEach((m, i) => s.addText(m, {
      x: 0.3 + i * 3.3, y: 4.9, w: 3.2, h: 0.725,
      align: 'center', valign: 'middle', fontSize: 11, color: C.offWhite, fontFace: 'Calibri'
    }));
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 02  Platform at a Glance
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    // Header
    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.88, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.88, w: 10, h: 0.05, fill: { color: C.purple }, line: { color: C.purple, width: 0 } });
    s.addText('PLATFORM AT A GLANCE', { x: 0.4, y: 0, w: 9, h: 0.88, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });
    s.addText('Key metrics and scope', { x: 7, y: 0.25, w: 2.6, h: 0.4, align: 'right', valign: 'middle',
      fontSize: 11, color: C.slate, fontFace: 'Calibri' });

    // 6 stat boxes — row 1
    const stats1 = [
      ['23,119', 'Questions in database', C.purple],
      ['25 yrs', 'Coverage: 2000–2025', C.teal],
      ['3 exams', 'NEET · JEE Main · JEE Advanced', C.green],
    ];
    stats1.forEach(([n, l, c], i) => statBox(s, 0.3 + i * 3.22, 0.97, 3.0, 1.28, n, l, c));

    // Row 2
    const stats2 = [
      ['23 M',   'SLM Parameters (PRAJNA)', C.purple],
      ['399-dim','Input feature vector', C.teal],
      ['12',     'REST API endpoints', C.amber],
    ];
    stats2.forEach(([n, l, c], i) => statBox(s, 0.3 + i * 3.22, 2.42, 3.0, 1.28, n, l, c));

    // Row 3 — narrower quality targets
    const stats3 = [
      ['≥60%',  'Top-10 coverage', C.purpleLt],
      ['≥85%',  'Grounding accuracy', C.tealLt],
      ['≤3 s',  'API latency P95', C.amberLt],
      ['≤10%',  'Fallback rate', C.greenLt],
    ];
    stats3.forEach(([n, l, c], i) => statBox(s, 0.3 + i * 2.37, 3.92, 2.18, 1.25, n, l, c));
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 03  Three-Tier Architecture
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.teal }, line: { color: C.teal, width: 0 } });
    s.addText('THREE-TIER ARCHITECTURE', { x: 0.4, y: 0, w: 8, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Tier cards
    const tiers = [
      { x: 0.25, color: C.green,  label: 'TIER 1', title: 'Data & ML Engine',
        items: ['SQLite exam.db  (10.9 MB)', '23,119 questions', 'PRAJNA SLM  (.pt models)', 'Predictor v3  (3-stage)', 'Student CSVs  (37+ MB)'],
        tech: 'Python · PyTorch · Pandas' },
      { x: 3.55, color: C.purple, label: 'TIER 2', title: 'Intelligence Layer',
        items: ['FastAPI  :8001', 'ChromaDB  :8002  (RAG)', 'Ollama  :11434  (SLM)', 'Pydantic schemas', 'Anti-hallucination guard'],
        tech: 'FastAPI · ChromaDB · Sentence-Transformers' },
      { x: 6.85, color: C.teal,   label: 'TIER 3', title: 'Frontend',
        items: ['Streamlit  :8501', 'Static HTML dashboard', 'Chart.js · Client-side JS', 'Pre-built JSON summaries', 'Zero-server mode'],
        tech: 'Streamlit · Vanilla JS · Chart.js' },
    ];

    tiers.forEach(({ x, color, label, title, items, tech }) => {
      // Card bg
      s.addShape('rect', { x, y: 1.05, w: 3.1, h: 4.3, fill: { color: C.surface },
        shadow: mkShadow(), line: { color: color, width: 1.5 } });
      // Top accent
      s.addShape('rect', { x, y: 1.05, w: 3.1, h: 0.06, fill: { color: color }, line: { color, width: 0 } });
      // Badge
      s.addShape('rect', { x: x + 0.15, y: 1.2, w: 0.82, h: 0.25,
        fill: { color: color }, line: { color, width: 0 } });
      s.addText(label, { x: x + 0.15, y: 1.2, w: 0.82, h: 0.25, align: 'center', valign: 'middle',
        fontSize: 8, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 1 });
      // Title
      s.addText(title, { x: x + 0.18, y: 1.55, w: 2.8, h: 0.38,
        fontSize: 15, bold: true, color: C.white, fontFace: 'Calibri' });
      // Items
      s.addText(items.map(t => ({ text: t, options: { bullet: true, breakLine: true, color: C.offWhite } })),
        { x: x + 0.25, y: 2.02, w: 2.7, h: 2.1, fontSize: 11, fontFace: 'Calibri', paraSpaceAfter: 3 });
      // Tech strip
      s.addShape('rect', { x, y: 4.98, w: 3.1, h: 0.37, fill: { color: color, transparency: 75 }, line: { color, width: 0 } });
      s.addText(tech, { x: x + 0.1, y: 4.98, w: 2.9, h: 0.37, align: 'center', valign: 'middle',
        fontSize: 9, color: C.white, fontFace: 'Calibri', italics: true });
    });

    // Arrows between tiers
    [3.38, 6.68].forEach(ax => {
      s.addShape('line', { x: ax, y: 3.0, w: 0.33, h: 0, line: { color: C.slate, width: 2 } });
      s.addText('→', { x: ax + 0.12, y: 2.82, w: 0.3, h: 0.35, fontSize: 16, color: C.slate, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 04  Data Layer
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.green }, line: { color: C.green, width: 0 } });
    s.addText('DATA LAYER', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Left: SQLite schema table
    sectionLabel(s, 'SQLite SCHEMA', 0.3, 1.05);
    s.addShape('rect', { x: 0.3, y: 1.33, w: 4.55, h: 3.5, fill: { color: C.surface }, shadow: mkShadow(),
      line: { color: C.green, width: 1 } });

    const schemaRows = [
      ['id', 'TEXT PK', '"JEE_ADV_2019_P1_Q12"'],
      ['exam', 'TEXT', 'NEET | JEE Main | JEE Adv'],
      ['year', 'INTEGER', '2000 – 2025'],
      ['subject', 'TEXT', 'Physics / Chemistry / Bio / Math'],
      ['topic', 'TEXT', 'Chapter-level topic name'],
      ['micro_topic', 'TEXT', 'Specific sub-topic'],
      ['question_type', 'TEXT', 'MCQ / integer / matrix_match'],
      ['difficulty', 'INTEGER', '1 – 5 scale'],
    ];
    // Header
    s.addShape('rect', { x: 0.3, y: 1.33, w: 4.55, h: 0.3, fill: { color: C.green }, line: { color: C.green, width: 0 } });
    ['Column', 'Type', 'Notes'].forEach((h, i) => s.addText(h, {
      x: 0.3 + [0, 1.1, 2.0][i], y: 1.33, w: [1.0, 0.9, 1.9][i], h: 0.3,
      align: 'left', valign: 'middle', fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri'
    }));
    schemaRows.forEach(([col, type, note], ri) => {
      const ry = 1.63 + ri * 0.39;
      if (ri % 2 === 0) s.addShape('rect', { x: 0.3, y: ry, w: 4.55, h: 0.39,
        fill: { color: C.card }, line: { color: C.card, width: 0 } });
      [col, type, note].forEach((v, ci) => s.addText(v, {
        x: 0.3 + [0, 1.1, 2.0][ci], y: ry, w: [0.98, 0.88, 1.9][ci], h: 0.39,
        valign: 'middle', fontSize: 9, color: ci === 0 ? C.tealLt : C.offWhite, fontFace: 'Calibri'
      }));
    });

    // Right: data files + ingestion
    sectionLabel(s, 'DATA FILES', 5.15, 1.05);
    const files = [
      ['exam.db', '10.9 MB', C.green],
      ['neet_results_v2.csv', '16 MB', C.teal],
      ['jee_results_v2.csv', '21.4 MB', C.teal],
      ['students_v2.csv', '14 KB', C.amber],
      ['student_summary_*.json', '1.7 MB', C.purple],
    ];
    files.forEach(([name, size, c], i) => {
      s.addShape('rect', { x: 5.15, y: 1.33 + i * 0.56, w: 4.55, h: 0.48,
        fill: { color: C.surface }, line: { color: c, width: 1 } });
      s.addShape('rect', { x: 5.15, y: 1.33 + i * 0.56, w: 0.06, h: 0.48,
        fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(name, { x: 5.28, y: 1.33 + i * 0.56, w: 3.2, h: 0.48,
        valign: 'middle', fontSize: 10, bold: true, color: C.offWhite, fontFace: 'Calibri' });
      s.addText(size, { x: 8.45, y: 1.33 + i * 0.56, w: 1.2, h: 0.48,
        align: 'right', valign: 'middle', fontSize: 10, color: C.slate, fontFace: 'Calibri' });
    });

    // Ingestion pipeline
    sectionLabel(s, 'INGESTION PIPELINE', 5.15, 4.22);
    s.addShape('rect', { x: 5.15, y: 4.5, w: 4.55, h: 0.88, fill: { color: C.surface },
      line: { color: C.purpleM, width: 1 } });
    s.addText([
      { text: 'PDF/HTML exam papers  →  ', options: { color: C.slate } },
      { text: 'Claude extraction prompt', options: { color: C.purpleLt, bold: true } },
      { text: '  →  JSON\nJSON  →  ', options: { color: C.slate, breakLine: false } },
      { text: 'loader.py', options: { color: C.tealLt, bold: true } },
      { text: '  →  ', options: { color: C.slate } },
      { text: 'exam.db', options: { color: C.greenLt, bold: true } },
      { text: '  (deduplication on ingest)', options: { color: C.muted } },
    ], { x: 5.25, y: 4.5, w: 4.35, h: 0.88, valign: 'middle', fontSize: 10, fontFace: 'Calibri' });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 05  PRAJNA SLM Architecture
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.purple }, line: { color: C.purple, width: 0 } });
    s.addText('PRAJNA SLM — MODEL ARCHITECTURE', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Architecture flow diagram
    const blocks = [
      { x: 0.25, y: 1.12, w: 2.1, h: 0.75, bg: C.teal,    text: 'Chapter Name\n(text input)' },
      { x: 2.65, y: 1.12, w: 2.4, h: 0.75, bg: C.purpleM, text: 'all-MiniLM-L6-v2\n384-dim embedding' },
      { x: 5.35, y: 1.12, w: 2.0, h: 0.75, bg: C.green,   text: '15 Temporal\nFeatures' },
      { x: 7.6,  y: 1.12, w: 2.1, h: 0.75, bg: C.purple,  text: 'Concat  →  399d\nInput Vector' },
    ];
    blocks.forEach(({ x, y, w, h, bg, text }) => {
      s.addShape('rect', { x, y, w, h, fill: { color: bg }, shadow: mkShadowSm(),
        line: { color: bg, width: 0 } });
      s.addText(text, { x, y, w, h, align: 'center', valign: 'middle',
        fontSize: 9.5, bold: true, color: C.white, fontFace: 'Calibri' });
    });
    // Arrows
    [[2.35, 1.49], [5.05, 1.49]].forEach(([ax, ay]) =>
      s.addText('→', { x: ax, y: ay - 0.2, w: 0.3, h: 0.4, fontSize: 16, color: C.slate, fontFace: 'Calibri' }));
    s.addText('+', { x: 7.3, y: 1.29, w: 0.3, h: 0.4, fontSize: 20, bold: true, color: C.amberLt, fontFace: 'Calibri' });

    // MLP layers
    sectionLabel(s, 'MLP LAYERS', 0.25, 2.15);
    const layers = [
      { x: 0.25, label: 'Dense 256\nReLU + BN + Drop 0.2', c: C.purple },
      { x: 2.65, label: 'Dense 128\nReLU + BN + Drop 0.2', c: C.purpleM },
      { x: 5.05, label: 'Dense 64\nReLU', c: C.teal },
    ];
    layers.forEach(({ x, label, c }, i) => {
      s.addShape('rect', { x, y: 2.42, w: 2.2, h: 0.78, fill: { color: c },
        shadow: mkShadowSm(), line: { color: c, width: 0 } });
      s.addText(label, { x, y: 2.42, w: 2.2, h: 0.78, align: 'center', valign: 'middle',
        fontSize: 10, bold: true, color: C.white, fontFace: 'Calibri' });
      if (i < layers.length - 1)
        s.addText('→', { x: x + 2.25, y: 2.62, w: 0.3, h: 0.4, fontSize: 16, color: C.slate, fontFace: 'Calibri' });
    });

    // Output heads
    sectionLabel(s, 'OUTPUT HEADS', 0.25, 3.45);
    const heads = [
      { x: 0.25, bg: C.green,  label: 'Head 1 — P(appear)', desc: 'Sigmoid → probability\nchapter will appear' },
      { x: 3.45, bg: C.teal,   label: 'Head 2 — E[questions]', desc: 'Linear regression\nexpected Q count' },
      { x: 6.65, bg: C.amber,  label: 'Head 3 — Difficulty', desc: 'Softmax → 5-class\n(1 = easy … 5 = hard)' },
    ];
    heads.forEach(({ x, bg, label, desc }) => {
      s.addShape('rect', { x, y: 3.72, w: 3.0, h: 1.6, fill: { color: C.surface }, shadow: mkShadow(),
        line: { color: bg, width: 1.5 } });
      s.addShape('rect', { x, y: 3.72, w: 3.0, h: 0.06, fill: { color: bg }, line: { color: bg, width: 0 } });
      s.addText(label, { x: x + 0.15, y: 3.84, w: 2.7, h: 0.38, fontSize: 11, bold: true,
        color: C.white, fontFace: 'Calibri' });
      s.addText(desc, { x: x + 0.15, y: 4.26, w: 2.7, h: 0.9, fontSize: 10.5,
        color: C.slate, fontFace: 'Calibri' });
    });

    // Param count badge
    s.addShape('rect', { x: 7.55, y: 2.32, w: 2.1, h: 0.88, fill: { color: C.purple },
      shadow: mkShadow(), line: { color: C.purpleLt, width: 1 } });
    s.addText('23 M\nParameters', { x: 7.55, y: 2.32, w: 2.1, h: 0.88, align: 'center', valign: 'middle',
      fontSize: 18, bold: true, color: C.white, fontFace: 'Calibri' });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 06  Feature Engineering  (15 temporal features)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.teal }, line: { color: C.teal, width: 0 } });
    s.addText('FEATURE ENGINEERING  —  15 TEMPORAL FEATURES', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 22, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 2 });

    const features = [
      ['0', 'Appearance rate', 'count(years appeared) / total span', C.green],
      ['1', 'Recency-weighted freq', 'Σ 1/(year_diff^1.5 + 1)  — exp decay', C.green],
      ['2', 'Recent presence (3yr)', 'Binary: appeared in last 3 years?', C.teal],
      ['3', 'Recent presence (5yr)', 'Binary: appeared in last 5 years?', C.teal],
      ['4', 'Gap (years since last)', 'Current year − last appearance year', C.purple],
      ['5', 'Mean gap', 'Avg interval between appearances', C.purple],
      ['6', 'Trend slope', 'Linear regression coeff on last 10 years', C.amber],
      ['7', 'Mean question count', 'Avg questions per appearing year', C.teal],
      ['8', 'Std-dev question count', 'Variance in annual question counts', C.teal],
      ['9', 'Max question count', 'Historical peak in a single year', C.teal],
      ['10','Total appearances', 'Normalised by total year window', C.green],
      ['11','Cross-exam presence', '1.0 if ≥1 other exam type covers it', C.purple],
      ['12','Cycle regularity', 'Inverse CV of appearance gaps', C.amber],
      ['13','Recent yield avg', 'Mean questions in last 3 appearances', C.green],
      ['14','Subject encoding', '0.25=Phys  0.50=Chem  0.75=Bio  1.0=Math', C.red],
    ];

    // Two columns
    const COL = [0.25, 5.1];
    features.forEach(([ idx, name, desc, c ], i) => {
      const col = i < 8 ? 0 : 1;
      const row = i < 8 ? i : i - 8;
      const x = COL[col], y = 1.05 + row * 0.56;
      s.addShape('rect', { x, y, w: 4.6, h: 0.48, fill: { color: C.surface },
        shadow: mkShadowSm(), line: { color: c, width: 0.8 } });
      s.addShape('rect', { x, y, w: 0.44, h: 0.48, fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(idx, { x, y, w: 0.44, h: 0.48, align: 'center', valign: 'middle',
        fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(name, { x: x + 0.50, y, w: 1.73, h: 0.48, valign: 'middle',
        fontSize: 9, bold: true, color: C.offWhite, fontFace: 'Calibri' });
      s.addText(desc, { x: x + 2.28, y, w: 2.28, h: 0.48, valign: 'middle',
        fontSize: 8.5, color: C.slate, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 07  Prediction Pipeline  (v3 3-stage)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.amber }, line: { color: C.amber, width: 0 } });
    s.addText('PREDICTION PIPELINE  —  PREDICTOR v3', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // 3 stage pipeline
    const stages = [
      { n: '01', title: 'Stage 1\nAppearance Probability',
        items: ['Recency-weighted frequency', 'Gap-return probability', 'Trend slope (lin. regression)', 'Cycle-match score'],
        c: C.green, x: 0.25 },
      { n: '02', title: 'Stage 2\nWeightage Model',
        items: ['Expected question count', 'Historical Q-count distribution', 'Accounts for difficulty trends', 'Given chapter appears'],
        c: C.purple, x: 3.55 },
      { n: '03', title: 'Stage 3\nQuestion Format',
        items: ['Likely question types', 'MCQ single / MCQ multi', 'Integer / Numerical', 'Matrix match'],
        c: C.teal, x: 6.85 },
    ];

    stages.forEach(({ n, title, items, c, x }) => {
      s.addShape('rect', { x, y: 1.05, w: 3.1, h: 3.0, fill: { color: C.surface },
        shadow: mkShadow(), line: { color: c, width: 1.5 } });
      s.addShape('rect', { x, y: 1.05, w: 3.1, h: 0.06, fill: { color: c }, line: { color: c, width: 0 } });
      // Stage number bubble
      s.addShape('ellipse', { x: x + 0.12, y: 1.18, w: 0.55, h: 0.55, fill: { color: c },
        line: { color: c, width: 0 } });
      s.addText(n, { x: x + 0.12, y: 1.18, w: 0.55, h: 0.55, align: 'center', valign: 'middle',
        fontSize: 13, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(title, { x: x + 0.75, y: 1.18, w: 2.25, h: 0.62,
        fontSize: 11, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(items.map(t => ({ text: t, options: { bullet: true, breakLine: true, color: C.offWhite } })),
        { x: x + 0.2, y: 1.88, w: 2.75, h: 1.9, fontSize: 10.5, fontFace: 'Calibri', paraSpaceAfter: 4 });
    });

    // Post-processing
    sectionLabel(s, 'POST-PROCESSING', 0.25, 4.35);
    const ppItems = [
      ['Subject balance quotas', C.green],
      ['Unique chapter enforcement', C.teal],
      ['Diversification penalty', C.purple],
      ['Constraint-solving reranker', C.amber],
    ];
    ppItems.forEach(([txt, c], i) => {
      s.addShape('rect', { x: 0.25 + i * 2.38, y: 4.62, w: 2.2, h: 0.75, fill: { color: C.surface },
        shadow: mkShadowSm(), line: { color: c, width: 1 } });
      s.addShape('rect', { x: 0.25 + i * 2.38, y: 4.62, w: 2.2, h: 0.06,
        fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(txt, { x: 0.35 + i * 2.38, y: 4.72, w: 2.0, h: 0.6,
        valign: 'middle', fontSize: 10, color: C.offWhite, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 08  Intelligence Layer (FastAPI)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.purple }, line: { color: C.purple, width: 0 } });
    s.addText('INTELLIGENCE LAYER  —  FastAPI SERVICE', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Left: Endpoint table
    sectionLabel(s, 'REST ENDPOINTS', 0.25, 1.05);
    const endpoints = [
      ['GET',  '/predictions/rank-all',       'Global chapter ranking'],
      ['GET',  '/predictions/chapter/{name}', 'Chapter-level breakdown'],
      ['POST', '/insights/micro-topic',        'SLM micro-topic explanation'],
      ['POST', '/insights/chapter',            'Chapter intelligence + clusters'],
      ['POST', '/reports/revision-plan',       'Personalised revision plan'],
      ['POST', '/copilot/ask',                 'Natural language Q&A'],
      ['GET',  '/data/trends',                 'Trending topic briefing'],
      ['GET',  '/health',                      'Service health check'],
    ];
    // Header
    s.addShape('rect', { x: 0.25, y: 1.33, w: 5.25, h: 0.28, fill: { color: C.purple },
      line: { color: C.purple, width: 0 } });
    ['Method', 'Path', 'Purpose'].forEach((h, i) => s.addText(h, {
      x: 0.25 + [0, 0.75, 2.4][i], y: 1.33, w: [0.72, 1.6, 2.8][i], h: 0.28,
      valign: 'middle', fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri'
    }));
    endpoints.forEach(([method, path, purpose], ri) => {
      const ry = 1.61 + ri * 0.44;
      if (ri % 2 === 0) s.addShape('rect', { x: 0.25, y: ry, w: 5.25, h: 0.44,
        fill: { color: C.card }, line: { color: C.card, width: 0 } });
      const mc = method === 'GET' ? C.teal : C.amber;
      s.addShape('rect', { x: 0.25, y: ry + 0.08, w: 0.68, h: 0.28,
        fill: { color: mc, transparency: 20 }, line: { color: mc, width: 0 } });
      s.addText(method, { x: 0.25, y: ry + 0.08, w: 0.68, h: 0.28, align: 'center', valign: 'middle',
        fontSize: 8, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(path,    { x: 0.98, y: ry, w: 1.65, h: 0.44, valign: 'middle', fontSize: 8.5, color: C.tealLt, fontFace: 'Calibri' });
      s.addText(purpose, { x: 2.68, y: ry, w: 2.82, h: 0.44, valign: 'middle', fontSize: 8.5, color: C.offWhite, fontFace: 'Calibri' });
    });

    // Right: SLM Providers + services
    sectionLabel(s, 'SLM PROVIDERS', 5.75, 1.05);
    const providers = [
      ['mock',           'Zero-setup  (fixtures)',  C.slate],
      ['ollama',         'Local  mistral:7b',       C.green],
      ['huggingface',    'phi-3-mini  (local GPU)', C.teal],
      ['openai_compat',  'GPT-4o-mini / Groq / vLLM', C.purple],
    ];
    providers.forEach(([name, desc, c], i) => {
      s.addShape('rect', { x: 5.75, y: 1.33 + i * 0.54, w: 3.95, h: 0.46,
        fill: { color: C.surface }, shadow: mkShadowSm(), line: { color: c, width: 1 } });
      s.addShape('rect', { x: 5.75, y: 1.33 + i * 0.54, w: 0.06, h: 0.46,
        fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(name, { x: 5.88, y: 1.33 + i * 0.54, w: 1.5, h: 0.46, valign: 'middle',
        fontSize: 10, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(desc, { x: 7.38, y: 1.33 + i * 0.54, w: 2.3, h: 0.46, valign: 'middle',
        fontSize: 9.5, color: C.slate, fontFace: 'Calibri' });
    });

    // Service components
    sectionLabel(s, 'KEY SERVICES', 5.75, 3.55);
    const services = [
      ['TopicAggregator', 'Batch builder, priority scorer, ranker', C.teal],
      ['ClusterDetector', 'Semantic topic cluster detection', C.purple],
      ['RAGRetriever', 'Top-K chroma retrieval, metadata filter', C.green],
      ['AntiHallucGuard', 'Fact grounding + fallback trigger', C.red],
    ];
    services.forEach(([name, desc, c], i) => {
      s.addShape('rect', { x: 5.75, y: 3.83 + i * 0.44, w: 3.95, h: 0.38,
        fill: { color: C.surface }, line: { color: c, width: 0.8 } });
      s.addText(name, { x: 5.85, y: 3.83 + i * 0.44, w: 1.65, h: 0.38, valign: 'middle',
        fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(desc, { x: 7.55, y: 3.83 + i * 0.44, w: 2.1, h: 0.38, valign: 'middle',
        fontSize: 8.5, color: C.slate, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 09  RAG + Anti-Hallucination
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.red }, line: { color: C.red, width: 0 } });
    s.addText('RAG  +  ANTI-HALLUCINATION GUARD', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Flow diagram (top)
    const flowItems = [
      { label: 'User Query', bg: C.teal },
      { label: 'Embed\n(384-dim)', bg: C.purpleM },
      { label: 'ChromaDB\nTop-K Search', bg: C.purple },
      { label: 'Metadata\nFilter', bg: C.purpleM },
      { label: 'SLM Prompt\n+ Context', bg: C.green },
      { label: 'Guard\nValidation', bg: C.red },
      { label: 'Response', bg: C.teal },
    ];
    const FW = 1.0, FH = 0.78, FY = 1.1, FGap = 0.22;
    flowItems.forEach(({ label, bg }, i) => {
      s.addShape('rect', { x: 0.25 + i * (FW + FGap), y: FY, w: FW, h: FH,
        fill: { color: bg }, shadow: mkShadowSm(), line: { color: bg, width: 0 } });
      s.addText(label, { x: 0.25 + i * (FW + FGap), y: FY, w: FW, h: FH,
        align: 'center', valign: 'middle', fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri' });
      if (i < flowItems.length - 1)
        s.addText('→', { x: 0.25 + i * (FW + FGap) + FW, y: FY + 0.2, w: FGap, h: 0.4,
          align: 'center', fontSize: 14, color: C.slate, fontFace: 'Calibri' });
    });

    // Left: RAG config
    sectionLabel(s, 'RAG CONFIGURATION', 0.25, 2.15);
    const ragItems = [
      ['Vector Store', 'ChromaDB  (local :8002 or managed)'],
      ['Embedding', 'all-MiniLM-L6-v2  —  384-dim, CPU'],
      ['Top-K', 'K = 5 documents per query (configurable)'],
      ['Min Relevance', '0.35 cosine similarity threshold'],
      ['Metadata Filter', 'exam · year · subject · micro_topic'],
      ['Context Injection', 'Retrieved docs prepended to SLM prompt'],
    ];
    ragItems.forEach(([label, val], i) => {
      const y = 2.43 + i * 0.46;
      if (i % 2 === 0) s.addShape('rect', { x: 0.25, y, w: 4.6, h: 0.46,
        fill: { color: C.card }, line: { color: C.card, width: 0 } });
      s.addText(label + ':', { x: 0.35, y, w: 1.55, h: 0.46, valign: 'middle',
        fontSize: 9.5, bold: true, color: C.tealLt, fontFace: 'Calibri' });
      s.addText(val,   { x: 1.95, y, w: 2.85, h: 0.46, valign: 'middle',
        fontSize: 9.5, color: C.offWhite, fontFace: 'Calibri' });
    });

    // Right: Anti-hallucination guard
    sectionLabel(s, 'ANTI-HALLUCINATION', 5.15, 2.15);
    const guardItems = [
      [C.green,  '≥ 0.85', 'Grounding accuracy target\nAll numerical facts verified vs. DB'],
      [C.teal,   '≥ 0.75', 'Factual consistency target\nClaims cross-checked multi-source'],
      [C.red,    '≤ 10%',  'Fallback rate target\nTemplate response if confidence fails'],
    ];
    guardItems.forEach(([c, metric, desc], i) => {
      s.addShape('rect', { x: 5.15, y: 2.43 + i * 1.02, w: 4.6, h: 0.88,
        fill: { color: C.surface }, shadow: mkShadowSm(), line: { color: c, width: 1.5 } });
      s.addShape('rect', { x: 5.15, y: 2.43 + i * 1.02, w: 1.1, h: 0.88,
        fill: { color: c, transparency: 20 }, line: { color: c, width: 0 } });
      s.addText(metric, { x: 5.15, y: 2.43 + i * 1.02, w: 1.1, h: 0.88,
        align: 'center', valign: 'middle', fontSize: 22, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(desc, { x: 6.35, y: 2.43 + i * 1.02, w: 3.3, h: 0.88,
        valign: 'middle', fontSize: 10, color: C.offWhite, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 10  Frontend Architecture
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.teal }, line: { color: C.teal, width: 0 } });
    s.addText('FRONTEND ARCHITECTURE', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Left: Streamlit
    card(s, 0.25, 1.05, 4.55, 4.35, C.purple);
    s.addShape('rect', { x: 0.25, y: 1.05, w: 4.55, h: 0.32, fill: { color: C.purple },
      line: { color: C.purple, width: 0 } });
    s.addText('STREAMLIT DASHBOARD  :8501', { x: 0.4, y: 1.05, w: 4.3, h: 0.32,
      valign: 'middle', fontSize: 10, bold: true, color: C.white, fontFace: 'Calibri' });
    const streamItems = [
      'Multi-page: Insights · Deep Dive · Copilot · API Docs',
      'Live SQLite integration + Plotly charts',
      'Student list with search + batch filter',
      'Hero card: accuracy %, strength zones, score',
      'Ranked prediction cards with urgency badges',
      'Copilot chat (streamed SLM responses)',
      'Dark theme — #0F0F1A / #7C3AED',
    ];
    s.addText(streamItems.map(t => ({ text: t, options: { bullet: true, breakLine: true, color: C.offWhite } })),
      { x: 0.42, y: 1.46, w: 4.25, h: 3.7, fontSize: 10.5, fontFace: 'Calibri', paraSpaceAfter: 6 });

    // Right: Static HTML
    card(s, 5.2, 1.05, 4.55, 4.35, C.teal);
    s.addShape('rect', { x: 5.2, y: 1.05, w: 4.55, h: 0.32, fill: { color: C.teal },
      line: { color: C.teal, width: 0 } });
    s.addText('STATIC HTML DASHBOARD  (no server)', { x: 5.35, y: 1.05, w: 4.3, h: 0.32,
      valign: 'middle', fontSize: 10, bold: true, color: C.white, fontFace: 'Calibri' });
    const htmlItems = [
      'Pure vanilla JS — zero framework dependency',
      'Loads pre-built JSON summaries (903 KB NEET)',
      'Level system: M ≥80%  S ≥65%  D ≥45%  W ≥25%  C <25%',
      'Priority score: (100−accuracy) × (slmImportance/100)',
      'Lazy guide: 59 chapter cards built on first expand',
      'Micro-topic API with Map-based dedup cache',
      'Chart.js radar + bar charts',
    ];
    s.addText(htmlItems.map(t => ({ text: t, options: { bullet: true, breakLine: true, color: C.offWhite } })),
      { x: 5.37, y: 1.46, w: 4.25, h: 3.7, fontSize: 10.5, fontFace: 'Calibri', paraSpaceAfter: 6 });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 11  Deployment & Infrastructure
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.green }, line: { color: C.green, width: 0 } });
    s.addText('DEPLOYMENT & INFRASTRUCTURE', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Deployment options grid
    const opts = [
      { title: 'Local Dev',      c: C.teal,   icon: '💻',
        lines: ['python run.py', 'uvicorn :8001 --reload', 'open student-dashboard.html'] },
      { title: 'Docker Compose', c: C.purple,  icon: '🐳',
        lines: ['API :8001', 'Ollama :11434', 'ChromaDB :8002'] },
      { title: 'Railway',        c: C.green,  icon: '🚂',
        lines: ['railway.toml config', 'Streamlit-first', 'Git-push deploy'] },
      { title: 'ngrok Tunnel',   c: C.amber,  icon: '🌐',
        lines: ['python serve.py', 'Public URL generated', 'Demo-ready sharing'] },
    ];
    opts.forEach(({ title, c, icon, lines }, i) => {
      const x = 0.25 + (i % 2) * 4.88, y = 1.1 + Math.floor(i / 2) * 2.2;
      s.addShape('rect', { x, y, w: 4.6, h: 2.0, fill: { color: C.surface },
        shadow: mkShadow(), line: { color: c, width: 1.5 } });
      s.addShape('rect', { x, y, w: 4.6, h: 0.06, fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(icon, { x, y: y + 0.1, w: 0.7, h: 0.6, align: 'center', valign: 'middle',
        fontSize: 22, fontFace: 'Calibri' });
      s.addText(title, { x: x + 0.7, y: y + 0.14, w: 3.8, h: 0.52,
        valign: 'middle', fontSize: 16, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(lines.map(l => ({ text: l, options: { bullet: true, breakLine: true, color: C.offWhite } })),
        { x: x + 0.2, y: y + 0.78, w: 4.25, h: 1.05,
          fontSize: 11, fontFace: 'Calibri', paraSpaceAfter: 3 });
    });

    // Env config highlight
    s.addShape('rect', { x: 0.25, y: 5.18, w: 9.5, h: 0.25, fill: { color: C.purpleM },
      line: { color: C.purpleM, width: 0 } });
    s.addText('Key env vars: SLM_PROVIDER · OLLAMA_MODEL · RAG_ENABLED · CHROMA_HOST · PREDICTION_CACHE_TTL_SEC · CORS_ORIGINS',
      { x: 0.4, y: 5.18, w: 9.2, h: 0.25, valign: 'middle',
        fontSize: 9, color: C.offWhite, fontFace: 'Calibri' });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 12  Quality Metrics & Roadmap
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };

    s.addShape('rect', { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.bg }, line: { color: C.bg, width: 0 } });
    s.addShape('rect', { x: 0, y: 0.82, w: 10, h: 0.04, fill: { color: C.amber }, line: { color: C.amber, width: 0 } });
    s.addText('QUALITY METRICS  &  ROADMAP', { x: 0.4, y: 0, w: 9, h: 0.82, valign: 'middle',
      fontSize: 26, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 3 });

    // Left: metric bars
    sectionLabel(s, 'QUALITY METRICS', 0.25, 1.05);
    const metrics = [
      ['Coverage@10',         '60%', 0.60, C.green],
      ['Heavy-Topic Recall',  '75%', 0.75, C.teal],
      ['Rank Correlation τ',  '≥0.70', 0.70, C.purple],
      ['Grounding Accuracy',  '85%', 0.85, C.amber],
      ['Student Usefulness',  '80%', 0.80, C.green],
    ];
    metrics.forEach(([label, target, pct, c], i) => {
      const y = 1.33 + i * 0.72;
      s.addText(label,  { x: 0.25, y, w: 2.1, h: 0.36, valign: 'middle',
        fontSize: 10, color: C.offWhite, fontFace: 'Calibri' });
      // Bar track
      s.addShape('rect', { x: 2.4, y: y + 0.06, w: 2.2, h: 0.24,
        fill: { color: C.card }, line: { color: C.card, width: 0 } });
      // Bar fill
      s.addShape('rect', { x: 2.4, y: y + 0.06, w: 2.2 * pct, h: 0.24,
        fill: { color: c }, line: { color: c, width: 0 } });
      s.addText(target, { x: 4.65, y, w: 0.6, h: 0.36, valign: 'middle', align: 'right',
        fontSize: 11, bold: true, color: c, fontFace: 'Calibri' });
    });

    // Right: roadmap
    sectionLabel(s, 'ROADMAP', 5.4, 1.05);
    const phases = [
      { phase: 'Phase 1', label: 'Foundation',          c: C.green,  status: '✓ Done' },
      { phase: 'Phase 2', label: 'Intelligence API',    c: C.teal,   status: '✓ Done' },
      { phase: 'Phase 3', label: 'Student Personalisation', c: C.purple, status: '✓ Done' },
      { phase: 'Phase 4', label: 'Production Hardening', c: C.amber,  status: '→ In Progress' },
      { phase: 'Phase 5', label: 'Advanced Features',   c: C.slate,  status: '◷ Planned' },
    ];
    phases.forEach(({ phase, label, c, status }, i) => {
      const y = 1.33 + i * 0.75;
      s.addShape('rect', { x: 5.4, y, w: 4.3, h: 0.64, fill: { color: C.surface },
        shadow: mkShadowSm(), line: { color: c, width: 1 } });
      s.addShape('rect', { x: 5.4, y, w: 0.06, h: 0.64, fill: { color: c }, line: { color: c, width: 0 } });
      s.addShape('rect', { x: 5.5, y: y + 0.18, w: 0.82, h: 0.28,
        fill: { color: c, transparency: 25 }, line: { color: c, width: 0 } });
      s.addText(phase, { x: 5.5, y: y + 0.18, w: 0.82, h: 0.28, align: 'center', valign: 'middle',
        fontSize: 8, bold: true, color: C.white, fontFace: 'Calibri' });
      s.addText(label,  { x: 6.4, y, w: 2.3, h: 0.64, valign: 'middle',
        fontSize: 10.5, bold: true, color: C.offWhite, fontFace: 'Calibri' });
      s.addText(status, { x: 8.75, y, w: 0.95, h: 0.64, align: 'right', valign: 'middle',
        fontSize: 9, color: c, fontFace: 'Calibri' });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SLIDE 13  Closing / CTA
  // ───────────────────────────────────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Left accent
    s.addShape('rect', { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: C.purple },
      line: { color: C.purple, width: 0 } });

    // Grid bg (right)
    s.addShape('rect', { x: 5.5, y: 0, w: 4.5, h: 5.625, fill: { color: C.navy },
      line: { color: C.navy, width: 0 } });
    for (let r = 0; r < 5; r++) for (let c = 0; c < 8; c++) {
      s.addShape('ellipse', {
        x: 5.85 + c * 0.5, y: 0.4 + r * 0.9, w: 0.07, h: 0.07,
        fill: { color: C.purpleLt, transparency: 75 }, line: { color: C.purpleLt, width: 0 }
      });
    }

    s.addText('PRAJNA', { x: 0.4, y: 0.85, w: 5, h: 1.0,
      fontSize: 64, bold: true, color: C.white, fontFace: 'Calibri', charSpacing: 8 });
    s.addText('Built to make every study hour count.', { x: 0.4, y: 1.9, w: 5.2, h: 0.5,
      fontSize: 16, color: C.purpleLt, fontFace: 'Calibri', italics: true });

    divLine(s, 0.4, 2.55, 4.8);

    const summary = [
      '23,119 questions  ·  25 years  ·  3 exam types',
      '23M-param SLM with 15 temporal features',
      'FastAPI + RAG + pluggable SLM providers',
      'Static + Streamlit dual frontend',
    ];
    s.addText(summary.map(t => ({ text: t, options: { bullet: true, breakLine: true, color: C.offWhite } })),
      { x: 0.4, y: 2.7, w: 4.8, h: 2.0, fontSize: 12, fontFace: 'Calibri', paraSpaceAfter: 8 });

    // Bottom strip
    s.addShape('rect', { x: 0, y: 4.9, w: 10, h: 0.725, fill: { color: C.purpleM },
      line: { color: C.purpleM, width: 0 } });
    s.addText('docs/prajna-arch-doc.docx   ·   docs/prajna-deck/prajna-arch-ppt.pptx   ·   v1.0  March 2026',
      { x: 0.3, y: 4.9, w: 9.4, h: 0.725, align: 'center', valign: 'middle',
        fontSize: 10, color: C.offWhite, fontFace: 'Calibri' });
  }

  await pres.writeFile({ fileName: '/Users/aman/exam-predictor/docs/prajna-deck/prajna-arch-ppt.pptx' });
  console.log('Done → prajna-arch-ppt.pptx');
}

buildDeck().catch(err => { console.error(err); process.exit(1); });
