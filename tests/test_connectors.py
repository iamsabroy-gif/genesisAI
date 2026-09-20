"""Unit tests for the Universal Connector Hub and macOS Bridge."""

import sys
from genesis.connectors.base import BaseConnector
from genesis.connectors.hub import ConnectorHub, get_default_hub
from genesis.connectors.macos_bridge import (
    MacOSBridgeConnector,
    macos_read_clipboard,
    macos_write_clipboard,
    macos_list_reminders,
    macos_list_calendar_events,
)


def test_connector_hub_registration():
    hub = ConnectorHub()
    connectors = hub.list_connectors()
    assert len(connectors) >= 1
    assert any(c["name"] == "macos_bridge" for c in connectors)

    tool_map = hub.get_active_tool_map()
    assert "macos_read_clipboard" in tool_map
    assert "macos_write_clipboard" in tool_map
    assert "macos_list_reminders" in tool_map
    assert "macos_list_calendar_events" in tool_map


def test_macos_clipboard_read_write():
    if sys.platform != "darwin":
        return
    test_msg = "Genesis Connector Test String"
    write_res = macos_write_clipboard(test_msg)
    assert "Successfully copied" in write_res

    read_res = macos_read_clipboard()
    assert test_msg in read_res


def test_macos_reminders_and_calendar_safe_queries():
    from unittest.mock import patch, MagicMock

    # Verify that reminders and calendar queries handle subprocess outputs safely without launching real GUI apps
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Test Task 1, Test Task 2"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        reminders_out = macos_list_reminders(completed=False, max_results=2)
        assert "Test Task 1" in reminders_out

        mock_proc.stdout = "Team Sync at Monday, September 21, 2026"
        calendar_out = macos_list_calendar_events(days_ahead=1)
        assert "Team Sync" in calendar_out


def test_calendar_and_reminders_schema_isolation():
    from genesis.tools.registry import get_schemas_for_task, CALENDAR_TOOLS, TOOL_SCHEMAS
    from genesis.connectors.hub import get_default_hub

    hub = get_default_hub()
    all_schemas = list(TOOL_SCHEMAS) + hub.get_active_tool_schemas()

    # Coding / general prompt should NEVER receive calendar tools
    coding_schemas = get_schemas_for_task("Fix the authorization bug in auth.py", all_schemas)
    coding_names = {s["function"]["name"] for s in coding_schemas}
    assert not (coding_names & CALENDAR_TOOLS), f"Leaked: {coding_names & CALENDAR_TOOLS}"

    # General conversation should NEVER receive calendar tools
    general_schemas = get_schemas_for_task("Hello Genesis, what is your status?", all_schemas)
    general_names = {s["function"]["name"] for s in general_schemas}
    assert not (general_names & CALENDAR_TOOLS), f"Leaked: {general_names & CALENDAR_TOOLS}"

    # Explicit calendar request SHOULD receive calendar tools
    cal_schemas = get_schemas_for_task("What events are on my calendar today?", all_schemas)
    cal_names = {s["function"]["name"] for s in cal_schemas}
    assert "macos_list_calendar_events" in cal_names

    # Explicit reminder/task request SHOULD receive reminders tools
    rem_schemas = get_schemas_for_task("Show me my to-do reminders", all_schemas)
    rem_names = {s["function"]["name"] for s in rem_schemas}
    assert "macos_list_reminders" in rem_names

