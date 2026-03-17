"""
Scrape JEE Main & Advanced questions from ExamSIDE's SvelteKit API.
Reuses the same deduplication format as the NEET scraper.

Usage:
    python extraction/scrape_jee.py                  # scrape all JEE papers
    python extraction/scrape_jee.py --main            # JEE Main only
    python extraction/scrape_jee.py --advanced        # JEE Advanced only

Output: JSON files in data/extracted/ (one per paper)
"""

import requests
import json
import os
import re
import time
import sys

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
OUTPUT_DIR = "data/extracted"

EXAMS = {
    "jee-main": {
        "base_url": "https://questions.examside.com/past-years/year-wise/jee/jee-main",
        "exam_label": "JEE Main",
    },
    "jee-advanced": {
        "base_url": "https://questions.examside.com/past-years/year-wise/jee/jee-advanced",
        "exam_label": "JEE Advanced",
    },
}


def clean_html(html):
    if not html or not isinstance(html, str):
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&#39;", "'").replace("&quot;", '"')
    return text.strip()


def resolve(data, idx):
    if isinstance(idx, int) and 0 <= idx < len(data):
        return data[idx]
    return idx


def format_slug(slug):
    if not slug or not isinstance(slug, str):
        return ""
    return slug.replace("-", " ").title()


def get_paper_keys(base_url):
    """Fetch all available paper keys from the exam listing page."""
    url = f"{base_url}/__data.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    nodes = r.json()["nodes"]
    d = nodes[1]["data"]

    keys = []
    for item in d:
        if isinstance(item, dict) and "key" in item and "year" in item:
            key = resolve(d, item["key"])
            keys.append(key)
    return keys


def get_question_ids(base_url, paper_key):
    """Fetch all question IDs for a paper from the listing page."""
    url = f"{base_url}/{paper_key}/__data.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    nodes = r.json()["nodes"]

    d = nodes[1]["data"]
    questions = []

    subjects_idx = d[0].get("questions")
    if subjects_idx is None:
        return []

    subjects_list = resolve(d, subjects_idx)
    if not isinstance(subjects_list, list):
        return []

    for subj_idx in subjects_list:
        subj = resolve(d, subj_idx)
        if isinstance(subj, dict) and "questions" in subj:
            q_indices = resolve(d, subj["questions"])
            if isinstance(q_indices, list):
                for qi in q_indices:
                    q = resolve(d, qi)
                    if isinstance(q, dict) and "question_id" in q:
                        qid = resolve(d, q["question_id"])
                        questions.append(qid)

    return questions


def extract_from_meta_and_content(d, meta, content_dict, exam_label):
    """Extract question data from metadata and content dicts."""
    subject = resolve(d, meta.get("subject", ""))
    chapter = resolve(d, meta.get("chapter", ""))
    topic = resolve(d, meta.get("topic", ""))
    year = resolve(d, meta.get("year", 0))
    q_type = resolve(d, meta.get("type", "mcq"))
    marks = resolve(d, meta.get("marks", 4))
    difficulty = resolve(d, meta.get("difficulty"))
    question_id = resolve(d, meta.get("question_id", ""))
    paper_key = resolve(d, meta.get("yearKey", ""))

    content_html = resolve(d, content_dict.get("content", ""))
    question_text = clean_html(content_html)

    options_list = resolve(d, content_dict.get("options", []))
    options = {}
    if isinstance(options_list, list):
        for opt_idx in options_list:
            opt = resolve(d, opt_idx)
            if isinstance(opt, dict):
                identifier = resolve(d, opt.get("identifier", ""))
                opt_content = resolve(d, opt.get("content", ""))
                options[identifier] = clean_html(opt_content)

    correct_ref = resolve(d, content_dict.get("correct_options", []))
    correct_options = []
    if isinstance(correct_ref, list):
        correct_options = [resolve(d, c) for c in correct_ref]

    q_type_mapped = "MCQ_single"
    if q_type == "mcq_multiple":
        q_type_mapped = "MCQ_multi"
    elif q_type in ("integer", "numerical"):
        q_type_mapped = "numerical"

    # Normalize exam label
    exam_tag = exam_label.replace(" ", "_")

    return {
        "id": f"{exam_tag}_{year}_{question_id}",
        "exam": exam_label,
        "year": year if isinstance(year, int) else 0,
        "shift": str(paper_key),
        "subject": format_slug(subject) if subject else "Unknown",
        "topic": format_slug(chapter) if chapter else "General",
        "micro_topic": format_slug(topic) if topic else format_slug(chapter),
        "question_text": question_text,
        "question_type": q_type_mapped,
        "difficulty": difficulty if isinstance(difficulty, int) else 3,
        "concepts_tested": [],
        "answer": ",".join(correct_options) if correct_options else "N/A",
        "marks": marks if isinstance(marks, int) else 4,
    }


