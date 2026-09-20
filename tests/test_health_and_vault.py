"""
Unit tests for Project Genesis System Health Watchdog and Local Vector Vault.
"""

from pathlib import Path
import pytest

from genesis.core.health_guard import SystemHealthWatchdog, check_system_ceiling
from genesis.tools.vault_rag import (
    chunk_text,
    cosine_similarity,
    vault_index_file,
    vault_search,
    vault_status,
)
from genesis.tools.registry import TOOL_MAP, TOOL_SCHEMAS


def test_system_health_watchdog():
    stats = SystemHealthWatchdog.get_memory_stats()
    assert stats["total_ram_mb"] > 8000
    assert stats["available_ram_mb"] > 0
    assert "swap_used_mb" in stats

    status, msg, eval_stats = SystemHealthWatchdog.evaluate_health_ceiling()
    assert status in ["NOMINAL", "WARNING", "CRITICAL"]
    assert len(msg) > 0

    panel = SystemHealthWatchdog.format_status_panel()
    assert "Hardware Ceiling Status:" in panel
    assert "Apple Silicon Unified RAM:" in panel

    is_safe, _ = check_system_ceiling()
    assert isinstance(is_safe, bool)


def test_chunk_text():
    sample = "Paragraph 1 is here.\n\nParagraph 2 is here.\n\nParagraph 3 is here."
    chunks = chunk_text(sample, chunk_size=30, overlap=10)
    assert len(chunks) >= 2


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(cosine_similarity(v1, v2), 0.01) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3), 0.01) == 0.0
    assert cosine_similarity([], []) == 0.0


def test_vault_indexing_and_search(tmp_path: Path):
    doc = tmp_path / "quantum_notes.md"
    doc.write_text(
        "# Quantum Computing Architecture\n\n"
        "Superconducting qubits operate at millikelvin temperatures.\n\n"
        "Error correction codes protect quantum states from decoherence.",
        encoding="utf-8",
    )

    index_msg = vault_index_file(str(doc))
    assert "Vault Indexing Complete" in index_msg

    search_res = vault_search("millikelvin qubits", top_k=1)
    assert "quantum_notes.md" in search_res
    assert "superconducting qubits" in search_res.lower()

    status_str = vault_status()
    assert "Genesis Sovereign Vector Vault:" in status_str


def test_tool_registry_registration():
    assert "vault_index_file" in TOOL_MAP
    assert "vault_search" in TOOL_MAP
    assert "vault_status" in TOOL_MAP
    assert "check_system_health" in TOOL_MAP

    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert "vault_index_file" in schema_names
    assert "vault_search" in schema_names
    assert "vault_status" in schema_names
    assert "check_system_health" in schema_names
