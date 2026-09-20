"""
Tool Registry and Schema Definitions for Project Genesis.
Standard OpenAI-compatible JSON function definitions.
"""

from typing import Dict, Any, Callable
from genesis.tools.file_ops import read_file, write_file, replace_snippet
from genesis.tools.shell import run_command
from genesis.tools.search import search_code, list_files
from genesis.tools.gmail import gmail_status, gmail_get_integration_plan

TOOL_MAP: Dict[str, Callable[..., Any]] = {
    "read_file": read_file,
    "write_file": write_file,
    "replace_snippet": replace_snippet,
    "run_command": run_command,
    "search_code": search_code,
    "list_files": list_files,
    "gmail_status": gmail_status,
    "gmail_get_integration_plan": gmail_get_integration_plan,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read line-numbered contents of a file within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to the file to read.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional 1-indexed starting line number.",
                        "default": 1,
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional 1-indexed ending line number.",
                        "default": 200,
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the target file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The exact full file contents to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_snippet",
            "description": "Replace an exact target snippet in a file with new replacement code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to patch.",
                    },
                    "target": {
                        "type": "string",
                        "description": "The exact code block to search for and replace.",
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The replacement code block.",
                    },
                },
                "required": ["path", "target", "replacement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command locally in the workspace (tests, git, build, linters).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact command line string to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a regex or string pattern across files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex or substring pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Relative subdirectory to search within (defaults to workspace root).",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Inspect workspace directory structure and file tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Target directory to list (defaults to workspace root).",
                        "default": ".",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum folder traversal depth (defaults to 2).",
                        "default": 2,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_status",
            "description": "Check configuration and connection status of the sovereign local Gmail adapter.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_get_integration_plan",
            "description": "Retrieve the technical engineering blueprint and setup options to connect Genesis with Gmail.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

from genesis.tools.web_research import web_search, web_scrape, web_research
from genesis.tools.person_diligence import person_due_diligence
from genesis.tools.pdf_converter import convert_pdf_to_markdown

TOOL_MAP["web_search"] = web_search
TOOL_MAP["web_scrape"] = web_scrape
TOOL_MAP["web_research"] = web_research
TOOL_MAP["person_due_diligence"] = person_due_diligence
TOOL_MAP["convert_pdf_to_markdown"] = convert_pdf_to_markdown

TOOL_SCHEMAS.extend([
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web using DuckDuckGo (zero API key needed). Returns titles, snippets, and clean URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query keywords.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": "Scrape any webpage and extract clean, readable semantic Markdown, stripping ads, scripts, and navigation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP or HTTPS URL to scrape.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters to extract to protect context window (default: 4000).",
                        "default": 4000,
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_research",
            "description": "Perform multi-source autonomous web research on a topic: searches, scrapes top pages, and builds a consolidated dossier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or technical question to research.",
                    },
                    "max_sources": {
                        "type": "integer",
                        "description": "Number of sources to scrape and synthesize (default: 3).",
                        "default": 3,
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "person_due_diligence",
            "description": "Perform OSINT background verification on an educator, tutor, or contractor. Scans professional, tutoring, and academic pillars, calculates a 1-10 triangulation score, generates safety checklist, and archives to vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full name of the individual to investigate.",
                    },
                    "location": {
                        "type": "string",
                        "description": "City, area, or locality (e.g., 'Kolkata', 'Bangalore', 'Salt Lake').",
                        "default": "",
                    },
                    "affiliation": {
                        "type": "string",
                        "description": "Subject, school, or organization (e.g., 'Math teacher', 'Physics tutor', 'DPS').",
                        "default": "",
                    },
                    "identifier": {
                        "type": "string",
                        "description": "Known phone number, email handle, or unique ID to resolve collisions.",
                        "default": "",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_pdf_to_markdown",
            "description": "Convert any PDF document into clean, structured Markdown prior to reading or performing analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the target PDF file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional destination Markdown (.md) path. Defaults to <pdf_stem>.md adjacent to PDF.",
                        "default": "",
                    },
                },
                "required": ["pdf_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vault_index_file",
            "description": "Index a code file, markdown file, or text document into the local sovereign vector vault for semantic search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to index into the vector vault.",
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Maximum characters per chunk (default: 800).",
                        "default": 800,
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vault_search",
            "description": "Perform local semantic vector search against indexed files in the vault. Retrieves top matching passages without exceeding context limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query or code concept to search for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top matching passages to return (default: 3).",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vault_status",
            "description": "Check current status and statistics of the local sovereign vector vault (documents indexed, chunks, size).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_system_health",
            "description": "Check real-time hardware health (Unified RAM headroom, swap usage, CPU load, and ceiling warning) to prevent system freezes.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deliberate_plan",
            "description": "Execute internal Test-Time deliberation (risk analysis, edge-case evaluation, and pre-flight validation) before performing high-impact actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "What you are trying to accomplish.",
                    },
                    "proposed_action": {
                        "type": "string",
                        "description": "The specific tool calls or modifications proposed.",
                    },
                },
                "required": ["intent", "proposed_action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_list_visible_apps",
            "description": "List all running applications visible in the macOS GUI.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_get_frontmost_window",
            "description": "Inspect the active frontmost application and window title on macOS.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_inspect_app_elements",
            "description": "Inspect buttons and menu bar hierarchy of a running macOS app via accessibility tree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the target running app (e.g. 'Finder', 'Safari', 'Terminal').",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_click_button",
            "description": "Click a named button in a running macOS application window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Target app name.",
                    },
                    "button_name": {
                        "type": "string",
                        "description": "Exact label of the button to click.",
                    },
                },
                "required": ["app_name", "button_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_type_text",
            "description": "Type text into the focused field or application window on macOS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to keystroke.",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "macos_press_hotkey",
            "description": "Trigger a keyboard shortcut in the active macOS application (e.g. key='s', modifier='command down').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key character (e.g. 's', 'c', 'v', 'w').",
                    },
                    "modifier": {
                        "type": "string",
                        "description": "Modifier clause (e.g. 'command down', 'option down', 'control down', 'shift down').",
                        "default": "command down",
                    },
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upload_files_or_folder",
            "description": "Ingest and index any file or entire folder into the workspace, auto-converting PDFs to Markdown and storing chunks in the Vector Vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the target file or directory to ingest.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_skills",
            "description": "List all active Sovereign Skills, capabilities, and slash commands available in Genesis.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
])

