"""
Tests for Dataset Curator and Sleep Daemon Triggers.
Authored by Test-Harness.
"""

from curator import curate_trajectories
from genesis_sleep_daemon import evaluate_sleep_trigger_conditions


def test_curate_trajectories_execution():
    # Should successfully process without errors
    stats = curate_trajectories()
    assert "sft" in stats
    assert "self_correction" in stats
    assert "dpo" in stats


def test_sleep_daemon_trigger_evaluation():
    can_run, reason = evaluate_sleep_trigger_conditions(force=False)
    # On typical test runs with <20 trajectories, it reports insufficient trajectories
    assert isinstance(can_run, bool)
    assert isinstance(reason, str)

    # Force flag should always evaluate to True
    forced, msg = evaluate_sleep_trigger_conditions(force=True)
    assert forced is True
