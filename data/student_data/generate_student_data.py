"""
PRAJNA – Synthetic Student Performance Dataset Generator
=========================================================
Generates realistic mock-exam performance data for 100 students across:
  • 10 NEET full-length mock exams  (85 topics)
  • 10 JEE Main full-length mock exams (84 topics)

Output files (in same directory):
  students.csv            – student profiles with latent ability
  neet_exam_results.csv   – topic-level rows, 100 × 10 × 85 = 85 000 rows
  neet_exam_summary.csv   – per-student per-exam totals + rank/percentile
  jee_exam_results.csv    – topic-level rows, 100 × 10 × 84 = 84 000 rows
  jee_exam_summary.csv    – per-student per-exam totals + rank/percentile
"""

import csv
import math
import os
import random
from pathlib import Path

# ── reproducibility ─────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

OUT_DIR = Path(__file__).parent

# ── topic lists ─────────────────────────────────────────────────────────────
NEET_TOPICS = {
    "Physics": [
        "Physical World & Measurement", "Kinematics", "Laws of Motion",
        "Work Energy & Power", "Rotational Motion", "Gravitation",
        "Properties of Solids & Liquids", "Thermodynamics",
        "Kinetic Theory of Gases", "Oscillations", "Waves",
        "Electrostatics", "Current Electricity", "Magnetic Effects of Current",
        "Magnetism & Matter", "Electromagnetic Induction",
        "Alternating Currents", "Electromagnetic Waves",
        "Ray Optics", "Wave Optics", "Dual Nature of Matter",
        "Atoms & Nuclei", "Electronic Devices", "Communication Systems",
    ],
    "Chemistry": [
        "Basic Concepts", "Atomic Structure", "Chemical Bonding",
        "States of Matter", "Thermodynamics (Chem)", "Equilibrium",
        "Redox Reactions", "Hydrogen", "s-Block Elements",
        "p-Block Elements (13&14)", "Organic Chemistry Basics",
        "Hydrocarbons", "Environmental Chemistry",
        "p-Block Elements (15-18)", "d & f Block Elements",
        "Coordination Compounds", "Haloalkanes & Haloarenes",
        "Alcohols Phenols Ethers", "Aldehydes Ketones",
        "Carboxylic Acids", "Amines", "Biomolecules",
        "Polymers", "Chemistry in Everyday Life",
        "Solid State", "Solutions", "Electrochemistry",
        "Chemical Kinetics", "Surface Chemistry",
    ],
    "Biology": [
        "The Living World", "Biological Classification",
        "Plant Kingdom", "Animal Kingdom", "Morphology of Flowering Plants",
        "Anatomy of Flowering Plants", "Structural Organisation in Animals",
        "Cell: Unit of Life", "Biomolecules", "Cell Cycle & Division",
        "Transport in Plants", "Mineral Nutrition", "Photosynthesis",
        "Respiration in Plants", "Plant Growth & Development",
        "Digestion & Absorption", "Breathing & Exchange of Gases",
        "Body Fluids & Circulation", "Excretory Products",
        "Locomotion & Movement", "Neural Control & Coordination",
        "Chemical Coordination", "Reproduction in Organisms",
        "Sexual Reproduction in Flowering Plants",
        "Human Reproduction", "Reproductive Health",
        "Principles of Inheritance", "Molecular Basis of Inheritance",
        "Evolution", "Human Health & Disease",
        "Strategies for Enhancement", "Microbes in Human Welfare",
        "Biotechnology Principles", "Biotechnology Applications",
        "Organisms & Populations", "Ecosystem",
        "Biodiversity & Conservation", "Environmental Issues",
    ],
}

