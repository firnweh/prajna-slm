'use strict';
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  ExternalHyperlink, TableOfContents,
} = require('docx');
const fs = require('fs');

// ─── Colours ─────────────────────────────────────────────────────────────────
const PURPLE     = '7C3AED';
const PURPLE_LT  = 'EDE9FE';
const TEAL       = '0891B2';
const TEAL_LT    = 'E0F2FE';
const GREEN      = '16A34A';
const GREEN_LT   = 'DCFCE7';
const AMBER      = 'D97706';
const AMBER_LT   = 'FEF3C7';
const DARK       = '1E1B4B';
const SLATE      = '374151';
const BORDER_CLR = 'CBD5E1';
const HEADER_BG  = '312E81';  // deep indigo
const ROW_EVEN   = 'F8F5FF';
const WHITE      = 'FFFFFF';
const GRAY_LT    = 'F1F5F9';

// ─── Page dimensions (US Letter, 1" margins) ─────────────────────────────────
const PAGE_W   = 12240;
const PAGE_H   = 15840;
const MARGIN   = 1440;
const CONTENT_W = PAGE_W - 2 * MARGIN; // 9360 DXA

// ─── Helpers ──────────────────────────────────────────────────────────────────
const border = (clr = BORDER_CLR, sz = 4) =>
  ({ style: BorderStyle.SINGLE, size: sz, color: clr });

const cellBorders = (clr = BORDER_CLR) => ({
  top: border(clr), bottom: border(clr), left: border(clr), right: border(clr),
});

const noBorder = () => ({ style: BorderStyle.NIL, size: 0, color: WHITE });
const noBorders = () => ({ top: noBorder(), bottom: noBorder(), left: noBorder(), right: noBorder() });

const cellPad = { top: 100, bottom: 100, left: 140, right: 140 };
const tightPad = { top: 60, bottom: 60, left: 120, right: 120 };

function heading1(text, color = DARK) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: PURPLE, space: 6 } },
    children: [new TextRun({ text, font: 'Arial', color, bold: true, size: 28 })],
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 100 },
    children: [new TextRun({ text, font: 'Arial', color: PURPLE, bold: true, size: 24 })],
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: 'Arial', color: TEAL, bold: true, size: 22 })],
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 80, line: 280 },
    children: [new TextRun({
      text, font: 'Arial', size: 20, color: SLATE, ...opts,
    })],
  });
}

function bodyBold(text) {
  return body(text, { bold: true, color: DARK });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    spacing: { before: 40, after: 40, line: 260 },
    children: [new TextRun({ text, font: 'Arial', size: 20, color: SLATE })],
  });
}

function note(text) {
  return new Paragraph({
    spacing: { before: 80, after: 100 },
    indent: { left: 360 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: TEAL, space: 8 } },
    children: [new TextRun({ text, font: 'Arial', size: 18, color: TEAL, italics: true })],
  });
}

function spacer(before = 80) {
  return new Paragraph({ spacing: { before, after: 0 }, children: [new TextRun('')] });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// ─── Badge cell (coloured pill-like header cell) ──────────────────────────────
function badgeCell(text, bg, fg = WHITE, w = 1400) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders(bg),
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: tightPad,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, font: 'Arial', size: 18, bold: true, color: fg })],
    })],
  });
}

function dataCell(text, w, bg = WHITE, bold = false, color = SLATE) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders(BORDER_CLR),
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: cellPad,
    verticalAlign: VerticalAlign.TOP,
    children: [new Paragraph({
      children: [new TextRun({ text, font: 'Arial', size: 19, color, bold })],
    })],
  });
}

// ─── Full-width header row ────────────────────────────────────────────────────
function tableHeaderRow(cols, widths, bg = HEADER_BG) {
  return new TableRow({
    tableHeader: true,
    children: cols.map((c, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      borders: cellBorders(bg),
      shading: { fill: bg, type: ShadingType.CLEAR },
      margins: cellPad,
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: AlignmentType.LEFT,
        children: [new TextRun({ text: c, font: 'Arial', size: 19, bold: true, color: WHITE })],
      })],
    })),
  });
}

// ─── Data row ─────────────────────────────────────────────────────────────────
function dataRow(cells, widths, even = false) {
  const bg = even ? ROW_EVEN : WHITE;
  return new TableRow({
    children: cells.map((c, i) => dataCell(c, widths[i], bg)),
  });
}

// ─── Code block (monospace, shaded) ──────────────────────────────────────────
function codeBlock(lines) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CONTENT_W, type: WidthType.DXA },
        borders: { top: border('94A3B8'), bottom: border('94A3B8'), left: border(PURPLE, 8), right: border('94A3B8') },
        shading: { fill: '0F172A', type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 200, right: 120 },
        children: lines.map(l => new Paragraph({
          spacing: { before: 20, after: 20 },
          children: [new TextRun({ text: l, font: 'Courier New', size: 17, color: '94F3D4' })],
        })),
      })],
    })],
  });
}

// ─── Section title card (full-width purple banner) ───────────────────────────
function sectionBanner(num, title) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [1200, CONTENT_W - 1200],
    rows: [new TableRow({
      children: [
        new TableCell({
          width: { size: 1200, type: WidthType.DXA },
          borders: noBorders(),
          shading: { fill: PURPLE, type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 160, right: 160 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: `§${num}`, font: 'Arial', size: 36, bold: true, color: WHITE })],
          })],
        }),
        new TableCell({
          width: { size: CONTENT_W - 1200, type: WidthType.DXA },
          borders: noBorders(),
          shading: { fill: DARK, type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 200, right: 200 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            children: [new TextRun({ text: title, font: 'Arial', size: 28, bold: true, color: WHITE })],
          })],
        }),
      ],
    })],
  });
}

