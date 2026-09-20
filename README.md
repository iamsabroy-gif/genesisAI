# Project Genesis AI

> **Sovereign Local AI Agent & Autonomous Process-Oriented Research Swarm**  
> Engineered natively for Apple Silicon (M1/M2/M3/M4) & Intel Macs with Dynamic Context Scaling, Apple WebKit Desktop GUI, and Publication-Grade Dossier Authoring.

---

## 🌟 Overview

**Project Genesis** is an autonomous, sovereign AI coding agent and academic-grade research swarm designed to run entirely locally or connected to high-throughput remote inference servers. Built from the ground up for macOS Unified Memory architecture, Genesis eliminates memory pressure and context degradation through **Memory Multiplexing**, **Priority-Weighted Context Eviction**, and a **5-Phase Process-Oriented Research Swarm**.

Whether executing full software engineering tasks or authoring exhaustive analytical whitepapers, Genesis operates through both a sleek **Apple WebKit Desktop GUI** (`Genesis.app` / `genesis-gui`) and a high-efficiency **Terminal REPL** (`genesis`).

---

## 🚀 Key Features

### 🔬 1. Process-Oriented Multi-Agent Research Swarm
An iterative, 5-phase academic and executive research pipeline:
- **Phase 1: Research Architect & Scoping Lead (`Dr. Vance`)**: Deconstructs topic into an investigative charter with 6 core pillars, quantitative metrics, and 8–12 targeted search queries.
- **Phase 2: Multi-Angle Intelligence Recon Squad (`Scout Alpha`)**: Probes web search engines, discovering and extracting data from **10 to 20 verified URLs**.
- **Phase 3: Quantitative & Systems Modeler (`Analyst Chen`)**: Translates raw extracted data into comparative benchmark matrices, SWOT analyses, and trade-off tables.
- **Phase 4: Red Team Peer Reviewer & Auditor (`Inspector Sterling`)**: Critiques analytical depth, checks citation validity, and issues 4 mandatory remediation directives.
- **Phase 5: Principal Executive Editor (`Editor-in-Chief Evelyn`)**: Authors the full, publication-ready Markdown deliverable saved directly to your workspace and the local vault (`~/.genesis/research/`).

### 🌐 2. Multi-Source Empirical Extraction & Context Compression
- **10 to 20 Verified Sources**: Expands research breadth far beyond simple 2-link summaries, gathering verified data across multiple technical domains.
- **Zero-Loss Disk Vaulting**: Full raw scraped HTML/markdown text is archived permanently to `~/.genesis/research/dossiers/<topic>_<swarm_id>_sources.json`.
- **In-Memory Structured Compression**: Distills each source into ~100 tokens (key quantitative metrics, benchmarks, and takeaways). Even a 20-source dossier occupies only ~2,400 tokens, protecting the model's context window.

### 📑 3. Five Supported Report Formats
Choose the optimal deliverable structure before launching research:
| Format ID | Name | Audience | Core Focus |
| :--- | :--- | :--- | :--- |
| `comprehensive` | **Comprehensive Academic Report** | Technical Leaders & Researchers | 7 Sections, deep benchmark matrices, SWOT, and formal citations bibliography. *(Default)* |
| `executive` | **Executive Briefing & Decision Memo** | C-Suite & Decision Makers | 7 Sections, KPI dashboard, cost/ROI models, and 90-day execution roadmap. |
| `technical` | **Technical Architecture & System Spec** | Senior Engineers & Architects | 7 Sections, system architecture, latency/throughput specs, and failure modes. |
| `market` | **Competitive Market & Industry Analysis** | Strategy & Product Teams | 7 Sections, TAM/SAM/SOM sizing, competitor pricing matrices, and moat analysis. |
| `due_diligence` | **Due Diligence & Go/No-Go Risk Audit** | Investors & Risk Committees | 7 Sections, red flags checklist, risk heatmaps, and definitive Go/No-Go verdict. |

### 🧠 4. Dynamic Context Scaling (8k – 128k)
- Dynamically scale context window on the fly via `/context 32k`, `/context 64k`, or `/context 128k`.
- **Hardware-Informed Watchdog**: Evaluates free Apple Silicon Unified RAM and warns before memory swapping occurs.
- **Priority-Weighted Pruning**: Triggers at 75% capacity, immutably anchoring system directives and root user goals while evicting ephemeral intermediate outputs.

