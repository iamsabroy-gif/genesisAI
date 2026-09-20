"""
File Operations Sandbox for Project Genesis.
Provides line-bounded reading, atomic writing, and snippet replacement.
"""

from pathlib import Path
from typing import Optional
from genesis.tools.safety import validate_path


def read_file(path: str, start_line: Optional[int] = 1, end_line: Optional[int] = 200) -> str:
    """Read a specific range of lines from a file with line numbers."""
    try:
        resolved = validate_path(path)
        if not resolved.is_file():
            return f"Error: File not found at '{path}'"

        lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)

        s_line = 1 if start_line is None else max(1, start_line)
        e_line = total_lines if end_line is None else min(total_lines, end_line)

        selected = lines[s_line - 1 : e_line]
        annotated = [f"{i + s_line}: {line}" for i, line in enumerate(selected)]
        header = f"[File: {resolved.name} | Showing lines {s_line}-{e_line} of {total_lines}]\n"
        return header + "\n".join(annotated)
    except Exception as e:
        return f"File Read Error: {e}"


def write_file(path: str, content: str) -> str:
    """Create a new file or completely overwrite an existing file."""
    try:
        resolved = validate_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {resolved.name}"
    except Exception as e:
        return f"File Write Error: {e}"


def replace_snippet(path: str, target: str, replacement: str) -> str:
    """
    Replace an exact snippet of code in a file.
    Fails if the target snippet is not found or is ambiguous (appears multiple times).
    """
    try:
        resolved = validate_path(path)
        if not resolved.is_file():
            return f"Error: File not found at '{path}'"

        text = resolved.read_text(encoding="utf-8")
        if target not in text:
            return f"Error: Target snippet not found in {resolved.name}. Ensure exact whitespace and line match."

        occurrences = text.count(target)
        if occurrences > 1:
            return (
                f"Error: Target snippet is ambiguous (found {occurrences} occurrences in {resolved.name}). "
                "Include more surrounding context lines to make the snippet unique."
            )

        updated = text.replace(target, replacement, 1)
        resolved.write_text(updated, encoding="utf-8")
        return f"Successfully applied patch to {resolved.name}"
    except Exception as e:
        return f"Patch Error: {e}"
