"""
Tests for Project Genesis Multi-Agent Swarm Orchestrator.
Authored by Test-Harness.
"""

from genesis.core.swarm import SwarmCoordinator, SwarmWorker


def test_swarm_worker_initialization():
    worker = SwarmWorker("Tester", "QA Lead", "Execute tests")
    assert worker.name == "Tester"
    assert worker.role_title == "QA Lead"
    assert worker.system_prompt == "Execute tests"


def test_swarm_coordinator_initialization():
    coordinator = SwarmCoordinator()
    assert "researcher" in coordinator.workers
    assert "implementer" in coordinator.workers
    assert "tester" in coordinator.workers
    assert "judge" in coordinator.workers
    assert coordinator.agent is not None


def test_swarm_report_goal_and_context_tracking():
    from unittest.mock import patch, MagicMock

    coordinator = SwarmCoordinator()

    # Mock agent.run_turn to simulate successful research, report creation, verification, and judge pass
    responses = [
        "Researcher notes on ethanol blending: E10/E20 mandates, sugarcane feedstock, 20% blending target.",
        "Created ethanol_blending_report.md with complete breakdown.",
        "ls -lh ethanol_blending_report.md: file exists, 2.4KB, 450 words.",
        "GOAL_ACHIEVED: YES - Complete report generated and verified on disk.",
    ]

    with patch.object(coordinator.agent, "run_turn", side_effect=responses):
        dossier = coordinator.run_swarm("give me a complete report on ethanol blending", max_rounds=2)
        assert dossier["status"] == "GOAL_ACHIEVED"
        assert len(dossier["rounds"]) == 1
        assert dossier["rounds"][0]["round"] == 1
        assert len(dossier["rounds"][0]["actions"]) == 4
        assert dossier["rounds"][0]["actions"][3]["worker"] == "judge"

