#!/usr/bin/env python3
"""
Project Genesis: Autonomous Dataset Curation Engine.
Parses, filters, and formats raw session trajectories into SFT and DPO training sets.
Implements algo.md Section 5.3 and implementation_plan.md Section 7.1.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from genesis.config import TRAJECTORY_DIR, DATASETS_DIR

SFT_OUT = DATASETS_DIR / "sft_dataset.jsonl"
SELF_CORRECT_OUT = DATASETS_DIR / "self_correction_dataset.jsonl"
DPO_OUT = DATASETS_DIR / "dpo_dataset.jsonl"


def curate_trajectories():
    """Process all session JSON files and partition into training datasets."""
    files = list(TRAJECTORY_DIR.glob("session_*.json"))
    print(f"[Curator] Discovered {len(files)} raw session trajectories in {TRAJECTORY_DIR}")

    sft_records: List[Dict[str, Any]] = []
    sc_records: List[Dict[str, Any]] = []
    dpo_records: List[Dict[str, Any]] = []

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Skip purged or incomplete sessions
        if data.get("outcome") == "purged":
            continue

        routing = data.get("routing", "unranked")
        trajectory = data.get("trajectory", [])
        if len(trajectory) < 2:
            continue

        # Build ShareGPT conversation format
        conversations = []
        for step in trajectory:
            role = step.get("role")
            content = step.get("content")
            if role in ["system", "user"]:
                speaker = "system" if role == "system" else "human"
                conversations.append({"from": speaker, "value": str(content)})
            elif role == "assistant":
                conversations.append({"from": "gpt", "value": str(content)})
            elif role == "assistant_tool_call":
                call_info = json.dumps(content) if isinstance(content, dict) else str(content)
                conversations.append({"from": "gpt", "value": f"[Tool Call]: {call_info}"})
            elif role == "tool_observation":
                obs_info = str(content)
                conversations.append({"from": "observation", "value": obs_info})

        record = {
            "session_id": data.get("session_id"),
            "reward_score": data.get("reward_score", 0.0),
            "conversations": conversations,
        }

        if routing == "sft_gold":
            sft_records.append(record)
        elif routing == "self_correction":
            sc_records.append(record)
        elif routing == "dpo_candidate":
            dpo_records.append(record)

    # Write SFT dataset
    with open(SFT_OUT, "w", encoding="utf-8") as out:
        for r in sft_records:
            out.write(json.dumps(r) + "\n")

    # Write Self-Correction dataset
    with open(SELF_CORRECT_OUT, "w", encoding="utf-8") as out:
        for r in sc_records:
            out.write(json.dumps(r) + "\n")

    # Write DPO dataset
    with open(DPO_OUT, "w", encoding="utf-8") as out:
        for r in dpo_records:
            out.write(json.dumps(r) + "\n")

    print(f"[Curator] Curation Complete:")
    print(f"  • SFT Gold Records: {len(sft_records)} -> {SFT_OUT}")
    print(f"  • Self-Correction Records: {len(sc_records)} -> {SELF_CORRECT_OUT}")
    print(f"  • DPO Preference Records: {len(dpo_records)} -> {DPO_OUT}")

    return {
        "sft": len(sft_records),
        "self_correction": len(sc_records),
        "dpo": len(dpo_records),
    }


if __name__ == "__main__":
    curate_trajectories()
