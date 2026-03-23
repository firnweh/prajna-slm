"""
Compare predictor v3 vs v4 micro-topic combined scores across 2019-2023.
Run: python3 -m analysis.backtest_v4 --exam NEET --k 200
"""
import argparse
import numpy as np
import analysis.predictor_v4 as v4_mod
import analysis.predictor_v3 as v3_mod
from utils.db import get_questions_df

DB = "data/exam.db"


def _score_preds(preds, actual_df, k):
    pred_micros = set(p["micro_topic"] for p in preds[:k])
    actual_micros = set(actual_df["micro_topic"].unique())
    qs_map = actual_df.groupby("micro_topic").size().to_dict()
    total = len(actual_df)
    heavy = {m for m, q in qs_map.items() if q >= 3}

    hits     = pred_micros & actual_micros
    precision = len(hits) / k
    coverage  = sum(qs_map.get(m, 0) for m in hits) / total
    heavy_r   = len(hits & heavy) / len(heavy) if heavy else 0

    subj_qs = actual_df.groupby("subject").size().to_dict()
    pred_subj = {}
    for m in hits:
        qs = qs_map.get(m, 0)
        s_series = actual_df[actual_df["micro_topic"] == m]["subject"].mode()
        if len(s_series):
            pred_subj[s_series.iloc[0]] = pred_subj.get(s_series.iloc[0], 0) + qs
    avg_sc = np.mean([pred_subj.get(s, 0) / q for s, q in subj_qs.items()]) if subj_qs else 0

    return {
        "precision": round(precision, 3),
        "coverage":  round(coverage, 3),
        "heavy_r":   round(heavy_r, 3),
        "avg_sc":    round(avg_sc, 3),
        "combined":  round(0.35 * precision + 0.40 * coverage + 0.15 * heavy_r + 0.10 * avg_sc, 3),
    }


def run_comparison(exam="NEET", test_years=None, k=200):
    if test_years is None:
        test_years = [2019, 2020, 2021, 2022, 2023]

    full_df = get_questions_df(DB)
    if exam:
        full_df = full_df[full_df["exam"] == exam]

    orig_holdout_v4 = v4_mod.HOLDOUT_YEARS
    orig_holdout_v3 = v3_mod.HOLDOUT_YEARS
    print(f"\n{'Year':<6} {'v3_comb':>9} {'v4_comb':>9} {'delta':>8}  coverage_v3  coverage_v4")
    print("-" * 60)

    v3_all, v4_all = [], []

    for yr in test_years:
        actual = full_df[full_df["year"] == yr]
        if actual.empty:
            continue

        holdout = set(range(yr, 2030))
        v4_mod.HOLDOUT_YEARS = holdout
        v3_mod.HOLDOUT_YEARS = holdout
        try:
            from analysis.predictor_v3 import predict_microtopics_v3
            p_v3 = predict_microtopics_v3(DB, target_year=yr, exam=exam, top_k=k)
            from analysis.predictor_v4 import predict_microtopics_v4
            p_v4 = predict_microtopics_v4(DB, target_year=yr, exam=exam, top_k=k)
        finally:
            v4_mod.HOLDOUT_YEARS = orig_holdout_v4
            v3_mod.HOLDOUT_YEARS = orig_holdout_v3

        s3 = _score_preds(p_v3, actual, k)
        s4 = _score_preds(p_v4, actual, k)
        delta = s4["combined"] - s3["combined"]
        print(f"{yr:<6} {s3['combined']:>9.3f} {s4['combined']:>9.3f} {delta:>+8.3f}  "
              f"{s3['coverage']:>11.3f}  {s4['coverage']:>11.3f}")
        v3_all.append(s3["combined"])
        v4_all.append(s4["combined"])

    print("-" * 60)
    print(f"{'AVG':<6} {np.mean(v3_all):>9.3f} {np.mean(v4_all):>9.3f} "
          f"{np.mean(v4_all)-np.mean(v3_all):>+8.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exam", default="NEET")
    parser.add_argument("--k", type=int, default=200)
    args = parser.parse_args()
    run_comparison(exam=args.exam, k=args.k)
