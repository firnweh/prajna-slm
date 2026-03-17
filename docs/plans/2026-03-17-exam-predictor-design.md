# Exam Predictor — Design Document

**Date:** 2026-03-17
**Goal:** Build a local system that analyzes 40 years of JEE & NEET question papers to find trends, classify difficulty, detect patterns, and predict likely topics for upcoming exams.

## Constraints

- Timeline: A few days
- Budget: Free/minimal (free tiers only)
- Skill level: Beginner — system must be learnable and simple
- No ongoing API costs — one-time LLM extraction, then fully offline

## Architecture

```
PDFs/Text → Claude/ChatGPT (one-time) → Structured JSON → SQLite → Analysis Engine → Streamlit Dashboard
```

## Data Pipeline

### Scope
- JEE Main (2002–2025): ~23 years
- JEE Advanced / IIT-JEE (1985–2025): ~40 years
- NEET / AIPMT (1988–2025): ~37 years
- Estimated total: 5,000–8,000 unique questions

### Extraction
One-time use of Claude/ChatGPT to extract structured JSON per question:

```json
{
  "exam": "JEE Advanced",
  "year": 2019,
  "shift": "Paper 1",
  "subject": "Physics",
  "topic": "Electromagnetism",
  "micro_topic": "Faraday's Law of Induction",
  "question_text": "A conducting loop of area...",
  "question_type": "MCQ_single",
  "difficulty": 3,
  "concepts_tested": ["Faraday's law", "Lenz's law", "induced EMF"],
  "similar_to": ["JEE2015_P1_Q12", "JEE2008_Q34"],
  "answer": "B",
  "marks": 3
}
```

### Storage
SQLite database (`exam.db`) with tables:
- `questions` — core question data
- `topics` — subject → topic → micro_topic hierarchy
- `patterns` — computed trends and repetitions

## Analysis Engine

### Module 1: Trend Analyzer
- Topic frequency over time
- Repetition detector (conceptually identical questions across years)
- Cycle detection via time-series autocorrelation
- Hot/cold topic identification

### Module 2: Difficulty Classifier
- Scikit-learn Random Forest using features: marks, topic complexity, question type, year
- Outputs difficulty score 1–5
- Clusters into easy / moderate / hard / very hard

### Module 3: Pattern Finder
- Topic co-occurrence analysis
- Subject distribution shifts over decades
- Question style evolution tracking
- Cross-exam correlation (JEE ↔ NEET)

### Module 4: Predictor
Weighted scoring model (no neural network):

```
prediction_score = (trend_weight × frequency_trend)
                 + (cycle_weight × cycle_match)
                 + (gap_weight × years_since_last)
                 + (cross_exam_weight × appeared_in_other_exam)
```

Outputs ranked list of top micro_topics most likely to appear next.

## Dashboard (Streamlit)

1. **Topic Heatmap** — micro_topics × years, color = frequency
2. **Predictions** — ranked table with reasoning, filterable by subject/difficulty/exam
3. **Question Explorer** — search/filter all questions, see similar questions grouped
4. **Smart Practice Sets** — auto-generated sets weighted by prediction scores, exportable as PDF

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Data extraction | Claude/ChatGPT (one-time) | Free tier |
| Database | SQLite | Free |
| Analysis engine | Python + Pandas + Scikit-learn | Free |
| Visualization | Matplotlib + Plotly | Free |
| Dashboard | Streamlit | Free |
| Hosting (optional) | Streamlit Community Cloud | Free |

## Project Structure

```
exam-predictor/
├── data/
│   ├── raw/              # Pasted paper text files
│   ├── extracted/        # JSON from Claude extraction
│   └── exam.db           # SQLite database
├── extraction/
│   └── prompt_template.md  # The prompt to use with Claude
├── analysis/
│   ├── trend_analyzer.py
│   ├── difficulty_classifier.py
│   ├── pattern_finder.py
│   └── predictor.py
├── dashboard/
│   └── app.py            # Streamlit app
├── utils/
│   ├── db.py             # Database helpers
│   └── loader.py         # JSON → SQLite loader
└── requirements.txt
```
