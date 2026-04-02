import sys, os, shutil
sys.path.insert(0, "/Users/aman/exam-predictor/venv/lib/python3.9/site-packages")

from huggingface_hub import HfApi, create_repo

REPO_ID = "amanrr48/prajna-dashboard"
LOCAL_DIR = "/Users/aman/exam-predictor/hf_deploy/streamlit-space"
SRC = "/Users/aman/exam-predictor"

api = HfApi()
try:
    create_repo(REPO_ID, repo_type="space", space_sdk="gradio", exist_ok=True)
    print("Repo created (will switch to streamlit via README metadata)")
except Exception as e:
    print(f"Repo: {e}")

os.makedirs(LOCAL_DIR, exist_ok=True)

# Copy essential files
files = [
    ("dashboard/app.py", "app.py"),
    ("analysis/predictor_v3.py", "analysis/predictor_v3.py"),
    ("analysis/trend_analyzer.py", "analysis/trend_analyzer.py"),
    ("analysis/deep_analysis.py", "analysis/deep_analysis.py"),
    ("analysis/mistake_analyzer.py", "analysis/mistake_analyzer.py"),
    ("analysis/mistake_predictor.py", "analysis/mistake_predictor.py"),
    ("data/exam.db", "data/exam.db"),
    ("data/syllabus.py", "data/syllabus.py"),
    (".streamlit/config.toml", ".streamlit/config.toml"),
]

# Check for weights cache
if os.path.exists(f"{SRC}/analysis/weights_cache.json"):
    files.append(("analysis/weights_cache.json", "analysis/weights_cache.json"))

# Check for student data CSVs (needed for mistake analysis tab)
# Only include results files, NOT students.csv (has names/cities)
student_data_dir = f"{SRC}/data/student_data"
if os.path.isdir(student_data_dir):
    for f in os.listdir(student_data_dir):
        if f.endswith('.csv') and 'results' in f:
            files.append((f"data/student_data/{f}", f"data/student_data/{f}"))

for src, dst in files:
    src_path = f"{SRC}/{src}"
    dst_path = f"{LOCAL_DIR}/{dst}"
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"Copied {src}")
    else:
        print(f"SKIP {src}")

# Create requirements.txt for the space
with open(f"{LOCAL_DIR}/requirements.txt", "w") as f:
    f.write("""pandas>=2.0.0
plotly>=5.15.0
streamlit>=1.28.0
scikit-learn>=1.3.0
scipy>=1.11.0
numpy<2
""")

# Create __init__.py files for imports
for d in ["analysis", "data", "data/student_data"]:
    init_path = f"{LOCAL_DIR}/{d}/__init__.py"
    os.makedirs(os.path.dirname(init_path), exist_ok=True)
    open(init_path, "w").close()

api.upload_folder(folder_path=LOCAL_DIR, repo_id=REPO_ID, repo_type="space")
print(f"\nUploaded to https://huggingface.co/spaces/{REPO_ID}")
