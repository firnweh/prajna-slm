"""
Fine-tune Llama 3.2 3B into PRAJNA SLM using MLX LoRA.

Usage:
  cd /Users/aman/exam-predictor
  source venv/bin/activate
  python analysis/train_prajna_slm.py [--stage combined|stage1|stage2] [--epochs 3] [--batch-size 4]

Requirements:
  - Apple Silicon Mac (M2/M4)
  - MLX and mlx-lm installed
  - Training data prepared by prepare_slm_training.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "slm_training"
ADAPTER_DIR = Path(__file__).parent.parent / "models" / "prajna-slm-adapter"
BASE_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"


def run_training(stage: str, epochs: int, batch_size: int, learning_rate: float):
    """Run MLX LoRA fine-tuning."""
    data_dir = DATA_DIR / stage

    if not (data_dir / "train.jsonl").exists():
        print(f"Error: Training data not found at {data_dir}")
        print("Run: python analysis/prepare_slm_training.py first")
        sys.exit(1)

    adapter_path = ADAPTER_DIR / stage
    adapter_path.mkdir(parents=True, exist_ok=True)

    train_count = sum(1 for _ in open(data_dir / "train.jsonl"))
    valid_count = sum(1 for _ in open(data_dir / "valid.jsonl"))
    iters = (train_count // batch_size) * epochs

    print(f"""
╔══════════════════════════════════════════════════════╗
║  PRAJNA SLM Fine-Tuning                             ║
╠══════════════════════════════════════════════════════╣
║  Base model:  {BASE_MODEL:<38} ║
║  Stage:       {stage:<38} ║
║  Train data:  {train_count:<38} ║
║  Valid data:  {valid_count:<38} ║
║  Epochs:      {epochs:<38} ║
║  Batch size:  {batch_size:<38} ║
║  Learn rate:  {learning_rate:<38} ║
║  Total iters: {iters:<38} ║
║  Adapter out: {str(adapter_path):<38} ║
╚══════════════════════════════════════════════════════╝
""")

    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", BASE_MODEL,
        "--data", str(data_dir),
        "--adapter-path", str(adapter_path),
        "--train",
        "--iters", str(iters),
        "--batch-size", str(batch_size),
        "--learning-rate", str(learning_rate),
        "--lora-layers", "16",
        "--lora-rank", "16",
        "--val-batches", "25",
        "--steps-per-eval", str(max(100, iters // 10)),
        "--steps-per-report", "50",
        "--max-seq-length", "1024",
        "--seed", "42",
    ]

    print("Starting training...")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))

    if result.returncode == 0:
        print(f"\n✅ Training complete! Adapter saved to: {adapter_path}")
        print(f"\nNext steps:")
        print(f"  1. Test: python -m mlx_lm.generate --model {BASE_MODEL} --adapter-path {adapter_path} --prompt 'What is Ohm law?'")
        print(f"  2. Fuse:  python -m mlx_lm.fuse --model {BASE_MODEL} --adapter-path {adapter_path} --save-path models/prajna-slm-3b")
        print(f"  3. Convert to GGUF for Ollama: python -m mlx_lm.convert --model models/prajna-slm-3b --quantize q4_K_M -o models/prajna-slm-3b-gguf")
    else:
        print(f"\n❌ Training failed with exit code {result.returncode}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune PRAJNA SLM")
    parser.add_argument("--stage", default="combined", choices=["combined", "stage1_questions", "stage2_predictions"],
                        help="Training stage (default: combined)")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs (default: 3)")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    parser.add_argument("--learning-rate", type=float, default=1e-5, help="Learning rate (default: 1e-5)")
    args = parser.parse_args()

    run_training(args.stage, args.epochs, args.batch_size, args.learning_rate)


if __name__ == "__main__":
    main()
