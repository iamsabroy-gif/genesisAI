"""
Tests for Project Genesis Safety Gates.
Authored by Test-Harness (Staff QA Lead).
"""

import pytest
from genesis.tools.safety import validate_path, validate_command, SafetyViolationError
from genesis.config import WORKSPACE_ROOT


def test_validate_path_inside_workspace():
    test_path = "sample.py"
    resolved = validate_path(test_path)
    assert resolved == (WORKSPACE_ROOT / test_path).resolve()


def test_validate_path_traversal_blocked():
    with pytest.raises(SafetyViolationError) as exc_info:
        validate_path("../../../../../etc/passwd")
    assert "Security Gate" in str(exc_info.value)


def test_validate_command_allowed():
    # Standard engineering commands should pass without exception
    validate_command("pytest -v")
    validate_command("git status")
    validate_command("npm test")
    validate_command("python3 -m unittest")


def test_validate_command_dangerous_blocked():
    dangerous_commands = [
        "rm -rf /",
        "rm -rf /System",
        "dd if=/dev/zero of=/dev/sda",
        "diskutil eraseDisk JHFS+ Untitled /dev/disk2",
    ]
    for cmd in dangerous_commands:
        with pytest.raises(SafetyViolationError):
            validate_command(cmd)