### 🖥️ 5. Dual Interfaces: Desktop GUI & Terminal REPL
- **Desktop GUI**: Native macOS WebKit (`WKWebView`) window running a modern dark-mode responsive dashboard with live phase progress, real-time token gauge, file drop zone, and model selector.
- **Terminal REPL**: Full-featured prompt toolkit with syntax highlighting, autocomplete, slash commands, and background job handling.

### 📦 6. Standalone macOS App & `.dmg` Installer
- Fully self-contained `Genesis.app` bundle.
- Pre-packaged drag-and-drop installer: `Genesis-Installer-arm64.dmg` (25 MB).

---

## 📥 Installation

### Option A: One-Command Universal Installer (Recommended)
On any Mac (Apple Silicon M1/M2/M3/M4 or Intel x86_64):

```bash
git clone https://github.com/iamsabroy-gif/genesisAI.git
cd genesisAI
chmod +x install.sh
./install.sh
```

This automated script:
1. Detects your Mac CPU architecture (`arm64` vs `x86_64`).
2. Creates an isolated virtual environment (`.venv`) and installs all dependencies.
3. Compiles the native `Genesis.app` bundle and copies it to `~/Applications/Genesis.app`.
4. Installs `genesis` and `genesis-gui` command-line shortcuts into `~/.local/bin`.

---

### Option B: Manual Setup

```bash
# 1. Clone repository
git clone https://github.com/iamsabroy-gif/genesisAI.git
cd genesisAI

# 2. Initialize virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip setuptools wheel
pip install -e .
pip install pywebview pyinstaller rich openai pydantic pypdf beautifulsoup4
```

---

### Option C: Building the Standalone `.dmg` Installer

To build or distribute an installable disk image for macOS:

```bash
./scripts/build_dmg.sh
```

Output:
- `dist/Genesis.app` (Native application bundle)
- `dist/Genesis-Installer-arm64.dmg` (Drag-and-drop macOS installer)

> **macOS Gatekeeper Notice**: When opening an ad-hoc compiled app on another Mac for the first time, macOS may show a developer verification notice. Either **Right-click `Genesis.app` → Open**, or execute:
> ```bash
> xattr -cr /Applications/Genesis.app
> ```

---

## ⚙️ Local LLM Backend (Ollama)

