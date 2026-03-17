from utils.db import get_questions_df
from analysis.trend_analyzer import detect_cycles


WEIGHTS = {
    "frequency_trend": 0.30,
    "cycle_match": 0.25,
    "gap_bonus": 0.20,
    "cross_exam": 0.15,
    "recency": 0.10,
}

# Years to exclude from training — we predict FOR these years, not FROM them
HOLDOUT_YEARS = {2024, 2025, 2026}


def predict_topics(db_path="data/exam.db", target_year=2026, exam=None):
    full_df = get_questions_df(db_path)

    # Training data: exclude holdout years so predictions aren't contaminated
    df = full_df[~full_df["year"].isin(HOLDOUT_YEARS)]
    if exam:
        df = df[df["exam"] == exam]
        full_df = full_df[full_df["exam"] == exam]

    if df.empty:
        return []

    all_micros = df.groupby(["topic", "micro_topic"]).agg(
        total_count=("year", "size"),
        years_list=("year", lambda x: sorted(x.unique())),
        last_year=("year", "max"),
        first_year=("year", "min"),
    ).reset_index()

    cycles = detect_cycles(db_path, exclude_years=HOLDOUT_YEARS)
    cycle_map = {c["micro_topic"]: c for c in cycles}

    max_year = df["year"].max()
    min_year = df["year"].min()
    year_span = max_year - min_year + 1

    # Cross-exam uses all data (no holdout needed for exam presence)
    cross_df = get_questions_df(db_path)
    cross_df = cross_df[~cross_df["year"].isin(HOLDOUT_YEARS)]

    predictions = []

    for _, row in all_micros.iterrows():
        reasons = []
        score = 0.0

        # 1. Frequency trend (based on training data only)
        freq = row["total_count"] / year_span
        freq_score = min(freq * 10, 1.0)
        score += WEIGHTS["frequency_trend"] * freq_score
        if freq_score > 0.5:
            reasons.append(f"High frequency: appeared {row['total_count']} times in {year_span} years (training data up to 2023)")

        # 2. Cycle match
        cycle_score = 0.0
        if row["micro_topic"] in cycle_map:
            cycle = cycle_map[row["micro_topic"]]
            cycle_len = cycle["estimated_cycle_years"]
            years_since = target_year - row["last_year"]
            if cycle_len > 0 and years_since % cycle_len == 0:
                cycle_score = 1.0
                reasons.append(f"Cycle match: appears every ~{cycle_len} years, due in {target_year}")
            elif cycle_len > 0 and abs(years_since % cycle_len) <= 1:
                cycle_score = 0.5
                reasons.append(f"Near cycle: ~{cycle_len}-year cycle, close to due")
        score += WEIGHTS["cycle_match"] * cycle_score

        # 3. Gap bonus (longer gap = higher chance of return)
        gap = target_year - row["last_year"]
        gap_score = min(gap / 10, 1.0) if gap >= 3 else 0.0
        score += WEIGHTS["gap_bonus"] * gap_score
        if gap >= 3:
            reasons.append(f"Gap bonus: not seen in {gap} years (last in training: {row['last_year']})")

        # 4. Cross-exam signal
        micro_df = cross_df[cross_df["micro_topic"] == row["micro_topic"]]
        exams_with_topic = micro_df["exam"].unique()
        cross_score = min(len(exams_with_topic) / 3, 1.0)
        score += WEIGHTS["cross_exam"] * cross_score
        if len(exams_with_topic) > 1:
            reasons.append(f"Cross-exam: appears in {', '.join(exams_with_topic)}")

        # 5. Recency (how recently it appeared in training data)
        recency = max(0, 1 - (gap / year_span))
        score += WEIGHTS["recency"] * recency

        if not reasons:
            reasons.append("Low signal — limited historical data")

        predictions.append({
            "topic": row["topic"],
            "micro_topic": row["micro_topic"],
            "score": round(score, 4),
            "total_appearances": row["total_count"],
            "last_appeared": row["last_year"],
            "training_years": f"{min_year}–{max_year}",
            "reasons": reasons,
        })

    predictions.sort(key=lambda x: x["score"], reverse=True)
    return predictions
