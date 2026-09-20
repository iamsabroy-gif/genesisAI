"""
Safety and Pre-Execution Validation Gates for Project Genesis.
Implements canonical path validation and command blocklists from algo.md.
"""

import re
from pathlib import Path
from genesis.config import WORKSPACE_ROOT, DANGEROUS_PATTERNS


class SafetyViolationError(Exception):
    """Raised when an operation violates workspace or command boundaries."""
    pass


def validate_path(path_str: str, allow_absolute_in_workspace: bool = True) -> Path:
    """
    Ensure the path resolves to a location within the designated workspace root.
    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    p = Path(path_str)
    if not p.is_absolute():
        resolved = (WORKSPACE_ROOT / p).resolve()
    else:
        resolved = p.resolve()

    # Enforce containment within WORKSPACE_ROOT or ~/.genesis
    allowed_roots = [
        WORKSPACE_ROOT,
        Path.home() / ".genesis",
    ]

    is_allowed = any(
        resolved == root or root in resolved.parents
        for root in allowed_roots
    )

    if not is_allowed:
        raise SafetyViolationError(
            f"Security Gate: Path '{path_str}' resolves outside authorized workspace: {resolved}"
        )

    return resolved


def validate_command(command: str) -> None:
    """
    Validates that a shell command does not match dangerous system patterns.
    """
    cmd_clean = command.strip()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            raise SafetyViolationError(
                f"Security Gate: Command blocked by safety policy matching '{pattern}': {command}"
            )
