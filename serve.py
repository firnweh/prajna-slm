"""Host the dashboard publicly from your laptop using ngrok."""
import subprocess
import sys
import threading
import time


def start_streamlit():
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
        "--server.port", "8501",
        "--server.headless", "true",
    ])


def start_ngrok():
    from pyngrok import ngrok
    time.sleep(3)  # wait for streamlit to start
    public_url = ngrok.connect(8501)
    print(f"\n{'=' * 50}")
    print(f"Your dashboard is live at: {public_url}")
    print(f"Share this URL with anyone!")
    print(f"{'=' * 50}\n")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ngrok.disconnect(public_url)


def main():
    from utils.db import init_db
    from utils.loader import load_all_extracted

    db_path = "data/exam.db"
    init_db(db_path)
    total = load_all_extracted(db_path)

    if total == 0:
        print("No questions found in data/extracted/. Add JSON files first.")
        return

    print(f"Loaded {total} questions. Starting server...")

    st_thread = threading.Thread(target=start_streamlit, daemon=True)
    st_thread.start()
    start_ngrok()


if __name__ == "__main__":
    main()
