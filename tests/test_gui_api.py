"""
Tests for Project Genesis Native macOS Desktop GUI API Bridge.
"""

import pytest
from unittest.mock import MagicMock, patch
from genesis.core.agent import GenesisAgent
from genesis.gui.api import GenesisDesktopApi


def test_gui_api_init():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    assert api.agent is agent
    assert api.window is None
    assert api._is_busy is False


def test_gui_api_init_session():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    session_data = api.init_session()

    assert "model" in session_data
    assert "used_tokens" in session_data
    assert "total_tokens" in session_data
    assert "ram_free_mb" in session_data
    assert "is_busy" in session_data
    assert session_data["is_busy"] is False


def test_gui_api_get_status():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    status = api.get_status()

    assert "model" in status
    assert "ram_free_mb" in status
    assert "usage_pct" in status
    assert "health_status" in status


def test_gui_api_execute_master_signal():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)

    res = api.execute_master_signal("!LOCK")
    assert res["signal"] == "!LOCK"
    assert res["read_only_lock"] is True

    res_unlock = api.execute_master_signal("!UNLOCK")
    assert res_unlock["signal"] == "!UNLOCK"
    assert res_unlock["read_only_lock"] is False


def test_gui_api_halt():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    res = api.halt()
    assert res["status"] == "halted"
    assert api._is_busy is False


def test_gui_api_clear_chat():
    agent = GenesisAgent()
    agent.messages = [{"role": "user", "content": "hi"}]
    api = GenesisDesktopApi(agent=agent)
    res = api.clear_chat()
    assert res["status"] == "cleared"
    assert len(agent.messages) == 0


def test_gui_api_emit_with_mock_window():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    api._emit("test_event", {"foo": "bar"})
    mock_window.evaluate_js.assert_called_once()
    called_js = mock_window.evaluate_js.call_args[0][0]
    assert "window.onGenesisEvent" in called_js
    assert "test_event" in called_js


def test_gui_api_get_research_formats():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    formats = api.get_research_formats()
    assert isinstance(formats, list)
    assert len(formats) == 5
    ids = [f["id"] for f in formats]
    assert "comprehensive" in ids
    assert "executive" in ids
    assert "technical" in ids


def test_gui_api_run_research_swarm_with_format():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    with patch("genesis.core.research_swarm.ResearchSwarmCoordinator.run_research_swarm", return_value={"status": "GOAL_ACHIEVED", "report_format": "executive"}) as mock_run:
        res = api.run_research_swarm("Quantum Computing", report_format="executive")
        assert res["status"] == "started"
        assert res["report_format"] == "executive"


def test_gui_api_send_prompt_research_formats_intercept():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    res = api.send_prompt("/research-formats")
    assert res["status"] == "completed"
    assert "Genesis Research Swarm: Available Report Formats" in res["response"]


def test_gui_api_run_research_swarm_with_starting_context():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    with patch("genesis.core.research_swarm.ResearchSwarmCoordinator.run_research_swarm", return_value={"status": "GOAL_ACHIEVED"}) as mock_run:
        res = api.run_research_swarm(
            "Solid-State Batteries",
            report_format="technical",
            target_urls=15,
            starting_context=["./paper.pdf", "https://example.com/seed"],
        )
        assert res["status"] == "started"
        assert res["has_starting_context"] is True


def test_gui_api_send_prompt_research_with_context_flag():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    with patch.object(api, "run_research_swarm", return_value={"status": "started"}) as mock_run:
        res = api.send_prompt("/research Solid-State Battery Commercialization --format executive --urls 15 --context https://arxiv.org/abs/1234,./notes.md")
        assert res["status"] == "started"
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "Solid-State Battery Commercialization"
        assert kwargs["report_format"] == "executive"
        assert kwargs["target_urls"] == 15
        assert "https://arxiv.org/abs/1234" in kwargs["starting_context"]
        assert "./notes.md" in kwargs["starting_context"]


def test_gui_api_pick_research_context():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    mock_window.create_file_dialog.return_value = ["/Users/test/paper.pdf", "/Users/test/docs"]
    api.set_window(mock_window)

    res = api.pick_research_context(folder_mode=False)
    assert res["status"] == "ok"
    assert len(res["paths"]) == 2
    assert "/Users/test/paper.pdf" in res["paths"]

