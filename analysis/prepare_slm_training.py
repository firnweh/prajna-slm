"""
Prepare training data for PRAJNA SLM fine-tuning.

Two datasets:
1. Stage 1: Question-solving (from qbg.db — 1.14M questions)
2. Stage 2: Prediction reasoning (from exam.db — 23K questions)

Output: JSONL files in data/slm_training/ for MLX LoRA fine-tuning.
Format: {"text": "<s>[INST] {question} [/INST] {answer}</s>"}
"""

import json
import os
import re
import sqlite3
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "slm_training"
QBG_DB = str(DATA_DIR / "qbg.db")
EXAM_DB = str(DATA_DIR / "exam.db")


def clean_html(text):
    """Strip HTML tags, keep LaTeX."""
    if not text:
        return ""
    text = re.sub(r'<math[^>]*>.*?</math>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-z]+;', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def build_stage1_data():
    """Stage 1: Question-solving conversations from qbg.db.

    Selects questions with good text_solutions (>50 chars, not just option numbers).
    Creates instruction-response pairs for fine-tuning.
    """
    print("Building Stage 1: Question-solving data...")
    conn = sqlite3.connect(QBG_DB)
    conn.row_factory = sqlite3.Row

    # Get questions with good solutions
    rows = conn.execute("""
        SELECT question_clean, answer_clean, text_solution, subject, difficulty, topic
        FROM questions
        WHERE text_solution IS NOT NULL
        AND LENGTH(text_solution) > 50
        AND text_solution NOT LIKE '%(1)%' OR LENGTH(text_solution) > 100
        ORDER BY RANDOM()
        LIMIT 100000
    """).fetchall()
    conn.close()

    examples = []
    for row in rows:
        question = clean_html(row["question_clean"])
        answer = clean_html(row["answer_clean"] or "")
        solution = clean_html(row["text_solution"])
        subject = row["subject"] or ""
        difficulty = row["difficulty"] or ""
        topic = row["topic"] or ""

        if not question or len(question) < 10:
            continue
        if not solution or len(solution) < 20:
            continue

        # Build the instruction
        meta = []
        if subject:
            meta.append(f"Subject: {subject}")
        if topic:
            meta.append(f"Topic: {topic}")
        if difficulty:
            meta.append(f"Difficulty: {difficulty}")
        meta_str = " | ".join(meta)

        instruction = f"{question}"
        if meta_str:
            instruction = f"[{meta_str}]\n{question}"

        # Build the response
        response_parts = []
        if answer:
            response_parts.append(f"**Answer:** {answer}")
        if solution:
            response_parts.append(f"\n**Explanation:**\n{solution}")

        response = "\n".join(response_parts)

        # Llama 3 chat format
        text = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are PRAJNA, an expert AI tutor for NEET and JEE exam preparation. Give clear, concise answers with proper mathematical notation using LaTeX. Always explain the reasoning step by step.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{response}<|eot_id|>"

        examples.append({"text": text})

    print(f"  Generated {len(examples)} examples")
    return examples


def build_stage2_data():
    """Stage 2: Prediction reasoning from exam.db.

    Creates examples that teach the model to reason about exam patterns:
    - Which topics appear frequently
    - Cyclical patterns (every N years)
    - Rising/declining trends
    - Expected question counts
    """
    print("Building Stage 2: Prediction reasoning data...")
    conn = sqlite3.connect(EXAM_DB)
    conn.row_factory = sqlite3.Row

    # Get topic statistics
    topics = conn.execute("""
        SELECT topic, subject,
               COUNT(*) as total_qs,
               COUNT(DISTINCT year) as years_appeared,
               MIN(year) as first_year,
               MAX(year) as last_year,
               GROUP_CONCAT(DISTINCT year) as all_years
        FROM questions
        WHERE topic IS NOT NULL AND topic != ''
        GROUP BY topic, subject
        HAVING COUNT(*) >= 3
        ORDER BY COUNT(*) DESC
    """).fetchall()
    conn.close()

    examples = []
    current_year = 2026

    for row in topics:
        topic = row["topic"]
        subject = row["subject"]
        total_qs = row["total_qs"]
        years_appeared = row["years_appeared"]
        first_year = row["first_year"]
        last_year = row["last_year"]
        all_years = row["all_years"]

        # Calculate derived signals
        year_range = current_year - first_year if first_year else 1
        appearance_rate = years_appeared / max(year_range, 1)
        avg_qs = total_qs / max(years_appeared, 1)
        gap_since_last = current_year - last_year if last_year else 999

        # Determine trend
        if last_year and last_year >= 2023:
            trend = "RISING" if years_appeared > year_range * 0.5 else "STABLE"
        elif gap_since_last > 5:
            trend = "COLD - may return soon" if total_qs > 10 else "DECLINING"
        else:
            trend = "STABLE"

        # Build prediction reasoning example
        instruction = f"Predict the likelihood of '{topic}' ({subject}) appearing in NEET/JEE 2026. Use historical data to justify your prediction."

        response = f"""**Topic:** {topic} ({subject})

**Historical Analysis:**
- Appeared in {years_appeared} out of {year_range} years ({appearance_rate:.0%} appearance rate)
- Total questions asked: {total_qs} (average {avg_qs:.1f} per appearance)
- First appeared: {first_year}, Last appeared: {last_year}
- Years since last appearance: {gap_since_last}

**Prediction for 2026:**
- Appearance probability: {"HIGH" if appearance_rate > 0.5 else "MEDIUM" if appearance_rate > 0.25 else "LOW"} ({appearance_rate:.0%})
- Expected questions: ~{avg_qs:.1f}
- Trend: {trend}

**Reasoning:** {"This topic has been consistently tested and appeared recently — highly likely to appear again." if appearance_rate > 0.5 and gap_since_last < 3 else "This topic has a moderate history but hasn't appeared recently — watch for potential return." if gap_since_last > 3 else "This topic appears occasionally — include in revision but don't over-prioritize."}"""

        text = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are PRAJNA, an exam prediction AI trained on 48 years of NEET/JEE exam data (23,000+ questions). Analyze historical patterns to predict which topics will appear in upcoming exams. Use data-driven reasoning with specific statistics.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{response}<|eot_id|>"

        examples.append({"text": text})

        # Also generate "which topics should I study" style questions
        if appearance_rate > 0.4:
            q2 = f"Should I study {topic} for {subject} in NEET 2026?"
            a2 = f"**Yes, definitely.** {topic} has appeared in {appearance_rate:.0%} of past exams with an average of {avg_qs:.1f} questions. It was last tested in {last_year}. {'Given its high frequency, this is a must-study topic.' if appearance_rate > 0.6 else 'It has moderate frequency but consistent presence — worth including in your revision.'}"

            text2 = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are PRAJNA, an exam prediction AI for NEET/JEE preparation. Give data-driven study advice based on historical exam patterns.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{q2}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{a2}<|eot_id|>"
            examples.append({"text": text2})

    print(f"  Generated {len(examples)} examples")
    return examples


def save_splits(examples, name, train_ratio=0.9, val_ratio=0.05):
    """Split into train/valid/test and save as JSONL."""
    random.shuffle(examples)
    n = len(examples)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    splits = {
        "train": examples[:train_end],
        "valid": examples[train_end:val_end],
        "test": examples[val_end:],
    }

    for split_name, data in splits.items():
        path = OUTPUT_DIR / name / f"{split_name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        print(f"  {split_name}: {len(data)} examples → {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Stage 1: Question-solving
    stage1 = build_stage1_data()
    save_splits(stage1, "stage1_questions")

    # Stage 2: Prediction reasoning
    stage2 = build_stage2_data()
    save_splits(stage2, "stage2_predictions")

    # Combined dataset for final training
    combined = stage1 + stage2
    random.shuffle(combined)
    save_splits(combined, "combined")

    print(f"\nTotal training examples: {len(combined)}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
