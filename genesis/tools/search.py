"""
Codebase Search and Directory Discovery Tools for Project Genesis.
Provides bounded ripgrep search and directory hierarchy inspection.
"""

import os
import re
from pathlib import Path
from typing import Optional, List
from genesis.config import WORKSPACE_ROOT
from genesis.tools.safety import validate_path


def search_code(pattern: str, path: Optional[str] = ".", max_results: int = 30) -> str:
    """
    Search for regex pattern across files within the workspace.
    Returns matched file paths, line numbers, and line snippets.
    """
    try:
        search_root = validate_path(path or ".")
        if not search_root.exists():
            return f"Error: Path '{path}' does not exist."

        regex = re.compile(pattern, re.IGNORECASE)
        matches: List[str] = []

        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}

        for root, dirs, files in os.walk(search_root):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                file_path = Path(root) / file
                # Skip binary files or large files
                if file_path.stat().st_size > 500_000:
                    continue

                try:
                    rel_path = file_path.relative_to(WORKSPACE_ROOT)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append(f"{rel_path}:{line_no}: {line.strip()[:150]}")
                                if len(matches) >= max_results:
                                    return (
                                        f"[Found {len(matches)}+ matches for pattern '{pattern}']\n"
                                        + "\n".join(matches)
                                        + f"\n... [Results capped at {max_results} matches]"
                                    )
                except Exception:
                    continue

        if not matches:
            return f"No matches found for pattern '{pattern}' in {path}."

        return f"[Found {len(matches)} matches for pattern '{pattern}']\n" + "\n".join(matches)

    except Exception as e:
        return f"Search Error: {e}"


def list_files(directory: Optional[str] = ".", max_depth: int = 2) -> str:
    """List directory structure up to max_depth, ignoring noisy directories."""
    try:
        target_dir = validate_path(directory or ".")
        if not target_dir.is_dir():
            return f"Error: '{directory}' is not a directory."

        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
        tree_lines = [f"[Directory Tree: {target_dir.relative_to(WORKSPACE_ROOT) if target_dir != WORKSPACE_ROOT else '.'}]"]

        def _walk(current: Path, depth: int, prefix: str = ""):
            if depth > max_depth:
                return
            items = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for i, item in enumerate(items):
                if item.name in ignore_dirs:
                    continue
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                tree_lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                if item.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    _walk(item, depth + 1, next_prefix)

        _walk(target_dir, 1)
        return "\n".join(tree_lines)

    except Exception as e:
        return f"List Files Error: {e}"
