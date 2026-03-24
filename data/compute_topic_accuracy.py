#!/usr/bin/env python3
"""
Compute per-question, per-topic accuracy by cross-referencing:
1. Student responses (questions array from final_data_sheet.csv)
2. Answer keys (from answer_keys.json)
3. Topic mapping (from test_topic_mapping.json)

Outputs updated student profiles with true per-chapter accuracy.
"""
import csv, json, re, statistics
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def parse_questions_array(raw):
    """Parse the questions response string into a list of answers.
    Format: ["" "" "4" "" "" "3" "1" ...]
    Returns list of strings (answer option or empty string for blank).
    """
    if not raw or raw.strip() in ("", "[]"):
        return []
    # Remove outer brackets
    s = raw.strip()
    if s.startswith("["):
        s = s[1:]
    if s.endswith("]"):
        s = s[:-1]
    # Split by whitespace between quoted values
    answers = re.findall(r'"([^"]*)"', s)
    return answers


def load_answer_keys():
    """Load answer keys from extracted JSON."""
    path = BASE / "data" / "raw" / "answer_keys.json"
    with open(path) as f:
        data = json.load(f)
    # Index by test_name
    keys = {}
    for ak in data["answer_keys"]:
        keys[ak["test_name"]] = ak
    return keys


def load_topic_mapping():
    """Load topic mapping from extracted JSON."""
    path = BASE / "data" / "raw" / "test_topic_mapping.json"
    with open(path) as f:
        data = json.load(f)
    return data["tests"]


def load_test_metadata():
    """Load test metadata from question paper sheet."""
    path = BASE / "data" / "raw" / "question_paper_sheet.csv"
    with open(path) as f:
        tests = list(csv.DictReader(f))
    tid_meta = {}
    for t in tests:
        tid = t["Testid's"].strip()
        if not tid:
            continue
        stream = t["Class_Stream"].strip()
        exam = "NEET" if "NEET" in stream else "JEE"
        tid_meta[tid] = {
            "name": t["Test Name"].strip(),
            "stream": stream,
            "exam": exam,
        }
    return tid_meta


def match_topic_mapping(topic_maps, test_name, exam_type):
    """Find the topic mapping entry that best matches the test name.
    Handles exam_type variants: 'JEE' matches 'JEE Mains' and 'JEE Advanced'.
    """
    # Normalize exam type for matching
    def _exam_matches(tm_exam, target_exam):
        if tm_exam == target_exam:
            return True
        # JEE matches JEE Mains and JEE Advanced
        if target_exam == "JEE" and tm_exam in ("JEE Mains", "JEE Advanced"):
            return True
        return False

    def _name_score(test_name, tm_name):
        """Score how well two test names match."""
        t = test_name.lower().replace("-", " ").replace(":", " ").replace("(", " ").replace(")", " ")
        m = tm_name.lower().replace("-", " ").replace(":", " ").replace("(", " ").replace(")", " ")
        t_words = set(t.split())
        m_words = set(m.split())
        # Look for key identifiers: test numbers, paper numbers, pyq
        key_matches = 0
        for pattern in ["test 10", "test 11", "test 12", "test 13", "test 14",
                        "test 15", "test 16", "test 17", "test 01", "test 02",
                        "pyq 5", "pyq 6", "pyq 7", "full test", "paper 1", "paper 2",
                        "p 1", "p 2", "mains", "advance", "weekly", "revision",
                        "syllabus 01", "syllabus 02", "dropper"]:
            if pattern in t and pattern in m:
                key_matches += 2
        return len(t_words & m_words) + key_matches

    best_match = None
    best_score = 0
    for tm in topic_maps:
        if not _exam_matches(tm["exam_type"], exam_type):
            continue
        score = _name_score(test_name, tm["test_name"])
        if score > best_score and score >= 2:
            best_score = score
            best_match = tm
    return best_match


def question_to_topic(q_num, topic_mapping):
    """Given a question number and topic mapping, return (subject, topics_list).
    For tests with specific topic lists, returns the list of chapters.
    For 'Full Syllabus' tests, returns ['Full Syllabus'].
    """
    if not topic_mapping:
        return None, []
    for section_name, section in topic_mapping["sections"].items():
        q_start = section["q_start"]
        q_end = section["q_end"]
        if q_start <= q_num <= q_end:
            return section_name, section.get("topics", [])
    return None, []


