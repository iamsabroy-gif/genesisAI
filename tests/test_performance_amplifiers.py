"""
Unit tests for Genesis Performance Amplifiers:
- Test-Time Compute Deliberation Engine
- Dynamic Task DAG with Checkpointing
- Hybrid RAG (Dense + BM25 RRF)
- Native macOS Accessibility UI Engine
"""

from pathlib import Path
import pytest

from genesis.core.deliberation import DeliberationEngine
from genesis.core.task_dag import TaskDAG, TaskNode
from genesis.tools.vault_rag import tokenize_terms, compute_bm25_scores, vault_search
from genesis.tools.macos_ui import (
    macos_list_visible_apps,
    macos_get_frontmost_window,
    macos_press_hotkey,
)
from genesis.tools.registry import TOOL_MAP, TOOL_SCHEMAS


def test_deliberation_engine():
    # Low risk
    trace_safe = DeliberationEngine.deliberate("Read config", "read_file('genesis/config.py')")
    assert trace_safe["approved"] is True
    assert trace_safe["risk_level"] == "LOW"

    # High risk
    trace_risk = DeliberationEngine.deliberate("Wipe database", "run_command('rm -rf /tmp/data')")
    assert trace_risk["approved"] is False
    assert trace_risk["risk_level"] == "HIGH"
    assert len(trace_risk["warnings"]) > 0

    formatted = DeliberationEngine.format_deliberation(trace_safe)
    assert "Deliberation Protocol [APPROVED]" in formatted


def test_task_dag_dependency_lifecycle(tmp_path: Path):
    dag = TaskDAG(goal="Build OAuth Integration", task_id="test_dag_1")
    
    # Step 1: Specs (no deps)
    dag.add_node("step_1", "Write Specs", "Define OAuth scopes")
    # Step 2: Implementation (depends on step 1)
    dag.add_node("step_2", "Code Auth Handler", "Implement token refresh", dependencies=["step_1"])
    # Step 3: Test (depends on step 2)
    dag.add_node("step_3", "Run Tests", "Run pytest auth test suite", dependencies=["step_2"])

    # Initially, only step_1 is ready
    ready = dag.get_ready_nodes()
    assert len(ready) == 1
    assert ready[0].node_id == "step_1"

    # Complete step_1
    dag.mark_completed("step_1", "Specs written.")
    ready = dag.get_ready_nodes()
    assert len(ready) == 1
    assert ready[0].node_id == "step_2"

    # Fail step_2
    dag.mark_failed("step_2", "Import error on oauthlib")
    assert dag.has_failed_nodes() is True
    assert dag.is_all_completed() is False

    # Render progress
    progress_md = dag.render_progress()
    assert "✅ **[step_1] Write Specs**" in progress_md
    assert "❌ **[step_2] Code Auth Handler**" in progress_md

    # Save and reload
    loaded = TaskDAG.load("test_dag_1")
    assert loaded is not None
    assert loaded.goal == "Build OAuth Integration"
    assert "step_1" in loaded.nodes


def test_bm25_sparse_scoring():
    query_terms = ["quantum", "qubit"]
    docs = [
        ["quantum", "mechanics", "qubit", "superposition"],
        ["python", "programming", "functions", "classes"],
        ["quantum", "cryptography", "key", "distribution"],
    ]
    scores = compute_bm25_scores(query_terms, docs)
    assert len(scores) == 3
    # Doc 0 contains both terms -> highest score
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    # Doc 1 has no matching terms -> score 0
    assert scores[1] == 0.0


def test_macos_accessibility_ui_inspection():
    apps = macos_list_visible_apps()
    assert "Running Visible macOS Applications:" in apps
    assert "- " in apps

    win = macos_get_frontmost_window()
    assert "Frontmost App:" in win


def test_all_tools_in_registry():
    expected_tools = [
        "deliberate_plan",
        "macos_list_visible_apps",
        "macos_get_frontmost_window",
        "macos_inspect_app_elements",
        "macos_click_button",
        "macos_type_text",
        "macos_press_hotkey",
        "vault_index_file",
        "vault_search",
        "vault_status",
        "check_system_health",
    ]
    for tool_name in expected_tools:
        assert tool_name in TOOL_MAP
        assert any(s["function"]["name"] == tool_name for s in TOOL_SCHEMAS)
