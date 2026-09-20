"""
Project Genesis: Configuration & Hardware Constraints.
Configured for 16 GB Apple Silicon Mac (M-series, 10 CPU / 8 GPU cores).
"""

import os
from pathlib import Path

# Base Paths
WORKSPACE_ROOT = Path(os.getcwd()).resolve()
GENESIS_HOME = Path.home() / ".genesis"
GENESIS_DIR = GENESIS_HOME
TRAJECTORY_DIR = GENESIS_HOME / "trajectories"
DATASETS_DIR = GENESIS_HOME / "datasets"
ADAPTERS_DIR = GENESIS_HOME / "adapters"
RESEARCH_DIR = GENESIS_HOME / "research"
DOCUMENTS_DIR = GENESIS_HOME / "documents"
VAULT_DIR = GENESIS_HOME / "vault"
TASKS_DIR = GENESIS_HOME / "tasks"

# Ensure runtime directories exist
for p in [GENESIS_HOME, TRAJECTORY_DIR, DATASETS_DIR, ADAPTERS_DIR, RESEARCH_DIR, DOCUMENTS_DIR, VAULT_DIR, TASKS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# LLM Engine Settings (Ollama on Apple Silicon)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = "ollama"

# Preferred Models for 16GB Mac
MODEL_CANDIDATES = [
    "qwen2.5-coder-agent",
    "qwen2.5-coder:7b",
    "hf.co/google/gemma-4-12B-it-qat-q4_0-gguf:Q4_0",
]
DEFAULT_MODEL = "qwen2.5-coder-agent"

# M5: Draft model for fast-path routing (simple/conversational queries)
# Set to a smaller/faster model pulled in Ollama. Falls back to DEFAULT_MODEL if not available.
DRAFT_MODEL = os.getenv("GENESIS_DRAFT_MODEL", "qwen2.5-coder:1.5b")

# Memory & Token Boundaries (Configurable Context Window Ceiling)
# Default is 16384 (calibrated for 16 GB Apple Silicon Macs to prevent memory pressure).
# Configurable via environment variable GENESIS_MAX_CONTEXT (e.g. 32768, 65536) or runtime commands.
MAX_CONTEXT_TOKENS = int(os.getenv("GENESIS_MAX_CONTEXT", 16384))
PRUNE_TRIGGER_TOKENS = int(os.getenv("GENESIS_PRUNE_TRIGGER", int(MAX_CONTEXT_TOKENS * 0.75)))
TARGET_HISTORY_TOKENS = int(os.getenv("GENESIS_TARGET_HISTORY", int(MAX_CONTEXT_TOKENS * 0.66)))
MAX_COMMAND_OUTPUT_CHARS = 3800     # Protect context buffer from long terminal dumps
MAX_REPAIR_RETRIES = 3              # Diagnostic backoff bound (K_max)

# Tool Safety Settings
COMMAND_TIMEOUT_SECONDS = 45
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs",
    r"dd\s+if=",
    r"diskutil\s+eraseDisk",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
]
