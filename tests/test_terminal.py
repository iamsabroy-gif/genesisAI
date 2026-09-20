"""
Tests for Project Genesis Static User Terminal & Asynchronous REPL.
Authored by Test-Harness (Staff QA Lead).
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from genesis.core.agent import GenesisAgent
from genesis.core.terminal import GenesisTerminal


def test_terminal_initialization():
    agent = GenesisAgent()
    terminal = GenesisTerminal(agent=agent)
    assert terminal.agent is agent
    assert terminal.current_task is None
    assert terminal.is_shutting_down is False


def test_terminal_bottom_toolbar_rendering():
    agent = GenesisAgent()
    terminal = GenesisTerminal(agent=agent)

    toolbar_html = terminal.get_bottom_toolbar()
    formatted = toolbar_html.value
    assert "Context:" in formatted
    assert "16,384" in formatted
    assert "State:" in formatted
    assert "Queue:" in formatted
    assert "Model:" in formatted


def test_terminal_halt_active_execution():
    agent = GenesisAgent()
    terminal = GenesisTerminal(agent=agent)
    terminal.current_task = "long running research"

    msg = terminal.halt_active_execution()
    assert terminal.current_task is None
    assert "MASTER OVERRIDE: Task interrupted" in msg
    assert agent.is_aborted()


@pytest.mark.anyio
async def test_terminal_task_worker_lifecycle():
    agent = GenesisAgent()
    terminal = GenesisTerminal(agent=agent)

    # Put a mocked command into queue
    await terminal._task_queue.put("test task")

    with patch.object(agent, "run_turn", return_value="Mocked task output"):
        # Run worker for one iteration
        worker_task = asyncio.create_task(terminal._execute_task_worker())
        await asyncio.sleep(0.1)

        terminal.is_shutting_down = True
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    assert terminal.current_task is None