JEE_TOPICS = {
    "Physics": [
        "Units & Measurement", "Kinematics 1D", "Kinematics 2D",
        "Laws of Motion", "Work Power Energy", "Centre of Mass",
        "Rotational Motion", "Gravitation", "Elasticity",
        "Fluid Mechanics", "Thermal Physics", "Kinetic Theory",
        "Oscillations (SHM)", "Wave Motion",
        "Electrostatics", "Capacitors", "Current Electricity",
        "Magnetic Force", "Magnetism", "Electromagnetic Induction",
        "AC Circuits", "EM Waves", "Ray Optics", "Wave Optics",
        "Modern Physics", "Semiconductor Devices",
    ],
    "Chemistry": [
        "Mole Concept", "Atomic Structure", "Chemical Bonding",
        "Gaseous State", "Thermodynamics", "Chemical Equilibrium",
        "Ionic Equilibrium", "Electrochemistry", "Chemical Kinetics",
        "Nuclear Chemistry", "s-Block", "p-Block",
        "d-Block", "Coordination Chemistry",
        "Isomerism", "Reaction Mechanisms", "Alkanes & Alkenes",
        "Alkynes & Aromatic", "Haloalkanes", "Alcohols & Ethers",
        "Carbonyl Compounds", "Carboxylic Acids & Derivatives",
        "Nitrogen Compounds", "Biomolecules & Polymers",
        "Analytical Chemistry", "Solid State & Solutions",
        "Surface Chemistry",
    ],
    "Mathematics": [
        "Sets Relations Functions", "Complex Numbers",
        "Quadratic Equations", "Progressions & Series",
        "Binomial Theorem", "Permutation & Combination",
        "Matrices & Determinants", "Straight Lines",
        "Circles", "Parabola", "Ellipse", "Hyperbola",
        "Trigonometric Functions", "Inverse Trigonometry",
        "Limits", "Continuity & Differentiability",
        "Differentiation", "Application of Derivatives",
        "Indefinite Integrals", "Definite Integrals",
        "Differential Equations", "Vectors",
        "3D Geometry", "Probability", "Statistics",
        "Mathematical Reasoning", "Linear Programming",
        "Height & Distance",
        "Mathematical Induction",
        "Relations & Functions Advanced",
        "Integration Applications",
    ],
}

# Flatten topic list preserving (subject, topic) pairs
def flatten_topics(topic_dict):
    result = []
    for subj, topics in topic_dict.items():
        for t in topics:
            result.append((subj, t))
    return result

NEET_FLAT = flatten_topics(NEET_TOPICS)   # 85 (subject, topic) pairs
JEE_FLAT  = flatten_topics(JEE_TOPICS)    # 83 (subject, topic) pairs

# Questions per topic per exam (realistic distribution by subject)
NEET_QS_PER_TOPIC = {
    "Physics": 2,
    "Chemistry": 2,
    "Biology": 2,
}
JEE_QS_PER_TOPIC = {
    "Physics": 3,
    "Chemistry": 3,
    "Mathematics": 4,
}

# Difficulty weight per topic index (cyclic mild variation)
def topic_difficulty(idx, total):
    """Returns a difficulty scalar 0.55–0.85 (higher = easier)."""
    base = 0.70
    wobble = 0.15 * math.sin(2 * math.pi * idx / max(total, 1))
    return max(0.55, min(0.85, base + wobble))

# ── student profiles ────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Aarav","Vivaan","Aditya","Vihaan","Arjun","Sai","Reyansh","Ayaan",
    "Krishna","Ishaan","Shaurya","Atharv","Advik","Pranav","Advait",
    "Dhruv","Kabir","Ritvik","Aarush","Arnav","Anaya","Diya","Saanvi",
    "Aanya","Aadhya","Avni","Riya","Meera","Navya","Kiara","Isha",
    "Priya","Neha","Shreya","Kavya","Anushka","Tanvi","Pooja","Divya",
    "Sneha","Rohan","Raj","Karan","Vikram","Rahul","Siddharth","Nikhil",
    "Tarun","Harsh","Dev","Mihir","Parth","Yash","Varun","Akash",
    "Naman","Shiv","Om","Lakshay","Gaurav","Deepak","Sumit","Rohit",
    "Aman","Ravi","Vijay","Suresh","Ajay","Amit","Pawan","Sandeep",
    "Ritesh","Ashish","Manish","Vishal","Pratik","Lokesh","Niraj","Sachin",
    "Ritu","Suman","Rekha","Geeta","Sunita","Savita","Lata","Sudha",
    "Meena","Usha","Anita","Seema","Vandana","Nisha","Mamta","Radha",
    "Puja","Pinki","Mona","Reena",
]
LAST_NAMES = [
    "Sharma","Verma","Singh","Kumar","Gupta","Mishra","Yadav","Tiwari",
    "Pandey","Dubey","Joshi","Patel","Shah","Mehta","Agarwal","Saxena",
    "Srivastava","Chaturvedi","Shukla","Tripathi","Rao","Reddy","Nair",
    "Pillai","Menon","Iyer","Krishnan","Subramaniam","Bhat","Kaur",
]

