"""
Tests for Auto-Verification Sub-Routine.
Authored by Test-Harness.
"""

import tempfile
from pathlib import Path
from genesis.tools.verifier import auto_verify_modification
from genesis.config import WORKSPACE_ROOT


def test_auto_verify_valid_syntax():
    # Test valid python file
    test_file = WORKSPACE_ROOT / "valid_test_script.py"
    test_file.write_text("def add(x, y):\n    return x + y\n")
    try:
        passed, msg = auto_verify_modification("valid_test_script.py")
        assert passed is True
        assert "Syntax: Valid" in msg
    finally:
        if test_file.exists():
            test_file.unlink()


def test_auto_verify_syntax_error():
    # Test invalid python syntax
    bad_file = WORKSPACE_ROOT / "broken_test_script.py"
    bad_file.write_text("def broken_syntax(\n")
    try:
        passed, msg = auto_verify_modification("broken_test_script.py")
        assert passed is False
        assert "FAILED: Syntax Error" in msg
    finally:
        if bad_file.exists():
            bad_file.unlink()