// ─── Cover page ───────────────────────────────────────────────────────────────
function buildCoverPage() {
  return [
    // Big title block
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [CONTENT_W],
      rows: [new TableRow({
        children: [new TableCell({
          width: { size: CONTENT_W, type: WidthType.DXA },
          borders: noBorders(),
          shading: { fill: DARK, type: ShadingType.CLEAR },
          margins: { top: 600, bottom: 600, left: 480, right: 480 },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 120 },
              children: [new TextRun({ text: 'PRAJNA', font: 'Arial', size: 72, bold: true, color: 'A78BFA' })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 80 },
              children: [new TextRun({ text: 'Exam Intelligence Platform', font: 'Arial', size: 32, color: WHITE, italics: true })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: 'Technical Architecture Document', font: 'Arial', size: 24, color: '94A3B8' })],
            }),
          ],
        })],
      })],
    }),
    spacer(400),
    // Metadata grid
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2200, 4960, 2200],
      rows: [
        new TableRow({ children: [
          dataCell('Document Version', 2200, GRAY_LT, true, DARK),
          dataCell('v1.0  —  March 2026', 4960, WHITE),
          dataCell('Classification', 2200, GRAY_LT, true, DARK),
        ]}),
        new TableRow({ children: [
          dataCell('Scope', 2200, GRAY_LT, true, DARK),
          dataCell('Full-stack architecture: data ingestion → ML engine → intelligence API → frontend', 4960, ROW_EVEN),
          dataCell('Internal', 2200, WHITE),
        ]}),
        new TableRow({ children: [
          dataCell('Target Exams', 2200, GRAY_LT, true, DARK),
          dataCell('NEET · JEE Main · JEE Advanced', 4960, WHITE),
          dataCell('Confidential', 2200, ROW_EVEN),
        ]}),
      ],
    }),
    spacer(480),
    // Abstract
    new Paragraph({
      spacing: { before: 0, after: 120, line: 320 },
      border: { left: { style: BorderStyle.SINGLE, size: 16, color: PURPLE, space: 12 } },
      indent: { left: 360 },
      children: [
        new TextRun({ text: 'Abstract — ', font: 'Arial', size: 21, bold: true, color: DARK }),
        new TextRun({
          text: 'PRAJNA is a production-grade exam intelligence platform for Indian competitive exams. It combines a 23,119-question historical database, a 23M-parameter Small Language Model (SLM), and a RAG-powered FastAPI layer to deliver personalised chapter-level predictions, study strategies, and micro-topic insights to students. This document details every architectural layer from raw data ingestion through to the student-facing dashboard.',
          font: 'Arial', size: 20, color: SLATE,
        }),
      ],
    }),
    pageBreak(),
  ];
}

// ─── Section 1 — System Overview ─────────────────────────────────────────────
function buildOverview() {
  const rows = [
    ['Total Questions', '23,119', 'NEET + JEE Main + JEE Advanced, 2000–2025'],
    ['Years Covered', '25 years', '2000 through 2025 (inclusive)'],
    ['Student Records', '1,000+', 'Mock exam results with per-chapter accuracy'],
    ['SLM Parameters', '23 M', 'PRAJNA SLM (Sentence-Transformer + MLP)'],
    ['Embedding Dimensions', '384', 'all-MiniLM-L6-v2 base model'],
    ['Feature Vector', '399', '384 text-embed + 15 temporal/statistical features'],
    ['REST Endpoints', '12', 'Predictions · Insights · Copilot · Reports · Bridge'],
    ['Pre-trained Models', '3', 'NEET, JEE Main, JEE Advanced (separate weights)'],
    ['API Latency Target', '≤ 3 s', 'P95 end-to-end (Ollama 7B)'],
    ['Fallback Rate Target', '≤ 10 %', 'Template response when SLM confidence low'],
  ];
  const W = [2600, 1800, 4960];

  return [
    sectionBanner(1, 'System Overview'),
    spacer(200),
    body('PRAJNA is structured as three loosely-coupled tiers that communicate through well-defined interfaces:'),
    spacer(80),
    bullet('Tier 1 — Data & ML Engine  (Python, PyTorch, SQLite)'),
    bullet('Tier 2 — Intelligence Layer  (FastAPI, ChromaDB, pluggable SLM providers)'),
    bullet('Tier 3 — Frontend  (Streamlit dashboard + static HTML/JS client)'),
    spacer(200),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W,
      rows: [
        tableHeaderRow(['Metric', 'Value', 'Notes'], W),
        ...rows.map(([a,b,c], i) => dataRow([a,b,c], W, i%2===0)),
      ],
    }),
    spacer(160),
    note('All tiers can run independently. The static HTML dashboard (docs/student-dashboard.html) requires no server — it loads pre-computed JSON summaries directly.'),
    pageBreak(),
  ];
}

