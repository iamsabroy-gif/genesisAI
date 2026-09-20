"""
Project Genesis: Sovereign Skills Registry & Capability Catalog.
Defines and exposes all built-in capabilities, tools, and workflows for Genesis.
"""

from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

# Complete registry of all system skills and capabilities
GENESIS_SKILLS: List[Dict[str, Any]] = [
    {
        "id": "research_swarm",
        "name": "5-Phase Process-Oriented Research Swarm",
        "command": "/research <topic> [--format <type>] [--context <url|file|folder>]",
        "category": "Deep Research",
        "icon": "🔬",
        "description": "Multi-agent academic pipeline (Architect → Intelligence Recon → Systems Modeler → Red Team Auditor → Chief Editor) producing tailored Markdown dossiers across 5 formats. Supports starting context via uploaded files, folders, or seed URLs.",
        "tools": ["web_search", "web_scrape", "web_research", "vault_index_file", "convert_pdf_to_markdown"],
        "example": "/research Solid-State Battery Commercialization 2026 --format executive --context ./whitepaper.pdf",
    },
    {
        "id": "web_research",
        "name": "Autonomous Web Intelligence & Scraping",
        "command": "web search / research",
        "category": "Deep Research",
        "icon": "🌐",
        "description": "Zero-API-key search via DuckDuckGo, clean semantic HTML-to-Markdown web scraping, and multi-source synthesis into consolidated dossiers.",
        "tools": ["web_search", "web_scrape", "web_research"],
        "example": "Research the latest benchmarks of Apple M4 Max unified memory",
    },
    {
        "id": "code_engineering",
        "name": "Autonomous Code Engineering & Verification",
        "command": "genesis <prompt> / /pipeline",
        "category": "Engineering",
        "icon": "⚡",
        "description": "File inspection, surgical snippet patching, regex search, local test runner with automated syntax and pytest self-verification loops.",
        "tools": ["read_file", "write_file", "replace_snippet", "run_command", "search_code", "list_files"],
        "example": "Inspect genesis/core/agent.py and optimize context pruning",
    },
    {
        "id": "file_upload",
        "name": "Multi-File & Folder Ingestion Engine",
        "command": "/upload <path>",
        "category": "Knowledge Base",
        "icon": "📁",
        "description": "Batch ingests individual files or entire directory trees into the workspace, auto-converts PDFs to Markdown, and indexes everything into the vector vault.",
        "tools": ["upload_files_or_folder", "vault_index_file", "convert_pdf_to_markdown"],
        "example": "/upload ~/Documents/ProjectSpecs",
    },
    {
        "id": "vector_vault",
        "name": "Sovereign Vector Vault (Local RAG)",
        "command": "genesis vault / vault_search",
        "category": "Knowledge Base",
        "icon": "🏛️",
        "description": "Local TF-IDF vector database for semantic passage retrieval, code indexing, and document search without cloud embeddings.",
        "tools": ["vault_index_file", "vault_search", "vault_status"],
        "example": "genesis vault search 'context management window'",
    },
    {
        "id": "pdf_pipeline",
        "name": "PDF to Markdown Structural Parser",
        "command": "genesis pdf <file.pdf>",
        "category": "Knowledge Base",
        "icon": "📄",
        "description": "Converts PDF documents into clean, structured semantic Markdown prior to analysis, preventing context bloat and token exhaustion.",
        "tools": ["convert_pdf_to_markdown"],
        "example": "genesis pdf research_paper.pdf",
    },
    {
        "id": "swarm_coordinator",
        "name": "Empirical 4-Agent Swarm Coordinator",
        "command": "/swarm <goal>",
        "category": "Autonomous Agents",
        "icon": "🐝",
        "description": "Coordinated swarm (Researcher, Implementer, Tester, Judge) running iterative loops until tests and empirical exit criteria confirm success.",
        "tools": ["run_swarm", "run_command"],
        "example": "/swarm Add health watchdog unit tests and ensure 100% pass",
    },
    {
        "id": "task_dag",
        "name": "TaskDAG Goal Planner & Checkpoints",
        "command": "/plan <goal>",
        "category": "Autonomous Agents",
        "icon": "📋",
        "description": "Decomposes complex engineering goals into directed acyclic dependency graphs (DAG) with step-by-step execution and state checkpoints.",
        "tools": ["deliberate_plan", "run_command"],
        "example": "/plan Refactor the authentication subsystem to support OAuth2",
    },
    {
        "id": "osint_diligence",
        "name": "OSINT Background & Person Due Diligence",
        "command": "genesis person-search",
        "category": "Intelligence",
        "icon": "🕵️",
        "description": "Multi-pillar OSINT investigation for tutors, educators, or contractors. Scans web records, calculates 1-10 triangulation score, and creates safety checklist.",
        "tools": ["person_due_diligence"],
        "example": "genesis person-search 'Ramesh Sharma' --city 'Kolkata' --role 'Math tutor'",
    },
    {
        "id": "macos_automation",
        "name": "Native macOS GUI & Accessibility Engine",
        "command": "macos_*",
        "category": "macOS Native",
        "icon": "🍎",
        "description": "Programmatic desktop control using macOS Accessibility API without computer-vision overhead: inspect window hierarchy, click buttons, and type text.",
        "tools": ["macos_list_visible_apps", "macos_get_frontmost_window", "macos_inspect_app_elements", "macos_click_button", "macos_type_text", "macos_press_hotkey"],
        "example": "Show me the frontmost application and its interactive buttons",
    },
    {
        "id": "macos_bridge",
        "name": "macOS Calendar, Reminders & Clipboard Bridge",
        "command": "on-demand query",
        "category": "macOS Native",
        "icon": "🗓️",
        "description": "Strictly on-demand macOS integration. Queries Apple Calendar events, manages Apple Reminders, and reads/writes clipboard with auto-cleanup.",
        "tools": ["macos_read_clipboard", "macos_write_clipboard", "macos_list_calendar_events", "macos_list_reminders", "macos_add_reminder"],
        "example": "What events are on my calendar today?",
    },
    {
        "id": "model_manager",
        "name": "Dynamic Multi-Backend Model Switcher",
        "command": "/models / /model <name>",
        "category": "System & Engine",
        "icon": "🧠",
        "description": "Hot-swaps between local backends (Ollama, LM Studio, vLLM) and remote cloud APIs (OpenAI, DeepSeek, Groq, OpenRouter) with real-time model catalog scanning.",
        "tools": ["switch_model", "fetch_models"],
        "example": "/model qwen2.5-coder:7b",
    },
    {
        "id": "hardware_guard",
        "name": "Apple Silicon Hardware Health Watchdog",
        "command": "genesis health / /status",
        "category": "System & Engine",
        "icon": "🛡️",
        "description": "Real-time monitoring of unified RAM headroom, virtual memory swap, and memory pressure to prevent macOS freezes on 16GB systems.",
        "tools": ["check_system_health"],
        "example": "/status",
    },
    {
        "id": "master_protocol",
        "name": "Master Authorization Protocol (MAP)",
        "command": "!HALT / !LOCK / !REVERT",
        "category": "System & Engine",
        "icon": "🔐",
        "description": "Inviolable cryptographic signals (!HALT, !LOCK, !UNLOCK, !REVERT, !KILL, !PURGE) that preempt LLM inference and enforce absolute Master subordination.",
        "tools": ["execute_master_signal"],
        "example": "!LOCK (engages read-only safety mode)",
    },
    {
        "id": "training_flywheel",
        "name": "Autonomous MLX LoRA Training Flywheel",
        "command": "/train",
        "category": "Self-Evolution",
        "icon": "🎓",
        "description": "Curates gold trajectories from successful sessions, generates Alpaca-formatted SFT datasets, and triggers local MLX LoRA adapter fine-tuning.",
        "tools": ["curate_trajectories", "train_adapter"],
        "example": "/train",
    },
]