def scrape_paper(base_url, paper_key, exam_label):
    """Scrape all questions for a single paper."""
    print(f"\n{'='*60}")
    print(f"Scraping: {paper_key} ({exam_label})")
    print(f"{'='*60}")

    try:
        question_ids = get_question_ids(base_url, paper_key)
    except Exception as e:
        print(f"  ERROR fetching listing: {e}")
        return []

    print(f"  Found {len(question_ids)} questions")

    if not question_ids:
        return []

    questions = []
    fetched_ids = set()

    for i, qid in enumerate(question_ids):
        if qid in fetched_ids:
            continue

        try:
            url = f"{base_url}/{paper_key}/{qid}/__data.json"
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            nodes = r.json()["nodes"]

            if len(nodes) > 2:
                d = nodes[2]["data"]

                for j, item in enumerate(d):
                    if isinstance(item, dict) and "question_id" in item and "chapter" in item and len(item) > 20:
                        this_qid = resolve(d, item["question_id"])
                        if this_qid in fetched_ids:
                            continue

                        question_ref = resolve(d, item.get("question"))
                        if isinstance(question_ref, dict) and "en" in question_ref:
                            content_dict = resolve(d, question_ref["en"])
                            if isinstance(content_dict, dict) and "content" in content_dict:
                                q = extract_from_meta_and_content(d, item, content_dict, exam_label)
                                if q and q["question_text"]:
                                    questions.append(q)
                                    fetched_ids.add(this_qid)

            time.sleep(0.5)

            if (i + 1) % 10 == 0:
                print(f"  Progress: {len(fetched_ids)}/{len(question_ids)} questions extracted")

        except Exception as e:
            print(f"  ERROR on question {qid}: {e}")
            time.sleep(1)

    print(f"  Total extracted: {len(questions)} questions")
    return questions


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Parse which exams to scrape
    scrape_main = True
    scrape_advanced = True
    if "--main" in sys.argv:
        scrape_advanced = False
    elif "--advanced" in sys.argv:
        scrape_main = False

    total_questions = 0

    for exam_key, exam_info in EXAMS.items():
        if exam_key == "jee-main" and not scrape_main:
            continue
        if exam_key == "jee-advanced" and not scrape_advanced:
            continue

        base_url = exam_info["base_url"]
        exam_label = exam_info["exam_label"]

        print(f"\n{'#'*60}")
        print(f"# {exam_label}")
        print(f"{'#'*60}")

        # Fetch all paper keys dynamically
        try:
            paper_keys = get_paper_keys(base_url)
            print(f"Found {len(paper_keys)} papers for {exam_label}")
        except Exception as e:
            print(f"ERROR fetching paper list for {exam_label}: {e}")
            continue

        for paper_key in paper_keys:
            output_file = os.path.join(OUTPUT_DIR, f"{paper_key}.json")

            if os.path.exists(output_file):
                with open(output_file) as f:
                    existing = json.load(f)
                print(f"\nSkipping {paper_key} — already have {len(existing)} questions")
                total_questions += len(existing)
                continue

            questions = scrape_paper(base_url, paper_key, exam_label)

            if questions:
                with open(output_file, "w") as f:
                    json.dump(questions, f, indent=2, ensure_ascii=False)
                print(f"  Saved to {output_file}")
                total_questions += len(questions)
            else:
                print(f"  No questions extracted for {paper_key}")

            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"DONE! Total JEE questions extracted: {total_questions}")
    print(f"Files saved in: {OUTPUT_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