// ─── Section 2 — High-Level Architecture ─────────────────────────────────────
function buildHighLevel() {
  return [
    sectionBanner(2, 'High-Level Architecture'),
    spacer(200),
    heading2('2.1  Conceptual Tiers'),
    body('The diagram below represents the primary data and control flows:'),
    spacer(120),
    codeBlock([
      '┌────────────────────────────────────────────────────────────────────────┐',
      '│                      PRAJNA  PLATFORM                                  │',
      '├──────────────┬─────────────────────────────┬──────────────────────────┤',
      '│  DATA TIER   │     INTELLIGENCE TIER        │     FRONTEND TIER        │',
      '├──────────────┼─────────────────────────────┼──────────────────────────┤',
      '│ exam.db      │ FastAPI  :8001               │ Streamlit  :8501         │',
      '│ (SQLite)     │  /predictions/*              │  — Student list          │',
      '│ 23,119 Qs    │  /insights/*                 │  — Prediction cards      │',
      '│              │  /copilot/ask                │  — Copilot chat          │',
      '│ student CSVs │  /reports/*                  │                          │',
      '│ (16 + 21 MB) │  /data/*                     │ Static HTML              │',
      '│              │                              │  — docs/student-         │',
      '│ PRAJNA SLM   │ ChromaDB  :8002  (RAG)       │    dashboard.html        │',
      '│ (.pt models) │                              │  — Pure JS, no server    │',
      '│              │ Ollama    :11434 (SLM)       │  — Chart.js rendering    │',
      '│ predictor_v3 │                              │                          │',
      '│ (3-stage)    │ Redis     (opt. cache)       │ Streamlit Cloud /        │',
      '│              │                              │ Railway / Heroku / ngrok │',
      '└──────────────┴─────────────────────────────┴──────────────────────────┘',
    ]),
    spacer(200),
    heading2('2.2  Request Lifecycle'),
    body('A typical "chapter importance" request flows as follows:'),
    spacer(80),
    bullet('1.  Student selects a chapter in the dashboard (Streamlit or HTML client).'),
    bullet('2.  Client calls POST /api/v1/insights/chapter with {chapter, exam, year}.'),
    bullet('3.  FastAPI dependency injection provides a singleton PredictionAdapter.'),
    bullet('4.  Adapter calls PRAJNA ML engine (locally or via HTTP) to get ranked prediction list.'),
    bullet('5.  TopicAggregator batches topics, computes priority scores, filters by confidence.'),
    bullet('6.  RAGRetriever queries ChromaDB with sentence-transformer embedding of the chapter name.'),
    bullet('7.  Top-K documents (metadata-filtered by exam & year) are appended to the SLM prompt.'),
    bullet('8.  SLM provider (Ollama / HuggingFace / OpenAI-compatible) generates structured JSON.'),
    bullet('9.  Anti-hallucination guard verifies all cited facts against database ground truth.'),
    bullet('10. Response serialised with Pydantic schemas, cached in Redis (TTL = 1 hour).'),
    spacer(120),
    note('If confidence score < 0.35 at Step 9, the system falls back to template-based responses to prevent hallucination. The fallback rate target is ≤ 10 %.'),
    pageBreak(),
  ];
}

// ─── Section 3 — Data Layer ───────────────────────────────────────────────────
function buildDataLayer() {
  const schemaRows = [
    ['id', 'TEXT PK', '"JEE_ADV_2019_P1_Q12"'],
    ['exam', 'TEXT NOT NULL', '"NEET" | "JEE Main" | "JEE Advanced"'],
    ['year', 'INTEGER NOT NULL', '2000 – 2025'],
    ['shift', 'TEXT', '"Shift 1" | "Morning" | "Paper 1"'],
    ['subject', 'TEXT NOT NULL', '"Physics" | "Chemistry" | "Biology" | "Mathematics"'],
    ['topic', 'TEXT NOT NULL', 'Broad topic (chapter-level)'],
    ['micro_topic', 'TEXT NOT NULL', 'Specific subtopic'],
    ['question_text', 'TEXT', 'Full question text'],
    ['question_type', 'TEXT', 'MCQ_single | MCQ_multi | integer | numerical | matrix_match'],
    ['difficulty', 'INTEGER', '1 – 5 scale'],
    ['concepts_tested', 'TEXT', 'JSON array of concept strings'],
    ['answer', 'TEXT', 'Correct answer'],
    ['marks', 'INTEGER', 'Marks awarded per question'],
  ];
  const W1 = [2000, 2000, 5360];

  const fileRows = [
    ['syllabus.py', '16.5 KB', 'NEET & JEE official syllabi (subject → chapter → topics)'],
    ['historical_events.py', '6.9 KB', 'Policy & syllabus-change timeline 2000–2025'],
    ['neet_results_v2.csv', '16 MB', 'Student mock exam results (chapter-level accuracy)'],
    ['jee_results_v2.csv', '21.4 MB', 'JEE student mock exam results'],
    ['students_v2.csv', '14 KB', 'Student metadata (name, batch, ID)'],
    ['neet_summary_v2.csv', '145 KB', 'Aggregated NEET per-student performance'],
    ['jee_summary_v2.csv', '153 KB', 'Aggregated JEE per-student performance'],
    ['student_summary_neet.json', '903 KB', 'Pre-computed intelligence summaries (dashboard use)'],
    ['student_summary_jee.json', '804 KB', 'Pre-computed JEE intelligence summaries'],
  ];
  const W2 = [3000, 1600, 4760];

  return [
    sectionBanner(3, 'Data Layer'),
    spacer(200),
    heading2('3.1  Primary Database  (exam.db — SQLite, 10.9 MB)'),
    body('All extracted exam questions are persisted in a single SQLite file for portability. The schema is flat — no foreign-key joins required at inference time.'),
    spacer(120),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W1,
      rows: [
        tableHeaderRow(['Column', 'Type', 'Notes'], W1),
        ...schemaRows.map(([a,b,c], i) => dataRow([a,b,c], W1, i%2===0)),
      ],
    }),
    spacer(200),
    heading2('3.2  Supporting Data Files'),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W2,
      rows: [
        tableHeaderRow(['File', 'Size', 'Purpose'], W2),
        ...fileRows.map(([a,b,c], i) => dataRow([a,b,c], W2, i%2===0)),
      ],
    }),
    spacer(200),
    heading2('3.3  Data Ingestion Pipeline'),
    body('Exam papers are converted to structured JSON through a two-step extraction process:'),
    spacer(80),
    bullet('Step 1  —  Raw PDF/HTML exam papers are fed to an extraction prompt template (extraction/prompt_template.md). Claude parses each question, classifies it by subject, topic, micro-topic, type, and difficulty, then outputs structured JSON.'),
    bullet('Step 2  —  utils/loader.py performs bulk insertion into SQLite (exam.db), deduplicating on the composite key (exam, year, shift, question_text).'),
    bullet('Step 3  —  utils/db.py exposes typed helper functions: get_questions_by_exam(), get_topic_hierarchy(), convert_to_dataframe().'),
    spacer(120),
    note('Data ingestion is offline/batch only. No live exam-scraping runs in production. The database is shipped as a static artifact and updated manually each exam cycle.'),
    pageBreak(),
  ];
}

