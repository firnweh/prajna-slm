"""
Label qbg.db questions with topic taxonomy using keyword matching.
Extracts topic keywords from NEET/JEE syllabus and matches against question_clean text.
"""

import sqlite3
import re
import time
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent.parent
QBG_DB = str(BASE / "data" / "qbg.db")

TOPIC_KEYWORDS = {
    "Kinematics": ["kinematics", "velocity", "acceleration", "projectile", "displacement", "uniform motion", "relative motion", "free fall"],
    "Laws of Motion": ["newton", "force", "friction", "inertia", "momentum", "impulse", "tension", "normal force", "free body"],
    "Work Energy Power": ["work done", "kinetic energy", "potential energy", "conservation of energy", "power", "work-energy theorem", "conservative force"],
    "Gravitation": ["gravitation", "gravitational", "kepler", "orbital", "escape velocity", "satellite", "gravitational potential"],
    "Thermodynamics": ["thermodynamics", "heat engine", "entropy", "enthalpy", "gibbs", "carnot", "isothermal", "adiabatic", "heat capacity", "specific heat", "calorimetry"],
    "Oscillations": ["oscillation", "shm", "simple harmonic", "pendulum", "spring constant", "amplitude", "angular frequency", "damped"],
    "Waves": ["wave equation", "sound wave", "doppler", "standing wave", "superposition", "interference", "beats", "resonance", "wavelength"],
    "Electrostatics": ["electrostatic", "coulomb", "electric field", "electric potential", "capacitor", "capacitance", "gauss", "dipole moment", "dielectric"],
    "Current Electricity": ["ohm's law", "resistance", "resistivity", "kirchhoff", "wheatstone", "potentiometer", "galvanometer", "emf", "internal resistance"],
    "Magnetism": ["magnetic field", "biot savart", "ampere", "solenoid", "lorentz force", "magnetism", "magnetic moment", "toroid", "cyclotron"],
    "Electromagnetic Induction": ["electromagnetic induction", "faraday", "lenz", "inductance", "eddy current", "mutual inductance", "self inductance"],
    "Alternating Current": ["alternating current", "impedance", "reactance", "resonance circuit", "transformer", "power factor", "phasor"],
    "Electromagnetic Waves": ["electromagnetic wave", "em wave", "maxwell", "electromagnetic spectrum", "radio wave", "microwave", "infrared"],
    "Optics": ["optics", "lens", "mirror", "refraction", "reflection", "diffraction", "interference pattern", "polarization", "prism", "total internal reflection", "snell"],
    "Modern Physics": ["photoelectric", "bohr model", "de broglie", "nuclear", "radioactive", "x-ray", "laser", "compton", "binding energy", "mass defect", "half life"],
    "Semiconductor": ["semiconductor", "diode", "transistor", "p-n junction", "logic gate", "zener", "rectifier", "amplifier"],
    "Rotational Motion": ["rotational", "moment of inertia", "torque", "angular momentum", "angular velocity", "rolling", "gyroscope"],
    "Fluid Mechanics": ["fluid", "bernoulli", "viscosity", "surface tension", "buoyancy", "archimedes", "pascal", "streamline", "venturi"],
    "Elasticity": ["elasticity", "stress", "strain", "young's modulus", "bulk modulus", "hooke", "elastic limit"],
    "Kinetic Theory": ["kinetic theory", "ideal gas", "rms speed", "mean free path", "degrees of freedom", "equipartition"],
    "Organic Chemistry": ["organic chemistry", "alkane", "alkene", "alkyne", "alcohol", "aldehyde", "ketone", "carboxylic acid", "ester", "amine", "benzene", "phenol", "ether", "iupac", "isomerism", "stereochemistry", "chirality"],
    "Inorganic Chemistry": ["periodic table", "chemical bonding", "coordination compound", "metallurgy", "salt analysis", "d-block", "p-block", "s-block", "ionic bond", "covalent bond", "hybridization", "vsepr"],
    "Physical Chemistry": ["mole concept", "stoichiometry", "colligative", "electrochemistry", "chemical kinetics", "equilibrium constant", "ionic equilibrium", "thermochemistry", "rate constant", "rate law", "activation energy", "nernst"],
    "Solutions": ["solution", "molarity", "molality", "mole fraction", "henry's law", "raoult's law", "osmotic pressure", "boiling point elevation", "freezing point depression"],
    "Chemical Bonding": ["chemical bonding", "hybridization", "molecular orbital", "vsepr", "dipole moment", "ionic bond", "covalent bond", "metallic bond", "hydrogen bond"],
    "Atomic Structure": ["atomic structure", "quantum number", "orbital", "electron configuration", "aufbau", "pauli", "hund", "heisenberg", "schrodinger"],
    "Redox Reactions": ["redox", "oxidation", "reduction", "oxidizing agent", "reducing agent", "electrochemical cell", "galvanic cell", "electrolysis"],
    "Genetics": ["gene", "genetic", "dna", "rna", "chromosome", "mutation", "heredity", "mendel", "allele", "genotype", "phenotype", "punnett", "linkage", "crossing over"],
    "Cell Biology": ["cell biology", "mitosis", "meiosis", "cell cycle", "organelle", "nucleus", "cell membrane", "endoplasmic reticulum", "golgi", "lysosome", "ribosome"],
    "Ecology": ["ecology", "ecosystem", "biodiversity", "food chain", "food web", "population ecology", "biome", "ecological succession", "biogeochemical cycle"],
    "Human Physiology": ["digestion", "respiration", "circulation", "excretion", "nervous system", "endocrine", "muscle contraction", "skeleton", "blood", "heart", "kidney", "lung", "neuron", "synapse", "hormone"],
    "Plant Physiology": ["photosynthesis", "transpiration", "mineral nutrition", "plant growth", "phytohormone", "auxin", "gibberellin", "abscisic", "chloroplast", "stomata"],
    "Reproduction": ["reproduction", "gametogenesis", "fertilization", "embryo", "placenta", "menstrual cycle", "spermatogenesis", "oogenesis", "pollination"],
    "Evolution": ["evolution", "natural selection", "darwin", "speciation", "adaptation", "fossil", "lamarck", "hardy weinberg", "genetic drift"],
    "Molecular Biology": ["transcription", "translation", "replication", "central dogma", "genetic code", "codon", "operon", "pcr", "restriction enzyme", "recombinant dna"],
    "Biotechnology": ["biotechnology", "genetic engineering", "cloning", "transgenic", "bioreactor", "fermentation", "monoclonal antibody"],
    "Taxonomy": ["taxonomy", "classification", "binomial nomenclature", "kingdom", "phylum", "class", "order", "family", "genus", "species"],
    "Plant Morphology": ["root", "stem", "leaf", "flower", "inflorescence", "fruit", "seed", "morphology"],
    "Animal Kingdom": ["animal kingdom", "vertebrate", "invertebrate", "arthropod", "mollusc", "annelid", "chordata", "mammalia"],
    "Algebra": ["equation", "polynomial", "quadratic equation", "inequality", "sequence", "series", "binomial theorem", "permutation", "combination", "complex number", "logarithm"],
    "Calculus": ["differentiation", "integration", "limit", "derivative", "definite integral", "indefinite integral", "continuity", "maxima", "minima", "differential equation"],
    "Coordinate Geometry": ["coordinate geometry", "parabola", "ellipse", "hyperbola", "circle equation", "straight line", "conic section", "locus"],
    "Trigonometry": ["trigonometry", "sine", "cosine", "tangent", "trigonometric identity", "inverse trigonometric", "triangle"],
    "Vectors": ["vector", "scalar product", "cross product", "dot product", "unit vector", "position vector"],
    "Probability": ["probability", "random variable", "distribution", "mean", "variance", "bayes theorem", "conditional probability", "binomial distribution"],
    "Matrices": ["matrix", "matrices", "determinant", "inverse matrix", "eigen", "adjoint", "cramer"],
    "Sets and Relations": ["set theory", "union", "intersection", "relation", "function", "domain", "range", "bijective", "surjective", "injective"],
    "Statistics": ["statistics", "mean", "median", "mode", "standard deviation", "regression", "correlation"],
    "3D Geometry": ["three dimensional", "3d geometry", "direction cosine", "direction ratio", "skew lines", "plane equation"],
}

