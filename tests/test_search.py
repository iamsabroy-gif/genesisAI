"""
Tests for Code Search and Directory Listing.
Authored by Test-Harness.
"""

from genesis.tools.search import search_code, list_files


def test_search_code_found():
    res = search_code("class GenesisAgent", path="genesis")
    assert "agent.py" in res
    assert "class GenesisAgent" in res


def test_search_code_not_found():
    res = search_code("non_existent_symbol_12345_xyz", path="genesis")
    assert "No matches found" in res


def test_list_files_structure():
    res = list_files("genesis", max_depth=2)
    assert "Directory Tree" in res
    assert "core" in res
    assert "tools" in res
