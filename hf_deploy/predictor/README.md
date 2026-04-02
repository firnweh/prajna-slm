---
license: apache-2.0
tags:
  - education
  - exam-prediction
  - neet
  - jee
language:
  - en
---

# PRAJNA v4 — Exam Prediction Engine

Predictive Resource Allocation for JEE/NEET Aspirants.

## Overview

PRAJNA v4 is a hierarchical exam prediction engine that predicts which topics will appear in upcoming NEET/JEE exams, using 48 years of historical exam data (23,119 questions).

## Architecture

- **10-signal appearance probability model** with hill-climbing optimized weights
- **Parent gate**: chapter-level prediction gates micro-topic scoring
- **Subject-balanced reranking** with exam-specific quotas
- **3-stage pipeline**: Appearance × Weightage × Format

## Signals

1. Recency-weighted frequency (exponential decay)
2. Appearance rate (fraction of years appeared)
3. Recent 3-year presence
4. Recent 5-year presence
5. Gap return probability (overdue topics)
6. Trend slope (10-year linear regression)
7. Cycle match (periodic reappearance)
8. Parent inheritance (chapter score passed to micro-topics)
9. Recency burst (dense recent appearances)
10. Dispersion (rewards consistent appearances)

## Performance

- **Chapter-level backtest (NEET, k=50)**: 94.4% precision, 75.0% coverage
- **Micro-topic level (NEET, k=100)**: Combined score 0.63
- **Backtest accuracy**: 91% (averaged across 2019-2023)

## Data

- 23,119 questions from 292 papers (1978-2026)
- 48 years of NEET + JEE Main + JEE Advanced
- 755 unique micro-topics across 143 chapters

## Usage

```python
from predictor_v3 import predict_chapters_v3, predict_microtopics_v3

# Chapter-level predictions
chapters = predict_chapters_v3("exam.db", target_year=2026, exam="neet", top_k=50)

# Micro-topic predictions
micros = predict_microtopics_v3("exam.db", target_year=2026, exam="neet", top_k=200)
```

## License

Apache 2.0
