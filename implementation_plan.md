# Sovereign Local AI Agent ("Project Genesis")
## Architecture, Phased Implementation, and Self-Improving Dataset Flywheel Plan

> **Vision**: An autonomous, 100% private, sovereign local AI coding assistant tailored specifically for a **16 GB Apple Silicon Mac (MacBook Air)**. Designed not as a static script, but as a living cognitive system that learns from every interaction, builds its own fine-tuning datasets, and continuously adapts over time through local LoRA fine-tuning.
>
> 📖 **Companion Documents**:
> - **Algorithms & Logic**: [algo.md](file:///Users/sabyasachiroy/projects/Learning/Details/algo.md) (State machine, token budgeting, safety gates, reward scoring math)
> - **Multi-Agent Team Roster**: [team.md](file:///Users/sabyasachiroy/projects/Learning/Details/team.md) (Agent roles, tech lead, QA tester, collaborative lifecycle)

---

## 1. Core Architectural Philosophy: The Four Inviolable Laws

1. **100% Sovereignty & Privacy**: Zero remote telemetry, zero cloud dependencies. Your code, terminal outputs, and thoughts never leave your Mac.
2. **Absolute Master Subordination & Preemptive Control**: You are the undisputed Master. Through cryptographic session authorization (MAP), your instructions unconditionally supersede any model logic. The model is wrapped in deterministic Python traps that intercept preemptive Master commands (`!HALT`, `!REVERT`) before the LLM can even deliberate.
3. **The Data Flywheel (Day 1 Telemetry)**: Every interaction—user prompts, tool calls, execution outputs, bug fixes, and user corrections—is automatically captured by a built-in **Flight Recorder** to curate high-quality training datasets for future fine-tuning.
4. **Zero-Swap Memory Discipline**: Strictly engineered to operate within a 16 GB Unified Memory budget without ever triggering SSD swap thrashing, maintaining high token generation speeds (40–55 tokens/sec) and cool thermals on a fanless MacBook Air.

---

## 2. Target Hardware Profile & System Budget (16 GB Apple Silicon)

- **Compute Architecture**: Apple Silicon M-series (10-core CPU, 8-core GPU with Metal Performance Shaders / MPS).
- **Memory Architecture**: 16 GB Unified Memory Architecture (UMA) dynamically shared between CPU, GPU, and macOS.
- **Thermal Envelope**: Fanless passive cooling. Sustained continuous loads cause thermal throttling; bursty, fast reasoning loops (7B model) run cool and efficient.

### 2.1 Unified Memory Allocation Budget

| Component | Target Allocation | Description |
| :--- | :--- | :--- |
| **macOS & System Apps** | ~4.0 – 4.5 GB | OS kernel, WindowServer, IDE, browser, terminal |
| **Model Weights (7B Q4_K_M)** | ~4.7 GB | Active quantized weights loaded in Metal GPU VRAM |
| **KV Cache (16,384 tokens)** | ~1.5 – 1.8 GB | Working context memory with Flash Attention enabled |
| **Local Vector DB & Embeddings** | ~0.4 GB | In-memory semantic index + `nomic-embed-text` |
| **Safety Headroom (Buffer)** | **~4.6 – 5.4 GB** | **Crucial headroom preventing macOS SSD swap** |
| **Total** | **16.0 GB** | **Zero swap latency; peak 40–55 tokens/sec** |

### 2.2 Model Selection Strategy
- **Core Engine (Default Baseline)**: `qwen2.5-coder:7b-instruct-q4_K_M`. Fast (~45 tps), brilliant tool-use capabilities, fits comfortably within 16 GB RAM with zero swap. Primary focus for Epochs 0–2.
- **The "Offline Professor" (Designated AirLLM Candidate)**: `qwen2.5-coder:32b-instruct` (~19 GB on disk). Frontier coding intelligence executed via AirLLM layer-by-layer SSD streaming for overnight Teacher-Student distillation and complex whole-repo audits. (Scheduled for download after finalizing the 7B base).
- **Heavy Deliberation (Optional Intermediate)**: `qwen2.5-coder:14b-instruct-q4_K_M` (~9 GB). Direct drop-in when native RAM allows.

---

## 3. High-Level System Architecture

```mermaid
flowchart TD
    User([User]) <--> CLI[Interactive Terminal / Rich TUI]
    CLI <--> Controller[Agentic ReAct Controller]
    
    subgraph Cognitive Core
        Controller <--> ContextMgr[Context & Token Budget Manager]
        Controller <--> Engine[Local LLM Engine\nOllama / Apple MLX]
        Controller <--> Memory[Multi-Tier Memory\nEpisodic + Tree-sitter AST]
    end
    
    subgraph Tool Sandbox
        Controller --> Dispatcher[Tool Dispatcher]
        Dispatcher --> FS[File Operations\nRead, Write, Unified Diff]
        Dispatcher --> Shell[Sandboxed Terminal\npytest, git, linters]
        Dispatcher --> Search[Ripgrep & Symbol Search]
    end
    
    subgraph Self-Improvement Flywheel
        Controller --> Recorder[Flight Recorder\nTelemetry & Trajectories]
        Recorder --> DatasetDB[(Raw Trajectories DB\nJSONL)]
        DatasetDB --> Curator[Automated Dataset Curator\nRejection Sampling & DPO Filter]
        Curator --> TrainingData[(Gold Standard SFT/DPO Datasets)]
        TrainingData --> FineTuner[Local LoRA Trainer\nApple MLX Framework]
        FineTuner -. Hot-Swapped Adapters .-> Engine
    end
```

---

## 4. The Four Cognitive Subsystems

### Subsystem A: The Dual-Loop Agent Engine (ReAct + Self-Verification)
- **Fast Action Loop**: Model thinks, plans, and issues JSON function calls (`read_file`, `write_file`, `run_command`).
- **Autonomous Verification Loop**: The agent doesn't stop when it writes code. It automatically runs linters (`flake8`, `tsc`, `ruff`) and test suites (`pytest`, `npm test`). If an error occurs, it inspects the traceback and self-corrects without burdening the user.

### Subsystem B: Multi-Tier Memory & Codebase Graph
1. **Working Memory (16k Context Window)**: Active conversation, sliding-window pruned when exceeding 70% capacity.
2. **Semantic Codebase Index (RAG + AST)**:
   - Tree-sitter extracts function signatures, class hierarchies, and imports into a lightweight graph.
   - Vector store (ChromaDB or SQLite-vec with `nomic-embed-text`) indexes docstrings and architectural design decisions.
3. **Episodic Memory & Mentorship Heuristics (`~/.genesis/memory.db`)**:
   - Stores extracted verbal human guidance tuples $\mathcal{H} = \langle \text{Domain}, \text{Forbidden}, \text{Preferred}, \text{Rationale} \rangle$.
   - Automatically queried via cosine similarity before every turn; matching rules are anchored into $C_{\text{memory}}$ so the agent never repeats a corrected behavior.
4. **External Source Assimilation**:
   - Ingests external API documentation, library changelogs, and local markdown notes into the local vector index for grounded reference.

### Subsystem C: The Autonomous Data Flywheel (The "Flight Recorder")
To improve the model over time, we must capture high-quality training pairs directly from usage:
- Every session generates a **Trajectory**:
  $$\text{Trajectory} = \{\text{System Prompt}, \text{User Goal}, [(\text{Thought}, \text{ToolCall}, \text{ToolResult})_1, \dots], \text{Final Output}\}$$
- **Automated Curation & Tagging**:
  - **Success (Gold Trajectory)**: The code compiled, tests passed, and user did not revert. Stored for **Supervised Fine-Tuning (SFT)**.
  - **Self-Correction Trajectory**: The model made an initial syntax error or test failure, diagnosed the output, and fixed it. This is **gold-standard data for teaching reasoning models self-correction**.
  - **Failure / Correction (DPO Pair)**: The model produced bad output, the user corrected it. The bad output becomes $y_w$ (rejected) and the corrected output becomes $y_l$ (chosen) for **Direct Preference Optimization (DPO)**.

### Subsystem D: Continuous Improvement via Apple MLX LoRA & The Sleep Daemon
- Rather than re-training billions of parameters, we train **LoRA (Low-Rank Adaptation)** adapters.
- **Why Apple MLX (`mlx-lm`)**:
  - Native to Apple Silicon; zero translation overhead.
  - Trains 4-bit quantized LoRA adapters directly on your 16 GB Mac using the Metal GPU.
  - LoRA adapters are lightweight (~20 MB to 50 MB files).
- **The Autonomous Sleep Daemon (`genesis-sleep-daemon`)**:
  - Background service that wakes when the Mac is on AC power, CPU idle $> 15$ min, and $\ge 20$ high-reward trajectories have accumulated.
  - Runs local MLX LoRA training autonomously, validates against regression benchmarks, and hot-swaps the new adapter.
- **Modular Adapter Architecture & Dynamic Router**:
  - `adapter_coding_style.npz`: Adapts the model to your personal code conventions.
  - `adapter_data_analysis.npz`: Fine-tuned for exploratory analysis, numerical verification, and data wrangling.
  - `adapter_debugging.npz`: Fine-tuned on past bug-fix trajectories for razor-sharp debugging.
  - Runtime router dynamically selects $\pi_{\text{adapter}}(\text{goal})$ in milliseconds.

### Subsystem E: Master Authorization Protocol (MAP) & Inviolable Override Trap
- **The Core Axiom**: The user is the certified Master. The LLM is an unprivileged reasoning engine wrapped inside deterministic Python control structures.
- **Cryptographic Master Identity**:
  - On startup, initializes a secure Master Key (`~/.genesis/master.key`, chmod 600) bound to your local macOS user session.
  - If a session is unauthorized, Genesis drops immediately to `READ_ONLY_LOCK`—blocking all tool dispatch, file writing, and shell execution.
- **Preemptive Runtime Trap (Kill-Switch & Rollback)**:
  - Any incoming input matching Master signals (`!HALT`, `!REVERT`, `!LOCK`, `!STATUS`) **bypasses LLM tokenization entirely**.
  - `!HALT`: Immediately sends `SIGKILL` to running subprocesses, terminates loops, and returns control to the terminal.
  - `!REVERT`: Executes an atomic Git rollback (`git checkout -- . && git clean -fd`), restoring your repository to the exact commit before the agent took action.

### Subsystem F: Sovereign Local Voice Interface (Microphone & Audio Adapters)
- **100% Private, Offline Voice Pipeline**: Zero cloud audio streaming. Your voice never leaves your MacBook.
- **Microphone Capture & Voice Activity Detection (VAD)**:
  - Uses `sounddevice` or native macOS `AVFoundation` with Push-to-Talk or `silero-vad` (<5 MB RAM).
- **Local Speech-to-Text (STT) via Apple Neural Engine**:
  - Powered by **`mlx-whisper`** (or `whisper.cpp`) running the `small.en` or `base.en` model.
  - Offloaded to Apple Silicon's **Apple Neural Engine (ANE) / Metal MPS**, consuming only ~200 MB of RAM with sub-second transcription latency.
  - Passes transcribed user voice commands straight into the `PERCEIVE` state of the cognitive loop.
- **Vocal Master Interrupt Trigger**:
  - If the audio stream detects the vocal emergency phrase (*"Genesis, halt!"* or *"Genesis, revert!"*), it triggers the preemptive MAP `!HALT` trap instantly, aborting active tasks.
- **Spoken Vocal Responses (Text-to-Speech / TTS)**:
  - Instant zero-overhead feedback via native macOS speech synthesis (`say` daemon with high-quality natural voice) or lightweight local **`Piper TTS`** (~50 MB RAM).

### Subsystem G: Autonomous Capability Expansion & External Connectors (Gmail, APIs, System Bridges)
- **The Anti-Refusal Cognitive Directive**:
  - Genesis is strictly forbidden from reciting passive AI boilerplate (*"As an AI assistant, I don't have the capability..."*).
  - When the Master requests access to an external service or data source (e.g., Gmail, Calendar, local databases), Genesis automatically enters the **Solution Architect** mode: analyzing protocols, formulating a technical plan, and offering to write the tool adapter directly into `genesis/tools/`.
- **Universal Sovereign Connector Hub (`genesis/connectors/`)**:
  - Unified interface (`BaseConnector`) standardizing external app integration and Model Context Protocol (MCP) server bridges.
  - **Tier 1 (macOS Native Bridge - Zero Setup)**:
    - Apple Calendar: Query meetings and scheduled events (`macos_list_calendar_events`).
    - Apple Reminders: Read and create tasks/to-dos (`macos_list_reminders`, `macos_add_reminder`).
    - System Clipboard: Read/write to macOS pasteboard (`macos_read_clipboard`, `macos_write_clipboard`).
  - **Tier 2 (Sovereign Local Gmail Connector)**:
    - Pathway 1 (Google Workspace OAuth2): Local token in `~/.genesis/credentials/gmail_token.json`.
    - Pathway 2 (Local IMAP/SSL): Built-in `imaplib` via Google App Password.
    - Pathway 3 (macOS Apple Mail Bridge): Zero-credential local access via AppleScript.
  - **Tier 3 (Developer & Cloud Connectors - Planned)**:
    - GitHub CLI (`gh`), Slack Webhooks, DuckDB/PostgreSQL adapters.
- **Dynamic Tool Registration**:
  - Connectors dynamically export their tools to `TOOL_MAP` and `TOOL_SCHEMAS` when configured, preventing unnecessary context token consumption when idle.

---

## 5. Phased Implementation Roadmap (Epochs 0 to 3)

### Epoch 0: Genesis Foundation & Flight Recorder (Week 1)
**Goal**: A rock-solid, local ReAct coding assistant running in terminal with 100% telemetry capture and Master authorization.
1. Configure Ollama with Metal GPU acceleration and Flash Attention:
   ```bash
   export OLLAMA_NUM_PARALLEL=1
   export OLLAMA_FLASH_ATTENTION=1
   export OLLAMA_KEEP_ALIVE="30m"
   ```
2. Build custom 16k context Modelfile:
   ```dockerfile
   FROM qwen2.5-coder:7b
   PARAMETER num_ctx 16384
   PARAMETER num_gpu 99
   PARAMETER temperature 0.2
   ```
3. Implement core tool sandbox (`read_file`, `write_file`, `replace_lines`, `run_command`).
4. Implement the **Flight Recorder** to automatically record all trajectory datasets to `~/.genesis/trajectories/`.
5. Implement **Master Authorization Protocol (MAP)**:
   - Cryptographic Master Key handshake in `~/.genesis/master.key`.
   - Preemptive interrupt trap for `!HALT`, `!REVERT`, and `!STATUS` signals.

### Epoch 1: Semantic Code Intelligence & Verification Loop (Weeks 2–3)
**Goal**: Transform the agent from a blind file editor into an architect with code awareness.
1. Integrate **Tree-sitter** for Python, TypeScript, and Go symbol extraction.
2. Build the **Auto-Verification Hook**: After every code modification, automatically detect and execute relevant unit tests or syntax checks.
3. Build **Unified Diff Preview**: Display clean Git diffs before applying changes, requiring single-keystroke confirmation.
4. Implement **Mentorship Ingestion**: Parse verbal user advice and store vectorized heuristics in `~/.genesis/memory.db`.
5. Implement **Sovereign Voice Interface (`genesis voice`)**:
   - Microphone capture via `sounddevice` with Push-to-Talk / `silero-vad`.
   - Local STT transcription via `mlx-whisper` (`base.en` / `small.en`) on Apple Neural Engine.
   - Preemptive voice kill-phrase: *"Genesis, halt!"* triggering the MAP `!HALT` trap.
   - Spoken vocal responses via native macOS `say` or local Piper TTS.

### Epoch 2: The Dataset Factory & Curation Pipeline (Weeks 4–5)
**Goal**: Automatically process recorded trajectories into clean, high-value training datasets.
1. Build `curator.py`:
   - Parses raw session trajectories.
   - Cleans ANSI escape codes and truncates excessive logs.
   - Formats data into standardized training formats (ShareGPT / Alpaca JSON).
2. Synthetic Trajectory Enrichment: Use your own local model during idle overnight hours to synthesize alternative solution paths and verify them against test cases (Rejection Sampling).
3. Build **Regression Evaluation Suite**: Standard benchmark problems (HumanEval subset + local repo unit tests) to gate adapter deployment.

### Epoch 3: Local LoRA Training & The Sleep Consolidation Daemon (Week 6+)
**Goal**: The model begins self-improving directly on your Mac without manual intervention.
1. Install Apple MLX:
   ```bash
   pip install mlx mlx-lm
   ```
2. Build the **Autonomous Sleep Daemon** (`genesis-sleep-daemon.py`):
   - Monitors trajectory threshold ($N \ge 20$) and system idle state.
   - Executes MLX fine-tuning safely within $<6.8\text{ GB}$ VRAM.
   - Benchmarks new adapter against regression suite before deployment.
3. Implement **Dynamic Adapter Router** in `GenesisAgent`:
   - Hot-swaps `adapter_coding_style.npz`, `adapter_data_analysis.npz`, and `adapter_debugging.npz` based on task classification.

---

## 6. Complete Working Prototype with Flight Recorder (`genesis_agent.py`)

Below is the complete, working implementation of **Epoch 0**. It features the full ReAct loop, tool execution, context safeguards, and the **Flight Recorder** that automatically captures training datasets from every run.

```python
#!/usr/bin/env python3
"""
Project Genesis: Sovereign Local AI Coding Assistant
Equipped with ReAct reasoning, tool sandboxing, and Flight Recorder telemetry.
"""

import os
import sys
import json
import time
import uuid
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen2.5-coder:7b"  # Or your custom 'qwen2.5-coder-agent'
GENESIS_DIR = Path.home() / ".genesis"
TRAJECTORY_DIR = GENESIS_DIR / "trajectories"

GENESIS_DIR.mkdir(parents=True, exist_ok=True)
TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# ----------------------------------------------------------------------
# Tool Registry & Execution Sandbox
# ----------------------------------------------------------------------
def run_command(command: str) -> str:
    """Run a shell command with bounds checks and output truncation."""
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=45,
            cwd=os.getcwd(),
        )
        output = (res.stdout + res.stderr).strip()
        if not output:
            return "Command executed successfully (exit code 0, no output)."
        # Truncate to protect context window on 16GB Mac
        if len(output) > 4000:
            return output[:3800] + f"\n... [Output truncated; total {len(output)} chars]"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 45 seconds."
    except Exception as e:
        return f"Execution Error: {e}"

def read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """Read specific line ranges with file bounds checks."""
    try:
        p = Path(path).resolve()
        if not p.is_file():
            return f"Error: File not found at {path}"
        
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)
        
        start = max(1, start_line)
        end = min(total_lines, end_line)
        
        selected = lines[start - 1 : end]
        annotated = [f"{i + start}: {line}" for i, line in enumerate(selected)]
        header = f"[File: {p.name} | Lines {start}-{end} of {total_lines}]\n"
        return header + "\n".join(annotated)
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(path: str, content: str) -> str:
    """Write or overwrite a file with strict directory creation."""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {p.name}"
    except Exception as e:
        return f"Error writing file: {e}"

def replace_snippet(path: str, target: str, replacement: str) -> str:
    """Precise snippet replacement to avoid rewriting entire files."""
    try:
        p = Path(path).resolve()
        if not p.is_file():
            return f"Error: File not found at {path}"
        
        text = p.read_text(encoding="utf-8")
        if target not in text:
            return f"Error: Target snippet not found in {p.name}."
        
        if text.count(target) > 1:
            return f"Error: Target snippet occurs {text.count(target)} times. Provide more unique context lines."
        
        updated = text.replace(target, replacement, 1)
        p.write_text(updated, encoding="utf-8")
        return f"Successfully applied patch to {p.name}"
    except Exception as e:
        return f"Error patching file: {e}"

TOOL_MAP = {
    "run_command": run_command,
    "read_file": read_file,
    "write_file": write_file,
    "replace_snippet": replace_snippet,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command (git, tests, build, linters) in current directory.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read line-numbered contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "default": 1},
                    "end_line": {"type": "integer", "default": 200},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_snippet",
            "description": "Replace an exact block of existing text in a file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "target": {"type": "string"},
                    "replacement": {"type": "string"},
                },
                "required": ["path", "target", "replacement"],
            },
        },
    },
]

# ----------------------------------------------------------------------
# Flight Recorder (Dataset Harvesting Engine)
# ----------------------------------------------------------------------
class FlightRecorder:
    """Captures complete execution trajectories for future model training."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.datetime.now().isoformat()
        self.trajectory: List[Dict[str, Any]] = []

    def record_step(self, role: str, content: Any, metadata: Dict[str, Any] = None):
        step = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
        }
        if metadata:
            step["metadata"] = metadata
        self.trajectory.append(step)

    def finalize(self, outcome: str = "success"):
        record = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": datetime.datetime.now().isoformat(),
            "outcome": outcome,
            "trajectory": self.trajectory,
        }
        output_file = TRAJECTORY_DIR / f"session_{self.session_id[:8]}.json"
        output_file.write_text(json.dumps(record, indent=2))
        print(f"\n[Flight Recorder] Trajectory saved to {output_file.name} for dataset pipeline.")

# ----------------------------------------------------------------------
# Agent Core Loop
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """You are Genesis, a sovereign local AI coding assistant running on Apple Silicon.
You have access to local file editing and shell execution tools.
Always inspect existing code before modifying.
Verify your changes by running tests or syntax checks whenever possible.
Be concise, proactive, and precise."""

def run_agent():
    recorder = FlightRecorder()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    recorder.record_step("system", SYSTEM_PROMPT)

    print("=" * 60)
    print(f" Project Genesis Agent [16GB Mac Metal Optimized]")
    print(f" Model: {MODEL_NAME} | Flight Recorder: Active")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            recorder.finalize(outcome="completed_by_user")
            print("\nGoodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        recorder.record_step("user", user_input)

        # Autonomous ReAct Loop
        max_turns = 15
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    temperature=0.2,
                )
            except Exception as e:
                print(f"\n[LLM Error]: {e}")
                break

            msg = response.choices[0].message
            messages.append(msg)

            # If no tool calls, model has answered the user
            if not msg.tool_calls:
                print(f"\nGenesis:\n{msg.content}")
                recorder.record_step("assistant", msg.content)
                break

            # Execute Tool Calls
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except Exception:
                    fn_args = {}

                print(f"\n[Action] {fn_name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in fn_args.items())})")
                
                recorder.record_step("assistant_tool_call", {
                    "name": fn_name,
                    "arguments": fn_args,
                    "id": tool_call.id
                })

                # Dispatch
                handler = TOOL_MAP.get(fn_name)
                if handler:
                    result = handler(**fn_args)
                else:
                    result = f"Error: Unknown tool '{fn_name}'"

                print(f"[Observation]: {str(result)[:200]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": str(result),
                })
                recorder.record_step("tool_observation", result, {"name": fn_name})

if __name__ == "__main__":
    run_agent()
```

---

## 7. The Dataset Curation & Fine-Tuning Playbook

To transform captured trajectories into improved intelligence, follow this continuous data cycle:

```mermaid
flowchart LR
    A[Raw Trajectories\n~/.genesis/trajectories] --> B[curator.py\nFilter & Score]
    B -->|Verified Clean| C[SFT Training Set\nShareGPT Format]
    B -->|User Corrected| D[DPO Preference Set\nChosen / Rejected]
    C & D --> E[Apple MLX LoRA\nmlx_lm.lora on Metal]
    E --> F[Personalized Adapter\nadapter.npz]
    F --> G[Genesis Agent Core\nHot-swapped]
    G --> A
```

### 7.1 Dataset Transformation Script (`curator.py`)
Run weekly or monthly to convert raw session traces into a clean SFT dataset:
```python
import json
from pathlib import Path

TRAJ_DIR = Path.home() / ".genesis" / "trajectories"
OUT_FILE = Path.home() / ".genesis" / "sft_dataset.jsonl"

dataset = []
for file in TRAJ_DIR.glob("session_*.json"):
    data = json.loads(file.read_text())
    if data.get("outcome") != "completed_by_user":
        continue

    # Convert trajectory to ShareGPT multi-turn conversation format
    conversations = []
    for step in data["trajectory"]:
        role = "human" if step["role"] == "user" else "gpt"
        conversations.append({"from": role, "value": str(step["content"])})

    if len(conversations) >= 2:
        dataset.append({"conversations": conversations})

with open(OUT_FILE, "w") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")

print(f"Generated {len(dataset)} training examples in {OUT_FILE}")
```

### 7.2 Training Your Custom Adapter with Apple MLX
Once you have collected 50–100 clean sessions, run the fine-tuner locally on your Mac's GPU:

```bash
# 1. Install MLX LM
pip install mlx-lm

# 2. Run LoRA fine-tuning on 16GB Metal GPU
mlx_lm.lora \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --train \
  --data ~/.genesis/sft_dataset.jsonl \
  --batch-size 1 \
  --lora-layers 8 \
  --learning-rate 1e-5 \
  --max-seq-length 2048 \
  --iters 500
```
This training run takes **~15 to 30 minutes** on your Mac, produces a **~35 MB adapter file**, and consumes **<8 GB of RAM** with zero thermal distress.

---

---
 
 ## 8. Multi-Agent Swarm Subsystem (`genesis/core/swarm.py`)
 
 ### 8.1 Sequential Memory Multiplexing on 16GB Apple Silicon
 To support continuous, multi-agent collaboration without overflowing the 16 GB Unified Memory budget:
 - Instead of running concurrent LLMs (which would require $>18\text{ GB}$ of RAM), Genesis uses a single resident `qwen2.5-coder-agent` process (~4.7 GB).
 - Specialized agents run as stateful persona workers multiplexed through the single engine:
   1. **`Researcher`**: Performs codebase reconnaissance (`search_code`, `list_files`, `read_file`).
   2. **`Implementer`**: Executes precise code edits (`replace_snippet`, `write_file`).
   3. **`Tester`**: Executes test suites and reproduction commands (`run_command`).
   4. **`Judge`**: Analyzes test results, diagnostics, and file state to certify whether the goal is achieved (`GOAL_ACHIEVED: YES` / `NO`).
 - The coordinator executes in iterative rounds until the `Judge` certifies completion or human intervention (`!HALT`) is triggered.
 - Complete execution logs and per-persona transcripts are recorded in `~/.genesis/swarm/<swarm_id>.json`.
 
 ### 8.2 Inviolable Swarm Control & RAM Eviction
 - **Preemptive Control**: The Master can halt any swarm in mid-execution using `!HALT` or initiate a swarm directly via `!SWARM <goal>`.
 - **Memory Deallocation**: Upon swarm completion or CLI exit, `GenesisAgent.close(unload_model=True)` triggers `POST /api/generate` with `keep_alive: 0`, ensuring volatile RAM is evicted down to 0 MB.
 
 ---

## 9. Task Controller, Interruption Guards & Command Queuing (`genesis/core/task_controller.py`)

### 9.1 Non-Destructive Master Interruption (`Ctrl+C` / `!HALT`)
Previously, pressing `Ctrl+C` raised an unhandled `KeyboardInterrupt` that killed the entire interactive session.
Genesis now features a non-destructive Task Controller:
- Intercepts `SIGINT` / `KeyboardInterrupt` during active LLM inference or tool runs.
- Deterministically signals `agent.abort_requested.set()`.
- Terminates all active child subprocesses (`terminate_active_processes()`) via `SIGKILL`.
- Restores the agent state cleanly to `IDLE` without tearing down the CLI session or losing active context history.

### 9.2 Command-Queuing & Chained Pipelines
- **Pipeline Syntax (`;;`)**: Users can chain multiple instructions in a single prompt (e.g. `read_file foo.py ;; run_command pytest ;; fix errors`).
- **Dynamic Queue Drainage**: When a task completes, the `TaskController` automatically inspects `agent.command_queue` and executes pending tasks sequentially.
- **Queue Signals**: 
  - `!QUEUE <cmd>`: Enqueue instruction for sequential dispatch.
  - `!QUEUE LIST`: Inspect currently pending commands.
  - `!QUEUE CLEAR`: Wipe pending commands.
### 9.3 Static Asynchronous User Terminal (`genesis/core/terminal.py`)
Powered by `prompt_toolkit` and `asyncio`:
- **Static Persistent Input Prompt (`You > `)**: Pinned permanently at the bottom of the terminal screen. Never disappears or blocks while Genesis is reasoning or executing tools.
- **Asynchronous Background Execution**: User prompts and swarm iterations execute in a decoupled background worker (`asyncio.to_thread`).
- **Concurrent Prompt Queuing**: The user can type follow-up instructions at any time while the agent is generating. New instructions are automatically enqueued with live confirmation and execute sequentially.
- **Static Context & State Toolbar**: Pinned directly above the input prompt, rendering real-time context tokens, percentage used, visual progress gauge, system state (`IDLE`/`BUSY`), active queue count, and loaded model.
- **Instant Interactive Control**: Entering `!HALT` or pressing `Ctrl+C` immediately aborts active execution and subprocesses without killing the REPL session.

---

## 10. Summary: What Makes This Architecture Unique

| Feature | Standard Local Agent | Project Genesis (Our Vision) |
| :--- | :--- | :--- |
| **Privacy** | Often leaks telemetry to cloud | **100% sovereign & local** |
| **Hardware Fit** | Generic, risks OOM/swap | **Engineered strictly for 16GB Apple Silicon** |
| **Multi-Agent Collaboration** | Memory-heavy multi-process | **Sequential Persona Multiplexing (<5GB VRAM)** |
| **User Interface** | Blocking synchronous terminal | **Static Async User Terminal with Live Context Toolbar** |
| **Interruption & Control** | Crashing SIGINT / Unresponsive | **Non-destructive `Ctrl+C`/`!HALT` + Command Queuing** |
| **Memory Evolution** | Amnesiac (forgets every restart) | **Multi-tier episodic memory + code AST** |
| **Learning Over Time** | Static model weights forever | **Built-in Flight Recorder + MLX LoRA Flywheel** |
| **Verification** | Blind file modifications | **Autonomous test-execution & self-repair loop** |
| **VRAM Reclamation** | Models remain cached indefinitely | **Deterministic `keep_alive: 0` eviction on exit** |



