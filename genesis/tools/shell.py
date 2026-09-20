"""
Sandboxed Subprocess Runner for Project Genesis.
Enforces command validation, execution timeouts, and output truncation.
"""

import os
import subprocess
from typing import Optional
from genesis.config import (
    WORKSPACE_ROOT,
    COMMAND_TIMEOUT_SECONDS,
    MAX_COMMAND_OUTPUT_CHARS,
)
from genesis.tools.safety import validate_command


import threading

_PROCESS_LOCK = threading.Lock()
_ACTIVE_PROCESSES = set()


def terminate_active_processes() -> int:
    """
    Instantly kill all active subprocesses spawned by Genesis tools.
    Used by !HALT, Ctrl+C interrupt traps, and Kill Switch.
    """
    killed_count = 0
    with _PROCESS_LOCK:
        for p in list(_ACTIVE_PROCESSES):
            try:
                p.kill()
                killed_count += 1
            except Exception:
                pass
        _ACTIVE_PROCESSES.clear()
    return killed_count


def run_command(command: str, cwd: Optional[str] = None) -> str:
    """
    Execute a shell command locally within the workspace directory.
    Validates command safety and truncates oversized output to protect context tokens.
    Tracks active process to enable deterministic cancellation via !HALT / Ctrl+C.
    """
    try:
        validate_command(command)
        
        target_cwd = WORKSPACE_ROOT if cwd is None else cwd
        
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=target_cwd,
        )

        with _PROCESS_LOCK:
            _ACTIVE_PROCESSES.add(proc)

        try:
            stdout, stderr = proc.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
        finally:
            with _PROCESS_LOCK:
                _ACTIVE_PROCESSES.discard(proc)

        combined = ((stdout or "") + (stderr or "")).strip()

        if not combined:
            return f"Command executed successfully (exit code {proc.returncode}, no output)."

        if len(combined) > MAX_COMMAND_OUTPUT_CHARS:
            truncated = combined[:MAX_COMMAND_OUTPUT_CHARS]
            return (
                f"{truncated}\n... [Output truncated at {MAX_COMMAND_OUTPUT_CHARS} chars; "
                f"total {len(combined)} chars | Exit code {proc.returncode}]"
            )

        return f"{combined}\n[Exit code: {proc.returncode}]"

    except subprocess.TimeoutExpired:
        with _PROCESS_LOCK:
            if 'proc' in locals():
                try:
                    proc.kill()
                except Exception:
                    pass
                _ACTIVE_PROCESSES.discard(proc)
        return f"Error: Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Shell Execution Error: {e}"