// ─── Section 4 — Prediction Engine ───────────────────────────────────────────
function buildPrediction() {
  const featRows = [
    ['0', 'Appearance rate', 'count(years appeared) / total year span'],
    ['1', 'Recency-weighted freq', 'Σ 1 / (year_diff^1.5 + 1)  — exponential decay'],
    ['2', 'Recent presence (3yr)', 'Binary: did chapter appear in last 3 years?'],
    ['3', 'Recent presence (5yr)', 'Binary: did chapter appear in last 5 years?'],
    ['4', 'Gap (years since last)', 'Current year minus last appearance year'],
    ['5', 'Mean gap', 'Average interval between consecutive appearances'],
    ['6', 'Trend slope', 'Linear regression coefficient on last 10 years'],
    ['7', 'Mean question count', 'Average questions per appearing year'],
    ['8', 'Std-dev question count', 'Variance in questions per year'],
    ['9', 'Max question count', 'Historical peak questions in a single year'],
    ['10', 'Total appearances', 'Normalised by number of exam years in window'],
    ['11', 'Cross-exam presence', '1.0 if chapter appears in ≥ 1 other exam type'],
    ['12', 'Cycle regularity', 'Inverse CV of appearance gaps (high = regular)'],
    ['13', 'Recent yield avg', 'Mean questions in most recent 3 appearances'],
    ['14', 'Subject encoding', '0.25=Physics  0.50=Chemistry  0.75=Biology  1.0=Math'],
  ];
  const W = [600, 2400, 6360];

  return [
    sectionBanner(4, 'Prediction Engine'),
    spacer(200),
    heading2('4.1  PRAJNA SLM  (Small Language Model)'),
    body('PRAJNA SLM is a custom 23M-parameter model that predicts the probability of each chapter appearing on a target exam year. It fuses a pre-trained sentence encoder with hand-engineered temporal features.'),
    spacer(120),
    heading3('Input Layer  (399 dimensions)'),
    codeBlock([
      'chapter_name  ──→  all-MiniLM-L6-v2  ──→  384-dim embedding',
      '                                                     │',
      '15 temporal features  ───────────────────────────────┤ concat',
      '                                                     │',
      '                                              399-dim vector',
    ]),
    spacer(160),
    heading3('15 Temporal / Statistical Features'),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W,
      rows: [
        tableHeaderRow(['Idx', 'Name', 'Computation'], W),
        ...featRows.map(([a,b,c], i) => dataRow([a,b,c], W, i%2===0)),
      ],
    }),
    spacer(200),
    heading3('MLP Architecture  (399 → 256 → 128 → 64)'),
    codeBlock([
      'Input (399)  →  Dense(256, ReLU)  →  BatchNorm  →  Dropout(0.2)',
      '             →  Dense(128, ReLU)  →  BatchNorm  →  Dropout(0.2)',
      '             →  Dense( 64, ReLU)',
      '             →  ┌──────────────────────────────────────────────┐',
      '                │ Head 1: Dense(1)    sigmoid  → P(appear)     │',
      '                │ Head 2: Dense(1)    linear   → E[questions]  │',
      '                │ Head 3: Dense(5)    softmax  → difficulty cls │',
      '                └──────────────────────────────────────────────┘',
    ]),
    spacer(200),
    heading2('4.2  Predictor v3  (3-Stage Statistical Model)'),
    body('predictor_v3.py implements a complementary statistical pipeline that runs alongside the SLM and whose outputs are merged before ranking.'),
    spacer(80),
    bullet('Stage 1 — Appearance probability.  Combines recency-weighted frequency, gap-return probability (peaks at 2× mean gap), trend slope (linear regression), and cycle-match score into a single P(appear) per chapter.'),
    bullet('Stage 2 — Weightage model.  Estimates expected question count, given that the chapter appears. Based on historical question-count distributions per chapter.'),
    bullet('Stage 3 — Question format prediction.  Classifies likely question types (MCQ single, MCQ multi, integer, numerical, matrix match) from historical distributions.'),
    spacer(120),
    heading3('Post-Processing & Constraint Satisfaction'),
    bullet('Subject balance quotas — Physics / Chemistry / Biology / Mathematics each have minimum and maximum slot allocations matching the official exam pattern.'),
    bullet('Unique chapter enforcement — each chapter may appear at most once in the final ranked list.'),
    bullet('Diversification penalty — correlated chapters (sharing ≥ 80 % topic overlap) are down-ranked to increase prediction diversity.'),
    bullet('Iterative reranking — constraint violations are resolved via a greedy swap loop until all constraints are satisfied.'),
    spacer(120),
    heading2('4.3  Pre-trained Model Artefacts'),
    body('Three separate model files are stored in /models/:'),
    spacer(80),
    bullet('slm_neet_chapter.pt  +  slm_neet_chapter_embeddings.npy  —  NEET-specific weights'),
    bullet('slm_jee_main_chapter.pt  +  slm_jee_main_chapter_embeddings.npy  —  JEE Main weights'),
    bullet('slm_jee_advanced_chapter.pt  +  slm_jee_advanced_chapter_embeddings.npy  —  JEE Advanced weights'),
    spacer(80),
    note('Each model is trained exclusively on data before its hold-out year (2024+). Training used PyTorch DataLoader with a combined loss: MSE for regression heads and cross-entropy for the difficulty classification head. Backtesting hold-out set: {2024, 2025, 2026}.'),
    pageBreak(),
  ];
}

