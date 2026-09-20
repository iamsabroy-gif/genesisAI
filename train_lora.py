#!/usr/bin/env python3
"""
Project Genesis: Apple MLX Local LoRA Fine-Tuning Engine.
Fine-tunes LoRA adapters on Apple Silicon Metal GPU within 16GB memory bounds.
Implements algo.md Section 6 and implementation_plan.md Section 7.2.
"""

import sys
import os
import subprocess
from pathlib import Path

from genesis.config import GENESIS_HOME, DATASETS_DIR, ADAPTERS_DIR

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
DATASET_PATH = DATASETS_DIR / "sft_dataset.jsonl"


def train_adapter(
    model_name: str = DEFAULT_BASE_MODEL,
    iters: int = 500,
    batch_size: int = 1,
    lora_layers: int = 8,
    lr: float = 1e-5,
):
    """Executes local LoRA fine-tuning using Apple MLX on Metal GPU."""
    print("=" * 60)
    print(" Project Genesis: Apple MLX Local LoRA Fine-Tuning")
    print(" Target Hardware: 16 GB Apple Silicon (Metal GPU)")
    print("=" * 60)

    # 1. Check MLX installation
    try:
        import mlx_lm
        print(f"[MLX Check]: mlx-lm is installed.")
    except ImportError:
        print("[MLX Notice]: mlx-lm is not installed in current environment.")
        print("To install Apple MLX dependencies, run:")
        print("  .venv/bin/pip install mlx mlx-lm\n")
        return False

    # 2. Check Dataset availability
    if not DATASET_PATH.exists() or DATASET_PATH.stat().st_size == 0:
        print(f"[Error]: Training dataset not found or empty at {DATASET_PATH}")
        print("Run ./curator.py first to compile session trajectories into datasets.")
        return False

    # Prepare training directory with train.jsonl
    training_dir = DATASETS_DIR / "sft_train"
    training_dir.mkdir(parents=True, exist_ok=True)
    target_train_file = training_dir / "train.jsonl"
    target_train_file.write_bytes(DATASET_PATH.read_bytes())

    adapter_out = ADAPTERS_DIR / "qwen_coder_genesis"

    # 3. Construct MLX LoRA Command
    cmd = [
        sys.executable,
        "-m",
        "mlx_lm.lora",
        "--model", model_name,
        "--train",
        "--data", str(training_dir),
        "--batch-size", str(batch_size),
        "--lora-layers", str(lora_layers),
        "--learning-rate", str(lr),
        "--max-seq-length", "2048",
        "--iters", str(iters),
        "--adapter-path", str(adapter_out),
    ]

    print(f"\n[Executing MLX Training]:")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Max VRAM Budget: ~6.8 GB (Safe within 16 GB RAM)\n")

    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"\n[Success]: LoRA adapter successfully trained and saved to {adapter_out}")
        return True
    else:
        print(f"\n[Error]: MLX training exited with code {res.returncode}")
        return False


if __name__ == "__main__":
    train_adapter()