# Pre-compile: lowercase all keywords, split multi-word into single check
TOPIC_PATTERNS = {}
for topic, keywords in TOPIC_KEYWORDS.items():
    TOPIC_PATTERNS[topic] = [kw.lower() for kw in keywords]


def match_topic(text: str) -> Optional[str]:
    """Match question text against topic keywords. Returns best topic or None."""
    if not text:
        return None
    text_lower = text.lower()

    scores = {}
    for topic, keywords in TOPIC_PATTERNS.items():
        count = 0
        for kw in keywords:
            if kw in text_lower:
                # Multi-word keywords get bonus weight
                count += 2 if ' ' in kw else 1
        if count >= 2:
            scores[topic] = count

    if not scores:
        return None

    # Return topic with highest score
    return max(scores, key=scores.get)


def main():
    print(f"Opening {QBG_DB}")
    conn = sqlite3.connect(QBG_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Step 1: Add topic column if not exists
    cols = [row[1] for row in conn.execute("PRAGMA table_info(questions)").fetchall()]
    if "topic" not in cols:
        print("Adding topic column...")
        conn.execute("ALTER TABLE questions ADD COLUMN topic TEXT")
        conn.commit()
    else:
        print("topic column already exists")

    # Step 2: Count total and unlabeled questions
    total = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    already_labeled = conn.execute("SELECT COUNT(*) FROM questions WHERE topic IS NOT NULL").fetchone()[0]
    unlabeled = total - already_labeled
    print(f"Total questions: {total}, Already labeled: {already_labeled}, To process: {unlabeled}")

    # Step 3: Process unlabeled rows in batches using id ranges for efficiency
    batch_size = 10000
    labeled = 0
    skipped = 0
    t0 = time.time()

    last_id = 0
    processed = 0
    while True:
        rows = conn.execute(
            "SELECT id, question_clean, text_solution, gpt_analysis FROM questions WHERE topic IS NULL AND id > ? ORDER BY id LIMIT ?",
            (last_id, batch_size)
        ).fetchall()

        if not rows:
            break

        updates = []
        for row_id, q_clean, text_sol, gpt_analysis in rows:
            last_id = row_id
            # Combine question + solution text for better matching
            combined = (q_clean or "")
            if text_sol and len(str(text_sol)) > 20:
                combined += " " + str(text_sol)

            topic = match_topic(combined)
            if topic:
                updates.append((topic, row_id))
                labeled += 1
            else:
                skipped += 1

        if updates:
            conn.executemany("UPDATE questions SET topic = ? WHERE id = ?", updates)
            conn.commit()

        processed += len(rows)
        elapsed = time.time() - t0
        rate = processed / elapsed if elapsed > 0 else 0
        print(f"  Processed {processed}/{unlabeled} ({rate:.0f} rows/sec) — labeled so far: {labeled}")

    elapsed = time.time() - t0
    print(f"\nLabeling complete in {elapsed:.1f}s")
    print(f"  Labeled: {labeled} ({labeled * 100 // total}%)")
    print(f"  Skipped: {skipped}")

    # Step 4: Create index on topic for fast lookups
    print("Creating index on topic column...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic)")
    conn.commit()

    # Step 5: Rebuild FTS5 index to include topic
    print("Rebuilding FTS5 index...")
    # Drop old FTS table and recreate with topic
    conn.execute("DROP TABLE IF EXISTS questions_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE questions_fts USING fts5(
            qbgid,
            subject,
            topic,
            question,
            text_solution,
            gpt_analysis,
            content='questions',
            content_rowid='id'
        )
    """)
    # Populate FTS
    conn.execute("""
        INSERT INTO questions_fts(rowid, qbgid, subject, topic, question, text_solution, gpt_analysis)
        SELECT id, qbgid, subject, topic, question, text_solution, gpt_analysis FROM questions
    """)
    conn.commit()
    print("FTS5 index rebuilt with topic column.")

    # Step 6: Print topic distribution
    print("\nTopic distribution (top 20):")
    dist = conn.execute("""
        SELECT topic, COUNT(*) as cnt
        FROM questions WHERE topic IS NOT NULL
        GROUP BY topic ORDER BY cnt DESC LIMIT 20
    """).fetchall()
    for topic, cnt in dist:
        print(f"  {topic}: {cnt:,}")

    # Also print solution quality stats
    print("\nSolution quality stats:")
    good_sol = conn.execute("""
        SELECT COUNT(*) FROM questions
        WHERE topic IS NOT NULL AND text_solution IS NOT NULL AND LENGTH(text_solution) > 50
    """).fetchone()[0]
    print(f"  Labeled questions with good solutions (>50 chars): {good_sol:,}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