def generate_students(n=100):
    students = []
    used_names = set()
    for i in range(n):
        while True:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            name = f"{fn} {ln}"
            if name not in used_names:
                used_names.add(name)
                break
        # Latent ability per subject (0–1 scale, normally distributed)
        ability = {
            "Physics":     max(0.1, min(0.99, random.gauss(0.60, 0.18))),
            "Chemistry":   max(0.1, min(0.99, random.gauss(0.62, 0.16))),
            "Biology":     max(0.1, min(0.99, random.gauss(0.65, 0.15))),
            "Mathematics": max(0.1, min(0.99, random.gauss(0.55, 0.20))),
        }
        students.append({
            "student_id": f"STU{i+1:03d}",
            "name": name,
            "city": random.choice([
                "Delhi","Mumbai","Bangalore","Hyderabad","Chennai",
                "Kolkata","Jaipur","Lucknow","Pune","Ahmedabad",
                "Kota","Chandigarh","Patna","Bhopal","Indore",
            ]),
            "coaching": random.choice([
                "Allen Kota","FIITJEE","Aakash","Resonance",
                "Narayana","PACE","Vibrant","Self Study",
            ]),
            "target": random.choice(["NEET","JEE","Both"]),
            **{f"ability_{k.lower()}": round(v, 4) for k, v in ability.items()},
        })
    return students

# ── exam date schedules ──────────────────────────────────────────────────────
import datetime

def exam_dates(n_exams, start_year=2024, gap_days=18):
    base = datetime.date(start_year, 1, 15)
    return [(base + datetime.timedelta(days=i*gap_days)).isoformat()
            for i in range(n_exams)]

NEET_DATES = exam_dates(10)
JEE_DATES  = exam_dates(10, start_year=2024, gap_days=21)

# ── core simulation ──────────────────────────────────────────────────────────
def simulate_topic(student, subj_ability, exam_no, topic_idx, n_topics,
                   n_qs, marks_correct, marks_wrong, rng):
    """
    Simulate a single topic's performance for one student in one exam.
    Returns a dict of performance metrics.
    """
    # Learning growth: logarithmic improvement across 10 exams
    growth = 0.07 * math.log1p(exam_no - 1)

    # Exam-day random factor (±15% swing)
    day_factor = random.gauss(0.0, 0.08)

    # Topic difficulty (0.55–0.85, higher = easier topic)
    t_diff = topic_difficulty(topic_idx, n_topics)

    # Effective probability of getting a question correct
    p_correct = max(0.05, min(0.97,
        subj_ability * t_diff + growth + day_factor
    ))

    # Attempt rate: stronger students attempt more
    p_attempt = max(0.50, min(1.0,
        0.70 + 0.25 * subj_ability + 0.04 * (exam_no - 1) / 9
    ))

    attempted = max(0, int(round(n_qs * p_attempt +
                                  random.gauss(0, 0.3))))
    attempted = max(0, min(n_qs, attempted))

    not_attempted = n_qs - attempted

    # Among attempted, how many correct?
    correct = 0
    for _ in range(attempted):
        if random.random() < p_correct:
            correct += 1

    # Guard: correct cannot exceed attempted
    correct = min(correct, attempted)

    # Wrong = attempted - correct (guard against any rounding edge-case)
    wrong_total = max(0, attempted - correct)

    # Some wrong answers are "marked wrong" (attempted but flagged), rest just wrong
    marked_wrong = int(rng.binomial(wrong_total, 0.30)) if wrong_total > 0 else 0
    wrong = wrong_total  # all wrong attempted answers count for negative marking

    score = correct * marks_correct - wrong * marks_wrong
    max_score = n_qs * marks_correct

    accuracy_pct = round(100.0 * correct / attempted, 1) if attempted > 0 else 0.0

    # Estimated time spent (minutes): correct Qs take longer, unattempted = 0
    time_min = round(
        correct * random.gauss(1.8, 0.3) +
        wrong * random.gauss(2.5, 0.5) +
        (attempted - correct - wrong) * random.gauss(3.0, 0.6),
        1
    )
    time_min = max(0.0, time_min)

    return {
        "attempted": attempted,
        "correct": correct,
        "wrong": wrong,
        "not_attempted": not_attempted,
        "score": round(score, 1),
        "max_score": max_score,
        "accuracy_pct": accuracy_pct,
        "time_min": time_min,
    }

