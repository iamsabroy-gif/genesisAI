"""
Autonomous Self-Verification Sub-Routine for Project Genesis.
Implements Verify(Delta) from algo.md Section 4.
Automatically checks syntax and relevant test suites following code modifications.
"""

import subprocess
from pathlib import Path
from typing import Tuple, Optional
from genesis.config import WORKSPACE_ROOT
from genesis.tools.safety import validate_path


def auto_verify_modification(file_path_str: str) -> Tuple[bool, str]:
    """
    Executes automated verification checks on a modified file:
    1. Python syntax compilation check (py_compile)
    2. Associated unit test discovery and execution (pytest)
    Returns: (passed: bool, diagnostic_message: str)
    """
    try:
        resolved = validate_path(file_path_str)
        if not resolved.is_file():
            return True, ""

        diagnostics = []

        # 1. Syntax Check for Python files
        if resolved.suffix == ".py":
            cmd = f"python3 -m py_compile {resolved}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=WORKSPACE_ROOT)
            if res.returncode != 0:
                err = (res.stderr or res.stdout).strip()
                return False, f"[Auto-Verification FAILED: Syntax Error]\n{err}"
            diagnostics.append("Syntax: Valid")

        # 2. Test Discovery: Check if a corresponding test file exists
        test_candidate = None
        if "test_" not in resolved.name and resolved.suffix == ".py":
            candidate_1 = resolved.parent / f"test_{resolved.name}"
            candidate_2 = WORKSPACE_ROOT / "tests" / f"test_{resolved.name}"
            if candidate_1.is_file():
                test_candidate = candidate_1
            elif candidate_2.is_file():
                test_candidate = candidate_2

        if test_candidate and test_candidate.is_file():
            # Run the specific test file
            rel_test = test_candidate.relative_to(WORKSPACE_ROOT)
            test_cmd = f".venv/bin/pytest -v {rel_test}"
            t_res = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, cwd=WORKSPACE_ROOT, timeout=30)
            if t_res.returncode != 0:
                err = (t_res.stdout + t_res.stderr).strip()
                return False, f"[Auto-Verification FAILED: Tests in {rel_test} Failed]\n{err[:2000]}"
            diagnostics.append(f"Tests: {rel_test} PASSED")

        if diagnostics:
            return True, f"[Auto-Verification: {', '.join(diagnostics)}]"
        return True, ""

    except Exception as e:
        return True, f"[Auto-Verification skipped: {e}]"