Genesis integrates out-of-the-box with [Ollama](https://ollama.com):

```bash
# Recommended default model (7B/8B code & reasoning)
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b
```

To configure a custom model or remote endpoint, set environment variables in your `~/.zshrc`:
```bash
export OLLAMA_BASE_URL="http://localhost:11434/v1"
export GENESIS_DEFAULT_MODEL="qwen2.5-coder:7b"
export GENESIS_MAX_CONTEXT=32768
```

---

## 🎮 How to Use Genesis

### 1. Launching the Desktop GUI
Open `Genesis.app` from your Applications folder, or run:
```bash
genesis-gui
```

### 2. Launching the Interactive Terminal REPL
```bash
genesis
```

---

### 3. Running the Process-Oriented Research Swarm

#### In the GUI:
1. Navigate to the **🔬 Research Swarm** tab.
2. Enter your topic.
3. Choose your **Report Format** (Comprehensive, Executive, Technical, Market, or Due Diligence).
4. Select your **Extraction Target** (10, 15, or 20 verified sources).
5. **(Optional) Attach Starting Context**:
   - Click **`📎 Attach File(s)`** to select local PDFs, Markdown docs, code, or CSVs.
   - Click **`📁 Attach Folder`** to select an entire directory of research documents.
   - Or type/paste specific **seed URLs** (e.g. `https://arxiv.org/abs/...`), file paths, or directives directly into the input box.
6. Click **Launch Research**.

#### In the Terminal REPL:
```text
# Run with defaults (Comprehensive format, 10 URLs)
/research Solid-State Battery Commercialization 2026

# Seed with a local PDF whitepaper and extract 15 verified URLs
/research Quantum Computing Fault Tolerance -f technical --urls 15 --file ./quantum_paper.pdf

# Seed with specific priority URLs and local lab notes
/research Lithium-Sulfur Batteries -f technical --context https://arxiv.org/abs/2301.xxxx,./lab_notes.md

# Executive briefing memo seeding an entire document folder
/research Autonomous Delivery Drones Market -f executive --folder ./market_reports/
```

#### Directly from the Command Line:
```bash
# Attach file or folder context directly from bash
genesis research "Next-Gen AI Accelerators" --format technical --urls 15 --file ./specs.pdf

# Provide seed URLs and directories
genesis research "Solid-State Batteries" --context https://arxiv.org/abs/1234,./notes_dir/
```

The resulting deliverable is saved both as a Markdown document in your current directory and archived in `~/.genesis/research/`. Raw source dossiers with full citation metadata are archived in `~/.genesis/research/dossiers/`.

---

### 4. Slash Commands Cheat Sheet (REPL & GUI)

| Slash Command | Description | Example |
| :--- | :--- | :--- |
| `/research <topic> [flags]` | Executes the 5-phase research swarm | `/research AI Chips -f technical --urls 15` |
| `/context [size]` | Inspects or rescales context capacity | `/context 32k` or `/context 64k` |
| `/formats` | Displays available report formats table | `/formats` |
| `/skills` | Lists all active and available capabilities | `/skills` |
| `/upload <path>` | Uploads local files or folders into context | `/upload ./data/specs.pdf` |
| `/models` | Shows available local & remote models | `/models` |
| `/model <name>` | Switches active LLM model | `/model qwen2.5-coder:7b` |
| `/health` | Displays Apple Silicon memory & CPU watchdog | `/health` |
| `/kill` | Emergency abort for all running tasks/swarms | `/kill` |
| `/clear` | Resets active conversational history | `/clear` |

---

## 💻 Hardware & Memory Optimization Matrix

Genesis is calibrated for Apple Silicon Unified Memory:

| Context Window | Model Weights (7B Q4) | KV Attention Cache | Total RAM Footprint | Hardware Guidance |
| :--- | :--- | :--- | :--- | :--- |
| **16k (16,384)** | ~4.8 GB | ~2.0 GB | ~7.2 GB | **Optimal for 16GB Macs** (Zero disk paging) |
| **32k (32,768)** | ~4.8 GB | ~4.1 GB | ~9.3 GB | **Stable on 16GB Macs** |
| **64k (65,536)** | ~4.8 GB | ~8.2 GB | ~13.4 GB | **Recommended for 32GB+ Macs** or Cloud APIs |
| **128k (131,072)**| ~4.8 GB | ~16.4 GB | ~21.6 GB | **Recommended for 64GB+ Macs** or Cloud APIs |

*When connected to remote or cloud endpoints (OpenAI, DeepSeek, Claude, Groq), the KV cache is managed on server GPUs, allowing you to use 64k or 128k context with zero local RAM impact.*

---

## 🧪 Running the Test Suite

Genesis includes 115 comprehensive automated tests:

```bash
# Run entire test suite
pytest

# Test research swarm specifically
pytest tests/test_research_swarm.py

# Test context management and scaling
pytest tests/test_context.py
```

---

## 📁 Repository Structure

```text
genesisAI/
├── Genesis.spec            # PyInstaller macOS build specification
├── install.sh              # Universal one-click installer for all Macs
├── pyproject.toml          # Package configuration and CLI entrypoints
├── requirements.txt        # Python dependency manifest
├── scripts/
│   └── build_dmg.sh        # Automated .app and .dmg packager
├── genesis/
│   ├── cli.py              # CLI entrypoint (genesis command)
│   ├── config.py           # Hardware constraints & memory ceilings
│   ├── core/
│   │   ├── agent.py        # Core GenesisAgent engine & LLM streaming
│   │   ├── context.py      # Dynamic context scaling & priority pruning
│   │   ├── health_guard.py # System health & RAM headroom watchdog
│   │   ├── research_swarm.py # 5-Phase process-oriented research swarm
│   │   ├── skills.py       # Modular skills registry
│   │   ├── subagents.py    # Hierarchical subagent workflows
│   │   ├── swarm.py        # Autonomous multi-agent coding loop
│   │   └── terminal.py     # Interactive prompt-toolkit REPL
│   ├── gui/
│   │   ├── api.py          # RPC bridge connecting frontend to Genesis
│   │   ├── app.py          # Native WebKit Cocoa window launcher
│   │   └── web/
│   │       └── index.html  # Responsive dark-mode dashboard UI
│   └── tools/
│       ├── file_ops.py     # Safe file viewing, editing, and diffing
│       ├── shell.py        # Sandboxed shell command execution
│       ├── uploader.py     # PDF & document context ingestion
│       └── web_research.py # Sovereign DuckDuckGo/Bing web scraping
└── tests/                  # 108 unit & integration test modules
```

---

## 📄 License

This project is licensed under the MIT License.