# ── NEET generation ──────────────────────────────────────────────────────────
def generate_neet(students, rng):
    results_rows = []
    summary_rows = []

    for exam_no in range(1, 11):
        exam_label = f"NEET Mock {exam_no:02d}"
        exam_date  = NEET_DATES[exam_no - 1]

        student_totals = {}

        for stu in students:
            sid   = stu["student_id"]
            sname = stu["name"]
            total_score = 0
            total_max   = 0

            for t_idx, (subj, topic) in enumerate(NEET_FLAT):
                n_qs = NEET_QS_PER_TOPIC.get(subj, 2)
                subj_ability = stu[f"ability_{subj.lower()}"]

                perf = simulate_topic(
                    stu, subj_ability, exam_no, t_idx,
                    len(NEET_FLAT), n_qs,
                    marks_correct=4, marks_wrong=1,
                    rng=rng,
                )

                results_rows.append({
                    "student_id": sid,
                    "name": sname,
                    "exam_no": exam_no,
                    "exam_date": exam_date,
                    "exam_label": exam_label,
                    "subject": subj,
                    "topic": topic,
                    "total_qs": n_qs,
                    "attempted": perf["attempted"],
                    "correct": perf["correct"],
                    "wrong": perf["wrong"],
                    "not_attempted": perf["not_attempted"],
                    "score": perf["score"],
                    "max_score": perf["max_score"],
                    "accuracy_pct": perf["accuracy_pct"],
                    "time_min": perf["time_min"],
                })

                total_score += perf["score"]
                total_max   += perf["max_score"]

            student_totals[sid] = {
                "student_id": sid,
                "name": sname,
                "exam_no": exam_no,
                "exam_date": exam_date,
                "exam_label": exam_label,
                "total_score": round(total_score, 1),
                "max_score": total_max,
                "percentage": round(100 * total_score / total_max, 2) if total_max else 0,
            }

        # Rank students within this exam (higher score = better rank)
        sorted_ids = sorted(student_totals.keys(),
                            key=lambda x: student_totals[x]["total_score"],
                            reverse=True)
        for rank, sid in enumerate(sorted_ids, 1):
            student_totals[sid]["rank"] = rank
            student_totals[sid]["percentile"] = round(
                100 * (len(students) - rank) / (len(students) - 1), 2
            )
            summary_rows.append(student_totals[sid])

        print(f"  NEET exam {exam_no:02d} done — {len(results_rows)} rows so far")

    return results_rows, summary_rows


