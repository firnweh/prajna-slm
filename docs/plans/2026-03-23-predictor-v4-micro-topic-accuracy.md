# PRAJNA Predictor v4 — Micro-Topic Accuracy Engine
**Date:** 2026-03-23
**Status:** Approved
**Target:** Improve micro-topic combined backtest score from ~0.53 → ~0.70+

---

## Problem Statement

The current `predictor_v3.py` achieves strong chapter-level accuracy (94.4% precision, 0.822 combined) but weak micro-topic accuracy (~0.53 combined at k=100). Key root causes identified from backtest analysis:

1. **k=100 is structurally insufficient** — NEET 2022+ papers contain 200-220 unique micro-topics, making a ceiling of ~45% coverage at k=100 mathematically impossible to overcome.
2. **60 chronic misses have 4+ years of history** — the engine knows they exist but ranks them outside the cutoff due to poor relative scoring at the micro level.
3. **Same 7 signals used for both chapters and micro-topics** — micro-topic gap patterns are sparser and noisier; the chapter-level formula underweights recency and parent context.
4. **No conditional structure** — all 470 micro-topics compete globally instead of within their parent chapter's candidate pool.

### Baseline Scores (NEET, micro-level, k=100, avg 2019-2023)
| Metric | Current v3 |
|--------|-----------|
| Precision@100 | ~0.72 |
| Coverage@100 | ~0.42 |
| Heavy Recall | ~0.65 |
| **Combined** | **~0.53** |

---

## Architecture — Three Approaches Combined

```
┌─────────────────────────────────────────────────────────────┐
│  PRAJNA Predictor v4 — Micro-Topic Accuracy Engine          │
│                                                             │
│  Stage 1 (Approach C):  Chapter model (~94% precision)      │
│         ↓ top-K chapters with final_scores                  │
│  Stage 2 (Approach B):  3 new signals per micro-topic       │
│         • parent_inheritance  (chapter score passed down)   │
│         • recency_burst       (appeared 2-of-last-3 yrs)   │
│         • dispersion_penalty  (rewards dense appearances)   │
│         ↓ enriched 10-signal vector                         │
│  Stage 3 (Approach A):  Hill-climbing weight optimiser      │
│         • backtests 2015–2023, maximises combined score     │
│         • saves best weights → analysis/weights_cache.json  │
│         ↓ optimised weights applied at predict time         │
│  Output: ranked micro-topic list with P(appear|chapter)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Section 1 — Stage 1: Chapter Gate (Approach C)

`predict_chapters_v3()` is reused unchanged as Stage 1. Its output — a ranked list of chapters with `final_score` values — forms the parent context for Stage 2.

**Key change:** Micro-topics are now scored *conditionally within each predicted chapter's bucket*, not globally across all 470. This means:
- Candidate pool per chapter = ~5.6 micro-topics on average (vs 470 global)
- Relative ranking within a chapter uses denser, more meaningful data
- A micro can only appear in the output if its parent chapter is in the top-K chapters

Dynamic K: Chapter k is set to `min(top_k_chapters, 60)`. Micro k per chapter is allocated proportionally based on chapter weight.

---

## Section 2 — Stage 2: Three New Signals (Approach B)

Added to the existing 7 signals in `_appearance_probability_micro()`, a new variant of the signal function tuned for micro-topic sparsity:

### Signal 8: `parent_inheritance`
The chapter's `final_score` from Stage 1 is injected as a signal. Micro-topics inside high-confidence chapters get a structural boost.
```python
parent_inheritance = chapter_predictions[parent_chapter]["final_score"]  # 0-1
```
Weight: `0.15` (high — parent context is strongly predictive)

### Signal 9: `recency_burst`
Fraction of the last 3 years in which this micro-topic appeared. Stronger than the existing `recent_3yr` because it's calibrated against the parent chapter's recency, not the global pool.
```python
recency_burst = sum(1 for y in years_appeared if y >= max_year - 2) / 3.0
```
Weight: `0.12`

### Signal 10: `dispersion`
Rewards micro-topics that cluster 2-3 questions per appearance (high exam weight). Penalises thin 1-question appearances scattered across many years.
```python
avg_qs_when_present = total_questions / max(len(set(years_appeared)), 1)
dispersion = min(avg_qs_when_present / 3.0, 1.0)  # 3+ Qs/yr = max score
```
Weight: `0.10`

### Rebalanced starting weights (before optimisation)
| Signal | v3 weight | v4 starting weight |
|--------|-----------|-------------------|
| recency_freq | 0.25 | 0.20 |
| appearance_rate | 0.20 | 0.15 |
| recent_3yr | 0.15 | 0.10 |
| recent_5yr | 0.05 | 0.03 |
| gap_return | 0.15 | 0.10 |
| trend_slope | 0.12 | 0.05 |
| cycle_match | 0.08 | 0.05 |
| **parent_inheritance** | — | **0.15** |
| **recency_burst** | — | **0.12** |
| **dispersion** | — | **0.10** |

Weights are normalised to sum = 1.0 before use. These starting values are then handed to the optimiser.

---

## Section 3 — Stage 3: Weight Optimiser (Approach A)

### Algorithm: Coordinate-wise Hill Climbing
```
optimise_weights(db_path, exam, n_rounds=40):
  weights = v4_starting_weights  # seed from Section 2
  best_score = backtest_avg_combined(weights, years=2015–2023)

  for round in range(n_rounds):
    for each weight dimension w_i:
      for delta in [+0.05, -0.05]:
        candidate = perturb(weights, w_i, delta)
        normalise(candidate)  # ensure sum=1
        score = backtest_avg_combined(candidate, years=2015–2023)
        if score > best_score:
          weights = candidate
          best_score = score

  save weights → analysis/weights_cache.json
  return weights, best_score
