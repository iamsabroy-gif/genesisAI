#!/usr/bin/env python3
"""
Project Genesis: Autonomous Sleep Consolidation Daemon ("The Dream Loop").
Implements algo.md Section 8.
Runs during system idle/sleep state when on AC power to autonomously fine-tune model weights.
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Tuple

from genesis.config import TRAJECTORY_DIR, GENESIS_HOME
from curator import curate_trajectories
from train_lora import train_adapter

DAEMON_STATE_FILE = GENESIS_HOME / "sleep_daemon_state.json"
MIN_NEW_TRAJECTORIES = 20


def is_on_ac_power() -> bool:
    """Check if Mac is connected to AC power using pmset."""
    try:
        res = subprocess.run("pmset -g batt", shell=True, capture_output=True, text=True)
        return "AC Power" in res.stdout
    except Exception:
        return True  # Fallback to True if unknown


def count_new_trajectories() -> int:
    """Count uncurated session trajectories."""
    files = list(TRAJECTORY_DIR.glob("session_*.json"))
    return len(files)


def evaluate_sleep_trigger_conditions(force: bool = False) -> Tuple[bool, str]:
    """
    Evaluates the 3 boundary conditions from algo.md Section 8.1:
    1. Sample Threshold (N >= 20)
    2. Power Status (AC power)
    3. System Idle
    """
    if force:
        return True, "Trigger forced by user flag."

    if not is_on_ac_power():
        return False, "MacBook is running on battery. Halting to preserve battery health."

    n_trajectories = count_new_trajectories()
    if n_trajectories < MIN_NEW_TRAJECTORIES:
        return False, f"Insufficient new trajectories ({n_trajectories}/{MIN_NEW_TRAJECTORIES} accumulated)."

    return True, f"All conditions met ({n_trajectories} trajectories, AC power active)."


def run_consolidation_cycle(force: bool = False):
    """Executes a single synaptic consolidation (dream loop) cycle."""
    print("=" * 60)
    print(" Project Genesis: Autonomous Sleep Consolidation Daemon")
    print("=" * 60)

    can_run, reason = evaluate_sleep_trigger_conditions(force=force)
    print(f"[Daemon Assessment]: {reason}")

    if not can_run:
        return False

    print("\n[Phase 1]: Curating high-reward SFT & DPO training pairs...")
    stats = curate_trajectories()

    if stats["sft"] == 0 and stats["self_correction"] == 0:
        print("[Daemon Notice]: No high-reward (R >= 0.80) trajectories ready for fine-tuning.")
        return False

    print("\n[Phase 2]: Launching Local Apple MLX LoRA Fine-Tuning on Metal GPU...")
    success = train_adapter(iters=300)

    if success:
        print("\n[Phase 3]: Consolidation complete. New synaptic adapter ready.")
    return success


def main():
    force_mode = "--force" in sys.argv or "-f" in sys.argv
    run_once = "--once" in sys.argv or force_mode

    if run_once:
        run_consolidation_cycle(force=force_mode)
    else:
        print("[Genesis Sleep Daemon] Running in daemon mode. Checking every 15 minutes...")
        while True:
            try:
                run_consolidation_cycle(force=False)
                time.sleep(900)  # Sleep 15 minutes
            except KeyboardInterrupt:
                print("\n[Genesis Sleep Daemon] Daemon stopped.")
                break


if __name__ == "__main__":
    main()