def get_skills_catalog() -> List[Dict[str, Any]]:
    """Return complete list of all registered Genesis skills."""
    return GENESIS_SKILLS


def format_skills_markdown() -> str:
    """Format skills catalog into structured Markdown."""
    lines = [
        "# ⚡ Genesis Sovereign Skills & Capabilities Catalog\n",
        "Genesis is equipped with built-in autonomous skills spanning research, engineering, and native macOS control.\n",
    ]

    # Group by category
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for skill in GENESIS_SKILLS:
        cat = skill["category"]
        categories.setdefault(cat, []).append(skill)

    for cat_name, skill_list in categories.items():
        lines.append(f"## {cat_name}\n")
        lines.append("| Skill | Trigger / Command | Description | Example |")
        lines.append("|---|---|---|---|")
        for s in skill_list:
            lines.append(f"| {s['icon']} **{s['name']}** | `{s['command']}` | {s['description']} | `{s['example']}` |")
        lines.append("")

    return "\n".join(lines)


def format_skills_table() -> Table:
    """Generate a Rich Table displaying all skills for terminal output."""
    table = Table(title="Genesis Sovereign Skills Catalog", border_style="cyan", header_style="bold cyan")
    table.add_column("Skill", style="bold white", width=26)
    table.add_column("Category", style="yellow", width=16)
    table.add_column("Command / Trigger", style="green", width=22)
    table.add_column("Description", style="dim white", width=42)

    for s in GENESIS_SKILLS:
        table.add_row(
            f"{s['icon']} {s['name']}",
            s["category"],
            f"{s['command']}",
            s["description"],
        )

    return table
