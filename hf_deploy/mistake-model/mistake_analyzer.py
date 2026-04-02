"""
PRAJNA Mistake Analyzer — Center View Aggregations
===================================================
"""
import pandas as pd
import numpy as np


class MistakeAnalyzer:
    def __init__(self, results_df: pd.DataFrame):
        self.df = results_df

    def error_rates(self, group_by=None):
        cols = ["micro_topic", "subject"]
        if group_by:
            cols.append(group_by)
        g = self.df.groupby(cols, as_index=False).agg(
            total_wrong=("wrong", "sum"),
            total_qs=("total_qs", "sum"),
            student_count=("student_id", "nunique"),
        )
        g["error_rate"] = (g["total_wrong"] / g["total_qs"]).clip(0, 1)
        return g.sort_values("error_rate", ascending=False).reset_index(drop=True)

    def danger_zones(self, prajna_probs: dict, error_threshold=0.4, top_n=15):
        er = self.error_rates()
        er["prajna_prob"] = er["micro_topic"].map(prajna_probs).fillna(0)
        er["danger_score"] = er["error_rate"] * er["prajna_prob"]
        dz = er[er["error_rate"] >= error_threshold].copy()
        dz = dz.sort_values("danger_score", ascending=False).head(top_n)
        return dz.reset_index(drop=True)

    def cofailure_pairs(self, fail_threshold=50, min_students=2, top_n=15):
        agg = self.df.groupby(["student_id", "micro_topic"], as_index=False).agg(
            acc=("accuracy_pct", "mean")
        )
        agg["failed"] = (agg["acc"] < fail_threshold).astype(int)
        pivot = agg.pivot_table(index="student_id", columns="micro_topic",
                                values="failed", fill_value=0)
        topics = list(pivot.columns)
        pairs = []
        for i, a in enumerate(topics):
            fails_a = pivot[a].sum()
            if fails_a < min_students:
                continue
            for b in topics[i + 1:]:
                both = ((pivot[a] == 1) & (pivot[b] == 1)).sum()
                if both < min_students:
                    continue
                p_b_given_a = both / fails_a
                fails_b = pivot[b].sum()
                p_a_given_b = both / fails_b if fails_b else 0
                pairs.append({
                    "topic_a": a, "topic_b": b,
                    "cofailure_pct": round(max(p_b_given_a, p_a_given_b) * 100, 1),
                    "both_fail_count": int(both),
                })
        pairs.sort(key=lambda x: x["cofailure_pct"], reverse=True)
        return pairs[:top_n]

    def time_vs_accuracy(self):
        g = self.df.groupby(["micro_topic", "subject"], as_index=False).agg(
            avg_time=("time_min", "mean"),
            avg_accuracy=("accuracy_pct", "mean"),
            student_count=("student_id", "nunique"),
        )
        return g.sort_values("avg_accuracy").reset_index(drop=True)
