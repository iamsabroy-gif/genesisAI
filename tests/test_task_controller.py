"""
Tests for Project Genesis Task Controller, Interruption, and Command-Queuing Engine.
Authored by Test-Harness (Staff QA Lead).
"""

from unittest.mock import MagicMock, patch
from genesis.core.agent import GenesisAgent
from genesis.core.task_controller import TaskController
from genesis.core.master_auth import MasterAuth


def test_parse_instruction_pipeline():
    agent = GenesisAgent()
    controller = TaskController(agent)

    # Single command
    res1 = controller.parse_instruction_pipeline("inspect tests/test_tools.py")
    assert res1 == ["inspect tests/test_tools.py"]

    # Chained pipeline
    res2 = controller.parse_instruction_pipeline(
        "search_code def test ;; run_command pytest tests/ ;; summarize results"
    )
    assert len(res2) == 3
    assert res2[0] == "search_code def test"
    assert res2[1] == "run_command pytest tests/"
    assert res2[2] == "summarize results"


def test_command_queue_operations():
    agent = GenesisAgent()
    controller = TaskController(agent)

    assert agent.get_queued_commands() == []
    
    count = controller.enqueue_instructions(["task 1", "task 2", "task 3"])
    assert count == 3
    assert agent.get_queued_commands() == ["task 1", "task 2", "task 3"]

    first = agent.pop_next_command()
    assert first == "task 1"
    assert agent.get_queued_commands() == ["task 2", "task 3"]

    cleared = agent.clear_command_queue()
    assert cleared == 2
    assert agent.get_queued_commands() == []


def test_master_signal_queue_commands():
    agent = GenesisAgent()
    auth = MasterAuth()
    context = {"agent": agent}

    assert auth.is_master_signal("!QUEUE run pytest")
    assert auth.is_master_signal("!QUEUE LIST")

    # Enqueue via signal
    out1, _ = auth.execute_master_signal("!QUEUE examine memory.db", context)
    assert "Enqueued instruction #1" in out1
    assert agent.get_queued_commands() == ["examine memory.db"]

    # List queue
    out2, _ = auth.execute_master_signal("!QUEUE LIST", context)
    assert "examine memory.db" in out2

    # Clear queue
    out3, _ = auth.execute_master_signal("!QUEUE CLEAR", context)
    assert "Command Queue cleared" in out3
    assert agent.get_queued_commands() == []


def test_interrupt_and_halt():
    agent = GenesisAgent()
    controller = TaskController(agent)

    assert not agent.is_aborted()
    msg = controller.interrupt_and_halt()
    assert agent.is_aborted()
    assert "MASTER OVERRIDE: Task interrupted" in msg


def test_execute_with_interrupt_protection_keyboard_interrupt():
    agent = GenesisAgent()
    controller = TaskController(agent)

    with patch.object(agent, "run_turn", side_effect=KeyboardInterrupt):
        result = controller.execute_with_interrupt_protection("long running task")
        assert "interrupted" in result.lower()
        assert agent.is_aborted()
