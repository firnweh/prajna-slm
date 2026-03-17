import pandas as pd
from itertools import combinations
from utils.db import get_questions_df


def topic_cooccurrence(db_path="data/exam.db"):
    df = get_questions_df(db_path)
    all_micros = df["micro_topic"].unique()
    cooccur = pd.DataFrame(0, index=all_micros, columns=all_micros)

    for (exam, year, shift), group in df.groupby(["exam", "year", "shift"]):
        micros = group["micro_topic"].unique()
        for a, b in combinations(micros, 2):
            cooccur.loc[a, b] += 1
            cooccur.loc[b, a] += 1

    return cooccur


def subject_weightage_over_time(db_path="data/exam.db", exam=None):
    df = get_questions_df(db_path)
    if exam:
        df = df[df["exam"] == exam]
    counts = df.groupby(["year", "subject"]).size().unstack(fill_value=0)
    totals = counts.sum(axis=1)
    weights = counts.div(totals, axis=0)
    return weights


def cross_exam_correlation(db_path="data/exam.db"):
    df = get_questions_df(db_path)
    results = []

    for micro_topic in df["micro_topic"].unique():
        subset = df[df["micro_topic"] == micro_topic]
        exams = subset["exam"].unique()
        if len(exams) < 2:
            continue

        for exam_a in exams:
            for exam_b in exams:
                if exam_a == exam_b:
                    continue
                years_a = sorted(subset[subset["exam"] == exam_a]["year"].unique())
                years_b = sorted(subset[subset["exam"] == exam_b]["year"].unique())

                for ya in years_a:
                    for yb in years_b:
                        lag = yb - ya
                        if 0 < lag <= 3:
                            results.append({
                                "micro_topic": micro_topic,
                                "from_exam": exam_a,
                                "to_exam": exam_b,
                                "from_year": ya,
                                "to_year": yb,
                                "lag_years": lag,
                            })

    results.sort(key=lambda x: x["lag_years"])
    return results
