"""
Tests for Project Genesis Context and Token Budgeting.
Authored by Test-Harness (Staff QA Lead).
"""

from genesis.core.context import (
    estimate_tokens,
    estimate_messages_tokens,
    prune_context,
)


def test_estimate_tokens():
    text = "def calculate_sum(a: int, b: int) -> int:\n    return a + b\n"
    tokens = estimate_tokens(text)
    assert tokens > 0
    assert tokens < len(text)


def test_prune_context_retention():
    # Construct a conversation exceeding prune threshold
    messages = [
        {"role": "system", "content": "System prompt immutable anchor"},
        {"role": "user", "content": "Initial user goal"},
    ]

    # Add several intermediate turns with long tool outputs
    for i in range(10):
        messages.append({
            "role": "assistant",
            "content": f"Assistant step {i}",
            "tool_calls": [
                {"function": {"name": "run_command", "arguments": "{\"command\": \"test\"}"}}
            ],
        })
        messages.append({
            "role": "tool",
            "name": "run_command",
            "content": "output line\n" * 50,  # long tool output
        })

    pruned = prune_context(messages, trigger_tokens=200, target_tokens=150)

    # Immutability Check: system and initial user goal MUST be preserved
    assert pruned[0]["role"] == "system"
    assert pruned[1]["role"] == "user"
    assert "System prompt immutable anchor" in pruned[0]["content"]
    assert "Initial user goal" in pruned[1]["content"]


def test_context_usage_report_and_metrics():
    from genesis.core.context import get_context_usage, ContextUsageReport

    messages = [
        {"role": "system", "content": "You are a local coding agent."},
        {"role": "user", "content": "Write a python function to compute fibonacci numbers."},
        {"role": "assistant", "content": "Here is the code implementation:\ndef fib(n): ..."},
        {"role": "tool", "content": "Tests passed: 5/5 assertions green."},
    ]

    report = get_context_usage(messages, max_tokens=16384)
    assert isinstance(report, ContextUsageReport)
    assert report.total_tokens == 16384
    assert report.used_tokens > 0
    assert report.remaining_tokens == 16384 - report.used_tokens
    assert 0.0 < report.usage_percentage < 100.0
    assert not report.is_pruning_needed

    # Check breakdown categories
    assert "system" in report.breakdown
    assert "user" in report.breakdown
    assert "assistant" in report.breakdown
    assert "tool" in report.breakdown
    assert report.breakdown["system"] > 0
    assert report.breakdown["user"] > 0

    # Check visual rendering
    gauge = report.render_bar(width=20)
    assert "[" in gauge and "]" in gauge
    assert "░" in gauge or "█" in gauge

    badge = report.single_line_badge()
    assert "Context:" in badge
    assert "remaining" in badge

    summary = report.detailed_summary()
    assert "=== CONTEXT WINDOW USAGE ===" in summary
    assert "System Anchor" in summary
    assert "Tool Executions" in summary


def test_master_signal_context_command():
    from genesis.core.master_auth import MasterAuth
    from genesis.core.context import get_context_usage

    auth = MasterAuth()
    assert auth.is_master_signal("!CONTEXT")
    assert auth.is_master_signal("!context")

    messages = [
        {"role": "system", "content": "System prompt anchor."},
        {"role": "user", "content": "Hello agent."},
    ]
    usage = get_context_usage(messages)

    output, state = auth.execute_master_signal("!CONTEXT", {"context_usage": usage, "estimated_tokens": 100})
    assert state == "NO_TRANSITION"
    assert "=== CONTEXT WINDOW USAGE ===" in output
    assert "Remaining Buffer" in output

    status_out, _ = auth.execute_master_signal("!STATUS", {"context_usage": usage, "estimated_tokens": 100, "history_len": 2})
    assert "Context Window:" in status_out
    assert "Remaining:" in status_out


def test_parse_context_size():
    from genesis.core.context import parse_context_size, get_recommended_context_size

    assert parse_context_size("16k") == 16384
    assert parse_context_size("32k") == 32768
    assert parse_context_size("64k") == 65536
    assert parse_context_size("128k") == 131072
    assert parse_context_size("32768") == 32768
    assert parse_context_size("invalid") is None
    assert parse_context_size("500") is None  # below minimum threshold

    rec = get_recommended_context_size()
    assert rec in [8192, 16384, 32768, 65536]


def test_agent_dynamic_context_scaling():
    from genesis.core.agent import GenesisAgent
    agent = GenesisAgent()
    assert agent.max_context_tokens == 16384

    # Scale to 32k
    agent.set_max_context(32768)
    assert agent.max_context_tokens == 32768
    usage = agent.get_context_usage()
    assert usage.total_tokens == 32768
    assert usage.prune_trigger_tokens == int(32768 * 0.75)


def test_gui_api_context_scaling():
    from genesis.core.agent import GenesisAgent
    from genesis.gui.api import GenesisDesktopApi
    from unittest.mock import MagicMock

    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    res = api.send_prompt("/context 32k")
    assert res["status"] == "completed"
    assert "Context window scaled" in res["response"]
    assert agent.max_context_tokens == 32768


