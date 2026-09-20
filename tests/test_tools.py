"""
Tests for Project Genesis Tool Registry.
Authored by Test-Harness (Staff QA Lead).
"""

import os
from pathlib import Path
from genesis.tools.file_ops import read_file, write_file, replace_snippet
from genesis.tools.shell import run_command
from genesis.config import WORKSPACE_ROOT

TEMP_TEST_FILE = "genesis_test_artifact.txt"


def test_write_and_read_file():
    content = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    res = write_file(TEMP_TEST_FILE, content)
    assert "Successfully wrote" in res

    read_res = read_file(TEMP_TEST_FILE, start_line=2, end_line=4)
    assert "2: line 2" in read_res
    assert "3: line 3" in read_res
    assert "4: line 4" in read_res
    assert "1: line 1" not in read_res


def test_replace_snippet_success():
    orig_content = "def hello():\n    return 'old'\n"
    write_file(TEMP_TEST_FILE, orig_content)

    res = replace_snippet(TEMP_TEST_FILE, "return 'old'", "return 'new'")
    assert "Successfully applied patch" in res

    updated = (WORKSPACE_ROOT / TEMP_TEST_FILE).read_text()
    assert "return 'new'" in updated


def test_replace_snippet_ambiguous_failure():
    ambiguous_content = "item = 1\nitem = 1\n"
    write_file(TEMP_TEST_FILE, ambiguous_content)

    res = replace_snippet(TEMP_TEST_FILE, "item = 1", "item = 2")
    assert "ambiguous" in res.lower()

    # Cleanup
    p = WORKSPACE_ROOT / TEMP_TEST_FILE
    if p.exists():
        p.unlink()


def test_run_command_truncation():
    # Generate 1000 characters and check output handling
    res = run_command("python3 -c 'print(\"A\" * 5000)'")
    assert "truncated" in res.lower() or "5000 chars" in res.lower()