// ─── Section 5 — Intelligence Layer ──────────────────────────────────────────
function buildIntelligence() {
  const endpointRows = [
    ['GET',  '/api/v1/predictions/batch-summary',   'Subject-level importance overview'],
    ['GET',  '/api/v1/predictions/rank-all',         'Global chapter ranking, all subjects'],
    ['GET',  '/api/v1/predictions/chapter/{name}',   'Chapter-level prediction breakdown'],
    ['POST', '/api/v1/insights/micro-topic',          'SLM explains micro-topic with citations'],
    ['POST', '/api/v1/insights/chapter',              'Chapter intelligence with topic clusters'],
    ['POST', '/api/v1/reports/revision-plan',         'Complete prioritised revision plan PDF'],
    ['GET',  '/api/v1/reports/trend-summary',         'Trending topic briefing'],
    ['POST', '/api/v1/copilot/ask',                   'Natural language Q&A via SLM + RAG'],
    ['GET',  '/api/v1/data/trends',                   'Bridge to trend_analyzer.py'],
    ['GET',  '/api/v1/data/deep-analysis/{chapter}',  'Bridge to deep_analysis.py'],
    ['GET',  '/health',                               'Service health check'],
  ];
  const W = [800, 3800, 4760];

  const slmRows = [
    ['mock',         'Zero setup', 'Testing & CI — returns deterministic fixtures'],
    ['ollama',       'Local (recommended)', 'mistral:7b-instruct via Ollama :11434'],
    ['huggingface',  'Local GPU/MPS/CPU', 'microsoft/phi-3-mini-4k-instruct (transformers)'],
    ['openai_compatible', 'Remote API', 'GPT-4o-mini, Groq, Together.ai, LM Studio, vLLM'],
  ];
  const W2 = [2400, 2400, 4560];

  return [
    sectionBanner(5, 'Intelligence Layer  (FastAPI)'),
    spacer(200),
    heading2('5.1  Service Structure'),
    body('The intelligence layer is a self-contained Python package under intelligence/ that wraps the prediction engine with SLM-powered text generation and RAG retrieval.'),
    spacer(120),
    codeBlock([
      'intelligence/',
      '├── services/api/',
      '│   ├── main.py          ← FastAPI app factory + middleware (CORS, logging)',
      '│   ├── deps.py          ← Singleton dependency injection (providers cached)',
      '│   └── routers/         ← Route modules (one per domain)',
      '├── services/insight_engine/',
      '│   ├── slm_provider.py  ← Abstract SLM interface + four concrete providers',
      '│   └── generator.py     ← Prompt assembly + anti-hallucination guard',
      '├── services/rag/',
      '│   ├── indexer.py       ← ChromaDB ingestion (batch upsert)',
      '│   └── retriever.py     ← Top-K retrieval with metadata filtering',
      '├── services/prediction_adapter/',
      '│   └── client.py        ← PRAJNA engine wrapper (local or HTTP)',
      '├── services/topic_intelligence/',
      '│   ├── aggregator.py    ← Batch builder, priority scorer, topic ranker',
      '│   └── cluster_detector.py ← Semantic topic cluster detection',
      '├── packages/schemas/    ← Pydantic models for all I/O contracts',
      '├── packages/prompts/    ← System prompts, task templates, JSON schemas',
      '├── packages/utils/      ← Confidence scoring, hierarchy helpers',
      '└── config/settings.py   ← Pydantic Settings (env-driven config)',
    ]),
    spacer(200),
    heading2('5.2  REST Endpoints'),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W,
      rows: [
        tableHeaderRow(['Method', 'Path', 'Purpose'], W),
        ...endpointRows.map(([a,b,c], i) => dataRow([a,b,c], W, i%2===0)),
      ],
    }),
    spacer(200),
    heading2('5.3  SLM Provider Strategy'),
    body('The SLM provider is pluggable — swap the backend via a single environment variable (SLM_PROVIDER) with no code changes.'),
    spacer(120),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W2,
      rows: [
        tableHeaderRow(['Provider', 'Mode', 'Details'], W2),
        ...slmRows.map(([a,b,c], i) => dataRow([a,b,c], W2, i%2===0)),
      ],
    }),
    spacer(200),
    heading2('5.4  RAG  (Retrieval-Augmented Generation)'),
    bullet('Vector store  —  ChromaDB running on port 8002 (local) or managed instance.'),
    bullet('Embedding model  —  sentence-transformers/all-MiniLM-L6-v2, 384-dim, CPU by default.'),
    bullet('Indexing  —  Each question stored as a document with metadata: {exam, year, subject, topic, micro_topic, difficulty}. Batch upsert via indexer.py.'),
    bullet('Retrieval  —  Top-K (default K=5) filtered by metadata predicates. Minimum relevance threshold: 0.35.'),
    bullet('Context injection  —  Retrieved documents are appended to the SLM prompt as structured bullet evidence before the task instruction.'),
    spacer(120),
    heading2('5.5  Anti-Hallucination Guard'),
    bullet('All numerical claims in the SLM response (percentages, year counts, question counts) are verified against the database before the response is returned.'),
    bullet('Citation IDs in the SLM JSON output are cross-checked against the RAG document IDs that were actually provided to the model.'),
    bullet('If the grounding accuracy score falls below 0.85, the guard replaces the response with a template-based answer derived directly from database queries.'),
    bullet('Grounding score, factual consistency, and fallback flag are included in every API response envelope for observability.'),
    pageBreak(),
  ];
}

