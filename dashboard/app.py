import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_questions_df, get_topics_hierarchy
from analysis.trend_analyzer import topic_frequency_by_year, find_hot_cold_topics, detect_cycles
from analysis.difficulty_classifier import classify_difficulty, difficulty_over_time
from analysis.pattern_finder import topic_cooccurrence, subject_weightage_over_time
from analysis.predictor import predict_topics

DB_PATH = "data/exam.db"

st.set_page_config(page_title="Exam Predictor", page_icon="📊", layout="wide")
st.title("Exam Predictor — JEE & NEET Analysis")

if not os.path.exists(DB_PATH):
    st.error("Database not found. Run the loader first: python run.py")
    st.stop()

df = get_questions_df(DB_PATH)

# Sidebar filters
st.sidebar.header("Filters")
exams = ["All"] + sorted(df["exam"].unique().tolist())
selected_exam = st.sidebar.selectbox("Exam", exams)
subjects = ["All"] + sorted(df["subject"].unique().tolist())
selected_subject = st.sidebar.selectbox("Subject", subjects)

filtered = df.copy()
if selected_exam != "All":
    filtered = filtered[filtered["exam"] == selected_exam]
if selected_subject != "All":
    filtered = filtered[filtered["subject"] == selected_subject]

st.sidebar.metric("Total Questions", len(filtered))
st.sidebar.metric("Year Range", f"{filtered['year'].min()}–{filtered['year'].max()}")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "Topic Heatmap", "Predictions", "Question Explorer", "Practice Sets"
])

exam_filter = selected_exam if selected_exam != "All" else None

with tab1:
    st.header("Topic Frequency Heatmap")
    freq = topic_frequency_by_year(DB_PATH, exam=exam_filter)
    if selected_subject != "All":
        subject_topics = df[df["subject"] == selected_subject][["topic", "micro_topic"]].drop_duplicates()
        valid_idx = [idx for idx in freq.index if idx in list(zip(subject_topics["topic"], subject_topics["micro_topic"]))]
        freq = freq.loc[valid_idx] if valid_idx else freq

    if not freq.empty:
        fig = px.imshow(
            freq.values,
            labels=dict(x="Year", y="Topic", color="Questions"),
            x=[str(c) for c in freq.columns],
            y=[f"{t} > {m}" for t, m in freq.index],
            color_continuous_scale="YlOrRd",
            aspect="auto",
        )
        fig.update_layout(height=max(400, len(freq) * 25))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Hot & Cold Topics")
    col1, col2 = st.columns(2)
    hot, cold = find_hot_cold_topics(DB_PATH, recent_years=3)
    with col1:
        st.markdown("**Hot Topics** (frequent recently)")
        for topic_idx, micro, count in hot[:15]:
            st.write(f"- **{micro}** ({count} times in last 3 years)")
    with col2:
        st.markdown("**Cold Topics** (dormant)")
        for topic_idx, micro, gap in cold[:15]:
            st.write(f"- **{micro}** (last seen {gap} years ago)")

    st.subheader("Cyclical Topics")
    cycles = detect_cycles(DB_PATH)
    if cycles:
        cycle_df = pd.DataFrame(cycles)
        st.dataframe(cycle_df[["topic", "micro_topic", "estimated_cycle_years", "avg_gap", "consistency"]])

with tab2:
    st.header("Topic Predictions")
    target_year = st.number_input("Predict for year", value=2026, min_value=2024, max_value=2030)
    predictions = predict_topics(
        DB_PATH,
        target_year=target_year,
        exam=exam_filter,
    )
    top_n = st.slider("Show top N predictions", 10, 100, 50)

    pred_df = pd.DataFrame(predictions[:top_n])
    if not pred_df.empty:
        fig = px.bar(
            pred_df, x="score", y="micro_topic", orientation="h",
            color="score", color_continuous_scale="Viridis",
            title=f"Top {top_n} Predicted Topics for {target_year}",
        )
        fig.update_layout(height=max(400, top_n * 25), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        for _, row in pred_df.iterrows():
            with st.expander(f"{row['micro_topic']} (score: {row['score']})"):
                st.write(f"**Topic:** {row['topic']}")
                st.write(f"**Total appearances:** {row['total_appearances']}")
                st.write(f"**Last appeared:** {row['last_appeared']}")
                st.write("**Reasons:**")
                for reason in row["reasons"]:
                    st.write(f"- {reason}")

with tab3:
    st.header("Question Explorer")
    search = st.text_input("Search questions", "")
    col1, col2 = st.columns(2)
    with col1:
        topic_filter = st.selectbox("Topic", ["All"] + sorted(filtered["topic"].unique().tolist()))
    with col2:
        diff_filter = st.selectbox("Difficulty", ["All", 1, 2, 3, 4, 5])

    explorer_df = filtered.copy()
    if search:
        explorer_df = explorer_df[
            explorer_df["question_text"].str.contains(search, case=False, na=False)
            | explorer_df["micro_topic"].str.contains(search, case=False, na=False)
        ]
    if topic_filter != "All":
        explorer_df = explorer_df[explorer_df["topic"] == topic_filter]
    if diff_filter != "All":
        explorer_df = explorer_df[explorer_df["difficulty"] == diff_filter]

    st.write(f"Showing {len(explorer_df)} questions")
    st.dataframe(
        explorer_df[["id", "exam", "year", "subject", "topic", "micro_topic", "difficulty", "question_type"]],
        use_container_width=True,
    )

    if not explorer_df.empty:
        st.subheader("Difficulty Distribution")
        fig = px.histogram(explorer_df, x="difficulty", nbins=5, color="subject")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Questions Per Year")
        fig = px.histogram(explorer_df, x="year", color="subject")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Smart Practice Sets")
    mode = st.selectbox("Mode", [
        "High Probability Topics",
        "Dormant Topics (Surprise Factor)",
        "Full Balanced Mock",
    ])
    num_questions = st.slider("Number of questions", 10, 90, 30)

    if st.button("Generate Practice Set"):
        if mode == "High Probability Topics":
            preds = predict_topics(DB_PATH, target_year=2026)
            top_micros = [p["micro_topic"] for p in preds[:20]]
            pool = filtered[filtered["micro_topic"].isin(top_micros)]
            practice = pool.sample(n=min(num_questions, len(pool)), random_state=42)
        elif mode == "Dormant Topics (Surprise Factor)":
            _, cold = find_hot_cold_topics(DB_PATH, recent_years=5)
            cold_micros = [c[1] for c in cold[:20]]
            pool = filtered[filtered["micro_topic"].isin(cold_micros)]
            practice = pool.sample(n=min(num_questions, len(pool)), random_state=42)
        else:
            practice = filtered.sample(n=min(num_questions, len(filtered)), random_state=42)

        st.dataframe(
            practice[["id", "exam", "year", "subject", "topic", "micro_topic", "difficulty", "question_text"]],
            use_container_width=True,
        )

        export_text = ""
        for i, (_, row) in enumerate(practice.iterrows(), 1):
            export_text += f"Q{i}. [{row['exam']} {row['year']}] [{row['micro_topic']}] (Difficulty: {row['difficulty']})\n"
            export_text += f"{row['question_text']}\n"
            export_text += f"Answer: {row['answer']}\n\n"

        st.download_button("Download Practice Set", export_text, "practice_set.txt", "text/plain")
