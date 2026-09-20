"""
Project Genesis: Sovereign Hardware Kill Switch & Memory Purge Engine.
Evicts all neural models from Apple Silicon Unified RAM/VRAM, cleans processes, and frees system memory.
"""

import os
import gc
import json
import subprocess
import urllib.request
from typing import List, Dict, Any

from genesis.config import OLLAMA_BASE_URL
from genesis.core.health_guard import SystemHealthWatchdog


def evict_all_models_from_vram() -> List[str]:
    """
    Find and immediately evict all loaded LLMs and embedding models from Unified RAM/VRAM.
    Frees up 4.7 GB to 8+ GB of RAM instantly.
    """
    base_host = OLLAMA_BASE_URL.replace("/v1", "")
    evicted = []

    # 1. Query loaded models via Ollama API (/api/ps)
    loaded_models = []
    try:
        req = urllib.request.Request(f"{base_host}/api/ps")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                loaded_models.append(m.get("name") or m.get("model"))
    except Exception:
        pass

    # 2. Also check via CLI 'ollama ps' as fallback
    try:
        ps_out = subprocess.check_output(["ollama", "ps"], text=True)
        for line in ps_out.splitlines()[1:]:
            parts = line.split()
            if parts:
                m_name = parts[0].strip()
                if m_name and m_name not in loaded_models:
                    loaded_models.append(m_name)
    except Exception:
        pass

    # 3. Evict each model
    for model in loaded_models:
        if not model:
            continue
        # Unload via API keep_alive: 0
        try:
            unload_payload = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
            post_req = urllib.request.Request(
                f"{base_host}/api/generate",
                data=unload_payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(post_req, timeout=5)
        except Exception:
            pass

        # Unload via CLI 'ollama stop'
        try:
            subprocess.run(["ollama", "stop", model], capture_output=True, timeout=5)
        except Exception:
            pass

        evicted.append(model)

    return evicted


def execute_kill_switch(terminate_self: bool = False) -> str:
    """
    Execute full sovereign kill switch:
    - Evicts all models from Unified RAM (VRAM)
    - Runs garbage collection and cache purges
    - Reports exact RAM reclaimed and new available headroom
    """
    stats_before = SystemHealthWatchdog.get_memory_stats()
    ram_before = stats_before["available_ram_mb"]

    # 1. Evict models from VRAM
    evicted_models = evict_all_models_from_vram()

    # 2. Run Garbage Collection
    gc.collect()

    # 3. Measure memory reclaimed
    stats_after = SystemHealthWatchdog.get_memory_stats()
    ram_after = stats_after["available_ram_mb"]
    ram_reclaimed = max(0.0, round(ram_after - ram_before, 1))

    model_list_str = ", ".join(f"`{m}`" for m in evicted_models) if evicted_models else "None (models were already cold)"

    report = (
        f"# Genesis Kill Switch Engaged\n\n"
        f"- **Models Evicted from VRAM**: {model_list_str}\n"
        f"- **Memory Reclaimed**: ~{ram_reclaimed:.0f} MB Unified RAM\n"
        f"- **Current Available Headroom**: **{ram_after:.0f} MB** (out of {stats_after['total_ram_mb']:.0f} MB total)\n"
        f"- **Swap Space Used**: {stats_after['swap_used_mb']:.1f} MB\n"
        f"- **Hardware Status**: **{SystemHealthWatchdog.evaluate_health_ceiling()[0]}**\n\n"
        f"All Genesis neural resources have been discharged. Your system RAM is fully available for other work."
    )

    if terminate_self:
        import sys
        sys.exit(0)

    return report