// ─── Section 6 — Frontend Architecture ───────────────────────────────────────
function buildFrontend() {
  return [
    sectionBanner(6, 'Frontend Architecture'),
    spacer(200),
    heading2('6.1  Streamlit Dashboard  (dashboard/app.py — 116 KB)'),
    body('A multi-page Streamlit application with live SQLite integration and real-time Plotly charts. Served on port 8501.'),
    spacer(80),
    bullet('Navigation  —  Sticky header with PRAJNA logo, exam-type toggle (NEET / JEE), global search.'),
    bullet('Student Sidebar  —  Scrollable student list with name search and batch filter. Clicking a student triggers a full re-render of the main panel.'),
    bullet('Hero Card  —  Student name, photo placeholder, key metrics: accuracy %, strength zones count, critical-zone count, predicted score.'),
    bullet('Metrics Row  —  Four KPI cards: Overall Accuracy, Strength Zones, Weak Zones, Predicted Score. Colour-coded green / amber / red.'),
    bullet('Prediction Cards  —  Ranked chapter list with urgency badges (CRITICAL / HIGH / MEDIUM / LOW). Each card shows SLM probability, chapter name, subject, and action text.'),
    bullet('Deep Dive Tab  —  Plotly time-series showing year-by-year question counts for a selected chapter. Topic-level breakdown with difficulty heatmap.'),
    bullet('Copilot Tab  —  Natural-language chatbot backed by /api/v1/copilot/ask. Streamed responses with Markdown rendering.'),
    bullet('API Docs Tab  —  Embedded OpenAPI documentation with curl examples for each endpoint.'),
    spacer(160),
    heading2('6.2  Static HTML Dashboard  (docs/student-dashboard.html — 64 KB)'),
    body('A single-file, zero-dependency HTML/JS client. No server required. Ships alongside the pre-computed JSON summaries.'),
    spacer(80),
    bullet('Data loading  —  Fetches docs/student_summary_neet.json (903 KB) or docs/student_summary_jee.json (804 KB) via the Fetch API on page load.'),
    bullet('Student rendering  —  Vanilla JS (no framework). Each student summary is rendered by a set of builder functions (buildHero, buildMetrics, buildSLMFocus, buildFullGuide) that return DOM nodes appended to a root div.'),
    bullet('Level system  —  Five performance levels: M (Mastered ≥ 80 %), S (Strong ≥ 65 %), D (Developing ≥ 45 %), W (Weak ≥ 25 %), C (Critical < 25 %). Computed client-side from accuracy percentages.'),
    bullet('Priority score  —  priority = (100 − accuracy) × (slmImportance / 100). Chapters are sorted descending by this composite score to surface the highest-ROI study targets first.'),
    bullet('Lazy guide  —  The full subject-wise study guide (59 chapter cards) is built lazily on first expand — avoids rendering 59 DOM subtrees on initial load.'),
    bullet('Micro-topic API  —  Each chapter detail card fetches micro-topic predictions from /api/v1/insights/micro-topic on first open, with a Map-based cache to prevent duplicate calls.'),
    bullet('Charts  —  Chart.js radar chart for subject accuracy, bar chart for chapter performance. Both re-drawn on student change via .destroy() + re-init.'),
    spacer(160),
    heading2('6.3  Colour Palette & Design Tokens'),
    spacer(80),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2200, 2000, 5160],
      rows: [
        tableHeaderRow(['Token', 'Hex', 'Usage'], [2200, 2000, 5160]),
        ...([
          ['Background', '#0F0F1A', 'Page & modal backgrounds'],
          ['Surface', '#161628 / #1E1E35', 'Card and panel backgrounds'],
          ['Purple accent', '#7C3AED', 'Primary brand colour, buttons, borders'],
          ['Purple light', '#A855F7', 'Highlights, hover states'],
          ['Teal accent', '#06B6D4', 'Secondary actions, copilot elements'],
          ['Green (Mastered)', '#22C55E', 'M-level badges'],
          ['Teal (Strong)', '#10B981', 'S-level badges'],
          ['Cyan (Developing)', '#06B6D4', 'D-level badges'],
          ['Amber (Weak)', '#F59E0B', 'W-level badges, warnings'],
          ['Red (Critical)', '#EF4444', 'C-level badges, critical alerts'],
        ]).map(([a,b,c], i) => dataRow([a,b,c], [2200, 2000, 5160], i%2===0)),
      ],
    }),
    pageBreak(),
  ];
}

// ─── Section 7 — Deployment & Infrastructure ─────────────────────────────────
function buildDeployment() {
  return [
    sectionBanner(7, 'Deployment & Infrastructure'),
    spacer(200),
    heading2('7.1  Local Development'),
    codeBlock([
      '# 1. Bootstrap database & launch Streamlit',
      'python run.py',
      '',
      '# 2. Intelligence API (separate terminal)',
      'cd intelligence && pip install -r requirements.txt',
      'cp .env.example .env          # Set SLM_PROVIDER=mock for zero-setup',
      'uvicorn services.api.main:app --port 8001 --reload',
      '',
      '# 3. HTML dashboard (no server needed)',
      'open docs/student-dashboard.html',
      '',
      '# 4. Public tunnel (ngrok)',
      'python serve.py               # prints: "Live at: https://xxxx.ngrok.io"',
    ]),
    spacer(200),
    heading2('7.2  Docker Compose Stack  (intelligence/infra/)'),
    codeBlock([
      'docker compose -f intelligence/infra/docker-compose.yml up -d',
      '# Starts: prajna-api (:8001)  prajna-ollama (:11434)  prajna-chroma (:8002)',
      '',
      'docker exec prajna-ollama ollama pull mistral:7b-instruct',
      'docker exec prajna-intelligence-api python -m scripts.index_documents',
      'curl http://localhost:8001/health',
    ]),
    spacer(200),
    heading2('7.3  Cloud Targets'),
    spacer(80),
    bullet('Railway  —  railway.toml declares the build command and start command. Suitable for the full Streamlit + API stack.'),
    bullet('Heroku  —  Procfile entry: web: python run.py. Free tier supports the Streamlit-only build.'),
    bullet('Streamlit Cloud  —  streamlit_app.py is the Cloud-compatible entry point. Connects to an external SQLite via Supabase or Railway database URL.'),
    spacer(200),
    heading2('7.4  Environment Variables  (intelligence/.env)'),
    codeBlock([
      'ENVIRONMENT=development       # development | production',
      'SLM_PROVIDER=mock             # mock | ollama | huggingface | openai_compatible',
      'OLLAMA_BASE_URL=http://localhost:11434',
      'OLLAMA_MODEL=mistral:7b-instruct',
      'PREDICTION_ADAPTER_MODE=local # local | http',
      'RAG_ENABLED=true',
      'CHROMA_HOST=localhost',
      'CHROMA_PORT=8002',
      'EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2',
      'RAG_TOP_K=5',
      'RAG_MIN_RELEVANCE=0.35',
      'SLM_MAX_TOKENS=1024',
      'SLM_TEMPERATURE=0.2',
      'PREDICTION_CACHE_TTL_SEC=3600',
      'REQUEST_TIMEOUT_SEC=90',
    ]),
    pageBreak(),
  ];
}