def compute_per_topic_accuracy():
    """Main pipeline: compute per-student, per-topic accuracy."""
    print("Loading data...")
    answer_keys = load_answer_keys()
    topic_maps = load_topic_mapping()
    test_meta = load_test_metadata()

    print(f"  → {len(answer_keys)} answer keys")
    print(f"  → {len(topic_maps)} topic mappings")
    print(f"  → {len(test_meta)} test metadata entries")

    # Load student results
    path = BASE / "data" / "raw" / "final_data_sheet.csv"
    with open(path) as f:
        results = list(csv.DictReader(f))
    print(f"  → {len(results)} student result rows")

    # Process: for each student result, cross-reference responses × answer key × topics
    # Accumulate per-(userid, exam, chapter) → {correct, wrong, blank}
    student_chapter_stats = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "wrong": 0, "blank": 0}))
    student_exam = {}  # userid → exam_type
    student_erpid = {}  # userid → erpid
    matched = 0
    unmatched = 0

    for r in results:
        tid = r["testid"].strip()
        uid = r["userid"].strip()
        erpid = r["erpid"].strip()
        if not uid or not tid:
            continue

        meta = test_meta.get(tid)
        if not meta:
            continue

        test_name = meta["name"]
        exam_type = meta["exam"]
        student_exam[uid] = exam_type
        student_erpid[uid] = erpid

        # Find answer key
        ak = answer_keys.get(test_name)
        if not ak:
            unmatched += 1
            continue

        # Find topic mapping
        tm = match_topic_mapping(topic_maps, test_name, exam_type)

        # Parse student responses
        responses = parse_questions_array(r.get("questions", ""))
        if not responses:
            continue

        matched += 1
        correct_answers = ak["answers"]

        for i, student_ans in enumerate(responses):
            q_num = i + 1
            q_str = str(q_num)

            # Get correct answer
            correct = correct_answers.get(q_str, "")
            if not correct:
                continue

            # Get topic
            section_name = None
            topics = []
            if tm:
                section_name, topics = question_to_topic(q_num, tm)

            # Determine correctness
            student_ans_clean = student_ans.strip()
            if not student_ans_clean:
                status = "blank"
            elif student_ans_clean == correct:
                status = "correct"
            else:
                status = "wrong"

            # Assign to chapters
            # If specific topics are listed (not "Full Syllabus"), distribute across them
            chapters_to_credit = []
            if topics:
                non_full = [t for t in topics if not t.startswith("Full Syllabus")]
                if non_full:
                    chapters_to_credit = non_full
                elif section_name:
                    chapters_to_credit = [section_name]  # Use subject as fallback
            elif section_name:
                chapters_to_credit = [section_name]

            for ch in chapters_to_credit:
                student_chapter_stats[(uid, exam_type)][ch][status] += 1

    print(f"\n  Matched: {matched} result rows with answer keys")
    print(f"  Unmatched: {unmatched} result rows (no answer key)")
    print(f"  Unique students with chapter data: {len(student_chapter_stats)}")

    return student_chapter_stats, student_exam, student_erpid


def update_student_profiles(chapter_stats, student_exam, student_erpid):
    """Update the existing student profile JSONs with true per-chapter accuracy."""
    import sys
    sys.path.insert(0, str(BASE / "data"))
    from process_real_students import _level, _assign_name, _assign_center, PW_CITIES

    for exam_type in ["neet", "jee"]:
        path = BASE / "docs" / f"student_summary_{exam_type}.json"
        with open(path) as f:
            data = json.load(f)

        students = data["students"]
        updated = 0

        # Build reverse index: student_id → uid for this exam
        sid_to_uid = {}
        for uid, erpid in student_erpid.items():
            if student_exam.get(uid, "").lower() == exam_type:
                sid = f"STU{erpid[-6:]}" if len(erpid) >= 6 else f"STU{erpid}"
                sid_to_uid[sid] = uid

        for s in students:
            matching_uid = sid_to_uid.get(s["id"])
            if not matching_uid:
                continue

            key = (matching_uid, exam_type.upper())
            ch_stats = chapter_stats.get(key, {})
            if not ch_stats:
                continue

            # Build chapters dict: {chapter_name: [accuracy, level_letter, test_count]}
            chapters = {}
            for ch, stats in ch_stats.items():
                total = stats["correct"] + stats["wrong"]
                if total == 0:
                    continue
                acc = round(stats["correct"] / total * 100, 1)
                level = _level(acc)
                chapters[ch] = [acc, level[0], stats["correct"] + stats["wrong"] + stats["blank"]]

            if chapters:
                s["chapters"] = chapters
                # Update strengths (top 5 by accuracy)
                sorted_chs = sorted(chapters.items(), key=lambda x: x[1][0], reverse=True)
                s["strengths"] = [{"chapter": ch, "acc": d[0]} for ch, d in sorted_chs[:5]]
                # Update slm_focus (weakest with enough data)
                weak_chs = sorted(
                    [(ch, d) for ch, d in chapters.items() if d[2] >= 2],
                    key=lambda x: x[1][0]
                )
                s["slm_focus"] = [
                    {
                        "chapter": ch, "accuracy": d[0], "level": _level(d[0]),
                        "slm_importance": round(70 + (50 - d[0]) * 0.5, 1),
                        "slm_priority_score": round((100 - d[0]) * 0.6, 1),
                        "trend": 0, "consistency": d[2] * 5,
                    }
                    for ch, d in weak_chs[:5]
                ]
                updated += 1

        # Write back
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Also update student_data copy
        copy_path = BASE / "data" / "student_data" / f"student_summary_{exam_type}.json"
        with open(copy_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  {exam_type.upper()}: {updated}/{len(students)} students updated with per-question chapter accuracy")


def main():
    chapter_stats, student_exam, student_erpid = compute_per_topic_accuracy()
    print("\nUpdating student profiles...")
    update_student_profiles(chapter_stats, student_exam, student_erpid)
    print("\nDone! Per-question micro-topic accuracy integrated.")


if __name__ == "__main__":
    main()
