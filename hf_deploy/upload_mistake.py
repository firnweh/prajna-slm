import sys, os, shutil
sys.path.insert(0, "/Users/aman/exam-predictor/venv/lib/python3.9/site-packages")

from huggingface_hub import HfApi, create_repo

REPO_ID = "amanrr48/prajna-mistake-predictor"
LOCAL_DIR = "/Users/aman/exam-predictor/hf_deploy/mistake-model"
SRC = "/Users/aman/exam-predictor"

api = HfApi()
try:
    create_repo(REPO_ID, repo_type="model", exist_ok=True)
except Exception as e:
    print(f"Repo: {e}")

os.makedirs(LOCAL_DIR, exist_ok=True)

files = [
    ("analysis/mistake_analyzer.py", "mistake_analyzer.py"),
    ("analysis/mistake_predictor.py", "mistake_predictor.py"),
    ("tests/test_mistake_analyzer.py", "tests/test_mistake_analyzer.py"),
    ("tests/test_mistake_predictor.py", "tests/test_mistake_predictor.py"),
]

for src, dst in files:
    src_path = f"{SRC}/{src}"
    dst_path = f"{LOCAL_DIR}/{dst}"
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"Copied {src}")

api.upload_folder(folder_path=LOCAL_DIR, repo_id=REPO_ID, repo_type="model")
print(f"\nUploaded to https://huggingface.co/{REPO_ID}")