// ─── Section 8 — Evaluation & Performance ────────────────────────────────────
function buildEval() {
  const metricRows = [
    ['Coverage@10', '≥ 60 %', '% of actual exam topics in top-10 predictions'],
    ['Heavy-Topic Recall', '≥ 75 %', 'Chapters with 3+ questions recalled in top-20'],
    ['Rank Correlation (τ)', '≥ 0.70', "Kendall τ: predicted rank vs. actual exam frequency"],
    ['Grounding Accuracy', '≥ 85 %', '% SLM facts supported by database evidence'],
    ['Factual Consistency', '≥ 75 %', 'Cross-check SLM claims against multiple sources'],
    ['Student Usefulness', '≥ 80 %', 'Thumbs-up rate on SLM insight cards'],
    ['API Latency P95', '≤ 3,000 ms', 'End-to-end for Ollama mistral:7b-instruct'],
    ['Fallback Rate', '≤ 10 %', '% requests falling back to template responses'],
    ['Subject Balance Error', '≤ 5 %', 'Deviation from official subject quota'],
  ];
  const W = [2600, 1600, 5160];

  return [
    sectionBanner(8, 'Evaluation & Performance'),
    spacer(200),
    heading2('8.1  Quality Metrics'),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: W,
      rows: [
        tableHeaderRow(['Metric', 'Target', 'Definition'], W),
        ...metricRows.map(([a,b,c], i) => dataRow([a,b,c], W, i%2===0)),
      ],
    }),
    spacer(200),
    heading2('8.2  Backtesting Methodology'),
    bullet('Hold-out years — {2024, 2025, 2026} are never used as training data. Models are evaluated by predicting these years from data available before them.'),
    bullet('Coverage@K — for each hold-out exam paper, count how many actual question topics appear in the top-K predictions. Averaged across all hold-out papers.'),
    bullet('Separate evaluation per exam type — NEET, JEE Main, JEE Advanced are evaluated independently with their respective model weights.'),
    spacer(200),
    heading2('8.3  Test Suite  (tests/)'),
    codeBlock([
      'tests/',
      '├── test_db.py              # SQLite init, CRUD operations',
      '├── test_loader.py          # JSON bulk loading, deduplication',
      '├── test_trend_analyzer.py  # Hot/cold topic detection, cycle detection',
      '├── test_predictor.py       # v1 prediction accuracy regression tests',
      '├── test_difficulty.py      # Difficulty classification correctness',
      '├── test_pattern_finder.py  # Pattern extraction from historical data',
      '└── test_e2e.py             # End-to-end pipeline smoke test',
    ]),
    spacer(120),
    note('Run with: pytest tests/ -v --tb=short. Tests run against the local exam.db SQLite file. No external services required.'),
    pageBreak(),
  ];
}

// ─── Section 9 — Security & Configuration ────────────────────────────────────
function buildSecurity() {
  return [
    sectionBanner(9, 'Security & Configuration'),
    spacer(200),
    heading2('9.1  API Security'),
    bullet('CORS  —  Allowed origins configured via CORS_ORIGINS env variable. Defaults to localhost:3000 and localhost:8080 in development. In production, set to the exact frontend domain.'),
    bullet('Rate limiting  —  REQUEST_TIMEOUT_SEC=90 per request. No global rate limiter in the current build; recommended addition before public deployment.'),
    bullet('Input validation  —  All request payloads validated by Pydantic schemas before reaching route handlers. Invalid input returns 422 Unprocessable Entity.'),
    bullet('Secrets  —  API keys (OPENAI_API_KEY, HF_TOKEN) loaded from environment variables via Pydantic Settings. Never hardcoded. .env files are gitignored.'),
    spacer(160),
    heading2('9.2  Data Privacy'),
    bullet('Student data  —  The CSV files (neet_results_v2.csv, jee_results_v2.csv) contain synthetic / anonymised records for testing. No real student PII is committed to the repository.'),
    bullet('Pre-computed summaries  —  docs/student_summary_neet.json and docs/student_summary_jee.json are generated artefacts. Real deployment should serve these from an authenticated endpoint, not as public static files.'),
    spacer(160),
    heading2('9.3  Dependency Summary'),
    spacer(80),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2400, 6960],
      rows: [
        tableHeaderRow(['Package', 'Role'], [2400, 6960]),
        ...([
          ['torch ≥ 2.0', 'PyTorch: SLM training & inference'],
          ['sentence-transformers ≥ 2.2', 'all-MiniLM-L6-v2 embeddings'],
          ['fastapi + uvicorn', 'Intelligence API server'],
          ['pydantic ≥ 2', 'Schema validation & settings management'],
          ['chromadb', 'Vector store for RAG retrieval'],
          ['pandas ≥ 2.0', 'Data manipulation, student CSV processing'],
          ['scikit-learn ≥ 1.3', 'Auxiliary ML utilities, metrics'],
          ['plotly ≥ 5.15', 'Interactive charts in Streamlit'],
          ['streamlit ≥ 1.28', 'Dashboard server'],
          ['fpdf2 ≥ 2.7', 'PDF report generation'],
          ['httpx + aiofiles', 'Async HTTP client (Ollama + OpenAI calls)'],
          ['pyngrok ≥ 7', 'Public ngrok tunnel for demo hosting'],
        ]).map(([a,b], i) => dataRow([a,b], [2400, 6960], i%2===0)),
      ],
    }),
    pageBreak(),
  ];
}