```

**Validation split:** Optimiser trains on 2015–2021, validates on 2022–2023 (held out). This prevents overfitting to the training years.

**Runtime estimate:** 40 rounds × 10 signals × 2 deltas × 9 backtest years = ~720 prediction calls. Expected ~3-4 minutes.

**Cache loading:** `predictor_v4.py` calls `_load_weights()` at import time — reads `weights_cache.json` if present, otherwise uses v4 starting weights.

---

## Section 4 — Final Score Formula (also optimised)

The micro-topic `final_score` formula is also parameterised for the optimiser:

```python
final_score = (
    W_app  * appearance_probability +    # start: 0.40
    W_qs   * normalised_expected_qs +    # start: 0.25
    W_yld  * yield_bonus +               # start: 0.10
    W_cross* cross_score +               # start: 0.10
    W_par  * parent_inheritance +        # start: 0.15  ← new
)
# W_syl gate applied multiplicatively, not as additive term
```

These 5 final-score weights are also included in the optimisation search space.

---

## Section 5 — Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `analysis/predictor_v4.py` | **CREATE** | Full v4 pipeline: stage 1 → stage 2 → output |
| `analysis/weight_optimiser.py` | **CREATE** | Standalone optimiser script, saves weights_cache.json |
| `analysis/weights_cache.json` | **GENERATED** | Cached optimal weights, loaded at predict time |
| `intelligence/services/api/routers/data_bridge.py` | **UPDATE** | `/predict?level=micro` routes to v4 |
| `dashboard/app.py` | **UPDATE** | Show v4 combined score + improvement delta vs v3 |

`analysis/predictor_v3.py` — **UNCHANGED**

---

## Section 6 — Success Criteria

| Metric | Current (v3) | Target (v4) |
|--------|-------------|------------|
| Micro combined score (avg 2019-2023) | 0.530 | ≥ 0.680 |
| Micro coverage@200 (avg) | 0.649 | ≥ 0.720 |
| Micro heavy-topic recall | 0.650 | ≥ 0.750 |
| Chapter combined score (must not regress) | 0.822 | ≥ 0.820 |
| Optimiser runtime | — | ≤ 5 min |

---

## Open Questions / Risks

- **Overfitting risk:** Hill-climbing on 9 years can still overfit if delta steps are too large. Mitigation: use 2022-2023 as validation, not training.
- **k inflation:** Hierarchical scoring requires predicting chapter k first — if the chapter stage misses a chapter, all its micro-topics are excluded. Mitigation: use slightly higher chapter k (top 70 instead of 50) for the v4 micro path.
- **Name normalisation:** Micro-topic names in the DB have inconsistencies (same concept, different strings). The existing `CHAPTER_ALIASES` pattern should be extended to micro-topics for the most common aliases.
