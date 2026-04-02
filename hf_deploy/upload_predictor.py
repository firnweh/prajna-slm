import sys
sys.path.insert(0, "/Users/aman/exam-predictor/venv/lib/python3.9/site-packages")

from huggingface_hub import HfApi, create_repo
import shutil, os

REPO_ID = "amanrr48/prajna-v4-predictor"
LOCAL_DIR = "/Users/aman/exam-predictor/hf_deploy/predictor"

# Create repo
api = HfApi()
try:
    create_repo(REPO_ID, repo_type="model", exist_ok=True)
except Exception as e:
    print(f"Repo creation: {e}")

# Copy model files
os.makedirs(LOCAL_DIR, exist_ok=True)

files_to_upload = [
    ("analysis/predictor_v3.py", "predictor_v3.py"),
    ("analysis/trend_analyzer.py", "trend_analyzer.py"),
    ("analysis/deep_analysis.py", "deep_analysis.py"),
    ("data/exam.db", "exam.db"),
]

# Check for weights cache
if os.path.exists("/Users/aman/exam-predictor/analysis/weights_cache.json"):
    files_to_upload.append(("analysis/weights_cache.json", "weights_cache.json"))

for src, dst in files_to_upload:
    src_path = f"/Users/aman/exam-predictor/{src}"
    dst_path = f"{LOCAL_DIR}/{dst}"
    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"Copied {src} -> {dst}")
    else:
        print(f"SKIP {src} (not found)")

# Upload
api.upload_folder(
    folder_path=LOCAL_DIR,
    repo_id=REPO_ID,
    repo_type="model",
)
print(f"Uploaded to https://huggingface.co/{REPO_ID}")