// ─── Section 10 — Roadmap ─────────────────────────────────────────────────────
function buildRoadmap() {
  const phases = [
    ['Phase 1', 'Foundation  (complete)', GREEN, GREEN_LT,
     'SQLite schema · question extraction pipeline · predictor_v1 · Streamlit v1 · PRAJNA SLM training'],
    ['Phase 2', 'Intelligence API  (complete)', TEAL, TEAL_LT,
     'FastAPI service · SLM provider abstraction · ChromaDB RAG · anti-hallucination guard · Pydantic schemas'],
    ['Phase 3', 'Student Personalisation  (complete)', PURPLE, PURPLE_LT,
     'Student analyser · priority score · static HTML dashboard · study guide · lazy detail cards · micro-topic cache'],
    ['Phase 4', 'Production Hardening  (in progress)', AMBER, AMBER_LT,
     'Redis caching · rate limiting · real student PII handling · authenticated API · monitoring / alerting · CI/CD'],
    ['Phase 5', 'Advanced Features  (planned)', '9333EA', 'F3E8FF',
     'Real-time exam-paper ingestion · SLM fine-tuning loop · collaborative filtering across students · mobile PWA'],
  ];

  return [
    sectionBanner(10, 'Product Roadmap'),
    spacer(200),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1400, 2400, 5560],
      rows: phases.map(([phase, status, clr, bg, items]) =>
        new TableRow({ children: [
          badgeCell(phase, clr, WHITE, 1400),
          new TableCell({
            width: { size: 2400, type: WidthType.DXA },
            borders: cellBorders(clr),
            shading: { fill: bg, type: ShadingType.CLEAR },
            margins: cellPad,
            children: [new Paragraph({
              children: [new TextRun({ text: status, font: 'Arial', size: 19, bold: true, color: clr })],
            })],
          }),
          new TableCell({
            width: { size: 5560, type: WidthType.DXA },
            borders: cellBorders(BORDER_CLR),
            shading: { fill: WHITE, type: ShadingType.CLEAR },
            margins: cellPad,
            children: [new Paragraph({
              children: [new TextRun({ text: items, font: 'Arial', size: 19, color: SLATE })],
            })],
          }),
        ]})
      ),
    }),
    spacer(240),
    note('Timeline: Phases 1–3 were completed across March 2026. Phase 4 target is Q2 2026. Phase 5 is a post-v1.0 roadmap item pending usage data from Phase 4 rollout.'),
    pageBreak(),
  ];
}

// ─── Build Document ───────────────────────────────────────────────────────────
async function main() {
  const children = [
    ...buildCoverPage(),
    // TOC placeholder
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 0, after: 120 },
      children: [new TextRun({ text: 'Table of Contents', font: 'Arial', size: 28, bold: true, color: DARK })],
    }),
    new TableOfContents('Table of Contents', { hyperlink: true, headingStyleRange: '1-3' }),
    pageBreak(),
    ...buildOverview(),
    ...buildHighLevel(),
    ...buildDataLayer(),
    ...buildPrediction(),
    ...buildIntelligence(),
    ...buildFrontend(),
    ...buildDeployment(),
    ...buildEval(),
    ...buildSecurity(),
    ...buildRoadmap(),
  ];

  const doc = new Document({
    numbering: {
      config: [{
        reference: 'bullets',
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: '•',
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }, {
          level: 1, format: LevelFormat.BULLET, text: '◦',
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } },
        }],
      }],
    },
    styles: {
      default: {
        document: { run: { font: 'Arial', size: 20 } },
      },
      paragraphStyles: [
        {
          id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 28, bold: true, font: 'Arial', color: DARK },
          paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
        },
        {
          id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 24, bold: true, font: 'Arial', color: PURPLE },
          paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 },
        },
        {
          id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 22, bold: true, font: 'Arial', color: TEAL },
          paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: PURPLE, space: 4 } },
            children: [
              new TextRun({ text: 'PRAJNA  ·  Technical Architecture Document', font: 'Arial', size: 17, color: '6B7280' }),
              new TextRun({ text: '   |   Confidential', font: 'Arial', size: 17, color: 'CBD5E1' }),
            ],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: BORDER_CLR, space: 4 } },
            children: [
              new TextRun({ text: '© 2026 PRAJNA Exam Intelligence Platform  ·  v1.0', font: 'Arial', size: 17, color: '9CA3AF' }),
              new TextRun({ text: '    Page ', font: 'Arial', size: 17, color: '6B7280' }),
              new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 17, color: PURPLE }),
            ],
          })],
        }),
      },
      children,
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = '/Users/aman/exam-predictor/docs/prajna-arch-doc.docx';
  fs.writeFileSync(outPath, buffer);
  console.log('Written:', outPath);
}

main().catch(err => { console.error(err); process.exit(1); });