# ── JEE generation ───────────────────────────────────────────────────────────
def generate_jee(students, rng):
    results_rows = []
    summary_rows = []

    for exam_no in range(1, 11):
        exam_label = f"JEE Main Mock {exam_no:02d}"
        exam_date  = JEE_DATES[exam_no - 1]

        student_totals = {}

        for stu in students:
            sid   = stu["student_id"]
            sname = stu["name"]
            total_score = 0
            total_max   = 0

            for t_idx, (subj, topic) in enumerate(JEE_FLAT):
                n_qs = JEE_QS_PER_TOPIC.get(subj, 3)
                key  = f"ability_{subj.lower()}"
                subj_ability = stu.get(key, stu["ability_physics"])  # fallback

                perf = simulate_topic(
                    stu, subj_ability, exam_no, t_idx,
                    len(JEE_FLAT), n_qs,
                    marks_correct=4, marks_wrong=1,
                    rng=rng,
                )

                results_rows.append({
                    "student_id": sid,
                    "name": sname,
                    "exam_no": exam_no,
                    "exam_date": exam_date,
                    "exam_label": exam_label,
                    "subject": subj,
                    "topic": topic,
                    "total_qs": n_qs,
                    "attempted": perf["attempted"],
                    "correct": perf["correct"],
                    "wrong": perf["wrong"],
                    "not_attempted": perf["not_attempted"],
                    "score": perf["score"],
                    "max_score": perf["max_score"],
                    "accuracy_pct": perf["accuracy_pct"],
                    "time_min": perf["time_min"],
                })

                total_score += perf["score"]
                total_max   += perf["max_score"]

            student_totals[sid] = {
                "student_id": sid,
                "name": sname,
                "exam_no": exam_no,
                "exam_date": exam_date,
                "exam_label": exam_label,
                "total_score": round(total_score, 1),
                "max_score": total_max,
                "percentage": round(100 * total_score / total_max, 2) if total_max else 0,
            }

        sorted_ids = sorted(student_totals.keys(),
                            key=lambda x: student_totals[x]["total_score"],
                            reverse=True)
        for rank, sid in enumerate(sorted_ids, 1):
            student_totals[sid]["rank"] = rank
            student_totals[sid]["percentile"] = round(
                100 * (len(students) - rank) / (len(students) - 1), 2
            )
            summary_rows.append(student_totals[sid])

        print(f"  JEE exam {exam_no:02d} done — {len(results_rows)} rows so far")

    return results_rows, summary_rows


# ── CSV helpers ──────────────────────────────────────────────────────────────
def write_csv(rows, path):
    if not rows:
        print(f"  [WARN] No rows for {path}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows):,} rows → {path.name}")


# ── main ─────────────────────────────────────────────────────────────────────
class SimpleRNG:
    """Minimal RNG wrapper that exposes .binomial() using stdlib random."""
    def binomial(self, n, p):
        """Draw from Binomial(n, p) using stdlib Bernoulli trials."""
        n = int(n)
        if n <= 0:
            return 0
        p = float(max(0.0, min(1.0, p)))
        return sum(1 for _ in range(n) if random.random() < p)


def main():
    print("PRAJNA – Synthetic Student Data Generator")
    print(f"  NEET topics : {len(NEET_FLAT)}")
    print(f"  JEE topics  : {len(JEE_FLAT)}")

    rng = SimpleRNG()

    print("\nGenerating 100 student profiles …")
    students = generate_students(100)
    write_csv(students, OUT_DIR / "students.csv")

    print(f"\nGenerating NEET mock results …")
    neet_res, neet_sum = generate_neet(students, rng)
    write_csv(neet_res, OUT_DIR / "neet_exam_results.csv")
    write_csv(neet_sum, OUT_DIR / "neet_exam_summary.csv")

    print(f"\nGenerating JEE Main mock results …")
    jee_res, jee_sum = generate_jee(students, rng)
    write_csv(jee_res,  OUT_DIR / "jee_exam_results.csv")
    write_csv(jee_sum,  OUT_DIR / "jee_exam_summary.csv")

    print("\n✓ All done!")
    print(f"  NEET results rows : {len(neet_res):,}")
    print(f"  JEE results rows  : {len(jee_res):,}")
    print(f"  Files written to  : {OUT_DIR}")


if __name__ == "__main__":
    main()