from genesis.tools.vault_rag import vault_index_file, vault_search, vault_status
from genesis.core.health_guard import SystemHealthWatchdog
from genesis.core.deliberation import DeliberationEngine
from genesis.tools.uploader import upload_files_or_folder
from genesis.core.skills import format_skills_markdown
from genesis.tools.macos_ui import (
    macos_list_visible_apps,
    macos_get_frontmost_window,
    macos_inspect_app_elements,
    macos_click_button,
    macos_type_text,
    macos_press_hotkey,
)

TOOL_MAP["vault_index_file"] = vault_index_file
TOOL_MAP["vault_search"] = vault_search
TOOL_MAP["vault_status"] = vault_status
TOOL_MAP["check_system_health"] = lambda: SystemHealthWatchdog.format_status_panel()
TOOL_MAP["deliberate_plan"] = lambda intent, proposed_action: DeliberationEngine.format_deliberation(
    DeliberationEngine.deliberate(intent, proposed_action)
)
TOOL_MAP["upload_files_or_folder"] = upload_files_or_folder
TOOL_MAP["show_skills"] = lambda: format_skills_markdown()
TOOL_MAP["macos_list_visible_apps"] = macos_list_visible_apps
TOOL_MAP["macos_get_frontmost_window"] = macos_get_frontmost_window
TOOL_MAP["macos_inspect_app_elements"] = macos_inspect_app_elements
TOOL_MAP["macos_click_button"] = macos_click_button
TOOL_MAP["macos_type_text"] = macos_type_text
TOOL_MAP["macos_press_hotkey"] = macos_press_hotkey


# ── C4 + M2: Dynamic Schema Loading ─────────────────────────────────────────
# Tools are grouped by task domain. Only the relevant subset is loaded per turn,
# reducing per-call schema token overhead from ~600 → ~200 tokens.

CALENDAR_TOOLS = {"macos_list_calendar_events", "macos_list_reminders", "macos_add_reminder"}

# Always-present core tools regardless of task type
_CORE_TOOLS = {
    "read_file", "write_file", "replace_snippet",
    "run_command", "list_files", "search_code",
    "check_system_health", "deliberate_plan",
    "upload_files_or_folder", "show_skills",
}

# Task-domain → additional tool names to include beyond core
TOOL_GROUPS: Dict[str, set] = {
    "code":     set(),  # Core tools are sufficient for coding
    "research": {"web_search", "web_scrape", "web_research",
                  "vault_search", "vault_index_file", "vault_status"},
    "personal": {"macos_list_visible_apps", "macos_get_frontmost_window",
                  "macos_inspect_app_elements", "macos_click_button",
                  "macos_type_text", "macos_press_hotkey",
                  "gmail_status", "gmail_get_integration_plan"},
    "calendar": CALENDAR_TOOLS,
    "pdf":      {"convert_pdf_to_markdown", "vault_index_file",
                  "vault_search", "vault_status"},
    "diligence": {"person_due_diligence", "web_search", "web_research"},
}

# Keyword patterns used to classify a prompt into a task domain
_TASK_CLASSIFIERS: Dict[str, list] = {
    "research":  ["research", "search", "find", "look up", "web", "google",
                  "article", "news", "what is", "explain", "learn"],
    "personal":  ["clipboard", "frontmost window", "click button", "keystroke",
                  "hotkey", "accessibility tree", "active window", "gmail", "email"],
    "calendar":  ["calendar", "reminder", "reminders", "schedule", "meeting",
                  "meetings", "event", "events", "to-do", "todo", "appointment", "appointments"],
    "pdf":       ["pdf", ".pdf", "document", "convert", "extract text"],
    "diligence": ["background", "due diligence", "person", "verify", "osint",
                  "tutor", "teacher", "contractor"],
}


def get_schemas_for_task(prompt: str, available_schemas: list = None) -> list:
    """
    C4: Classify prompt and return only the relevant tool schema subset.
    Calendar and reminders tools are strictly isolated: only loaded when
    the user's prompt explicitly requests calendar/tasks/reminders.

    Token savings: ~600 → ~200 per specialized task turn.
    """
    schema_pool = available_schemas if available_schemas is not None else TOOL_SCHEMAS
    schema_by_name = {s["function"]["name"]: s for s in schema_pool}

    prompt_lower = prompt.lower()
    matched_groups = []

    for domain, keywords in _TASK_CLASSIFIERS.items():
        if any(kw in prompt_lower for kw in keywords):
            matched_groups.append(domain)

    # If prompt is ambiguous or general coding/system task, return standard schemas
    # EXCLUDING calendar/reminders tools to prevent spontaneous invocations
    if not matched_groups or len(matched_groups) > 2:
        return [s for s in schema_pool if s["function"]["name"] not in CALENDAR_TOOLS]

    # Build the tool name set: core + matched domain extras
    active_names = set(_CORE_TOOLS)
    for domain in matched_groups:
        active_names.update(TOOL_GROUPS.get(domain, set()))

    return [schema_by_name[n] for n in active_names if n in schema_by_name]
