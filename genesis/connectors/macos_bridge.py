"""
Project Genesis: macOS Native Bridge Connector.
Provides zero-configuration local integration with macOS Calendar, Reminders, and Clipboard.
"""

import sys
import subprocess
from typing import Dict, Any, Callable, List
from genesis.connectors.base import BaseConnector


def macos_read_clipboard() -> str:
    """Read the current text contents of the macOS system clipboard."""
    try:
        res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        text = res.stdout.strip()
        if not text:
            return "Clipboard is empty."
        if len(text) > 2000:
            return text[:2000] + "\n... [Clipboard output truncated]"
        return text
    except Exception as e:
        return f"Error reading clipboard: {e}"


def macos_write_clipboard(text: str) -> str:
    """Copy the given text into the macOS system clipboard."""
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
        proc.communicate(input=text, timeout=5)
        return f"Successfully copied {len(text)} characters to the macOS clipboard."
    except Exception as e:
        return f"Error writing to clipboard: {e}"


def macos_list_reminders(completed: bool = False, max_results: int = 10) -> str:
    """List reminders from macOS Apple Reminders (cleanly and without keeping app open if not previously running)."""
    comp_str = "true" if completed else "false"
    script = f'''
    tell application "System Events"
        set wasRunning to (exists (processes where name is "Reminders"))
    end tell
    tell application "Reminders"
        set outputList to {{}}
        set matchedReminders to (every reminder whose completed is {comp_str})
        set maxCount to {max_results}
        set totalFound to count of matchedReminders
        if totalFound < maxCount then set maxCount to totalFound
        repeat with i from 1 to maxCount
            set r to item i of matchedReminders
            set end of outputList to (name of r)
        end repeat
    end tell
    if not wasRunning then
        tell application "Reminders" to quit
    end if
    return outputList
    '''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        output = res.stdout.strip()
        if res.returncode != 0 or not output:
            return "No active reminders found in Apple Reminders (or Reminders is empty)."
        return f"Apple Reminders ({'Completed' if completed else 'Active'}):\n{output}"
    except Exception as e:
        return f"Error querying Apple Reminders: {e}"


def macos_add_reminder(title: str, notes: str = "") -> str:
    """Add a new task/reminder to macOS Apple Reminders (cleanly and without keeping app open if not previously running)."""
    escaped_title = title.replace('"', '\\"')
    escaped_notes = notes.replace('"', '\\"')
    script = f'''
    tell application "System Events"
        set wasRunning to (exists (processes where name is "Reminders"))
    end tell
    tell application "Reminders"
        set defaultList to default list
        tell defaultList
            make new reminder with properties {{name:"{escaped_title}", body:"{escaped_notes}"}}
        end tell
    end tell
    if not wasRunning then
        tell application "Reminders" to quit
    end if
    return "Reminder created successfully"
    '''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return f"Successfully created Apple Reminder: '{title}'"
        return f"Could not create reminder: {res.stderr.strip()}"
    except Exception as e:
        return f"Error adding Apple Reminder: {e}"


def macos_list_calendar_events(days_ahead: int = 1) -> str:
    """List upcoming events from macOS Calendar (cleanly and without keeping app open if not previously running)."""
    script = f'''
    tell application "System Events"
        set wasRunning to (exists (processes where name is "Calendar"))
    end tell
    tell application "Calendar"
        set outputList to {{}}
        set startDate to (current date)
        set endDate to (startDate + ({days_ahead} * days))
        repeat with c in calendars
            tell c
                set evs to (every event whose start date ≥ startDate and start date ≤ endDate)
                repeat with ev in evs
                    set end of outputList to (summary of ev & " at " & (start date of ev as string))
                end repeat
            end tell
        end repeat
    end tell
    if not wasRunning then
        tell application "Calendar" to quit
    end if
    return outputList
    '''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        output = res.stdout.strip()
        if res.returncode != 0 or not output:
            return f"No calendar events found in the next {days_ahead} day(s)."
        return f"Upcoming Calendar Events (Next {days_ahead} day(s)):\n{output}"
    except Exception as e:
        return f"Error querying macOS Calendar: {e}"


class MacOSBridgeConnector(BaseConnector):
    """Zero-configuration connector for native macOS Calendar, Reminders, and Clipboard."""

    name = "macos_bridge"
    description = "Native macOS Bridge for Calendar, Reminders, and Clipboard"

    def is_configured(self) -> bool:
        # Standard on macOS Darwin
        return sys.platform == "darwin"

    def get_tool_map(self) -> Dict[str, Callable[..., Any]]:
        return {
            "macos_read_clipboard": macos_read_clipboard,
            "macos_write_clipboard": macos_write_clipboard,
            "macos_list_reminders": macos_list_reminders,
            "macos_add_reminder": macos_add_reminder,
            "macos_list_calendar_events": macos_list_calendar_events,
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "macos_read_clipboard",
                    "description": "Read text currently in the macOS system clipboard (pasteboard).",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "macos_write_clipboard",
                    "description": "Copy text directly into the macOS system clipboard.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to write into the clipboard.",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "macos_list_reminders",
                    "description": "List task reminders from macOS Apple Reminders app.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "completed": {
                                "type": "boolean",
                                "description": "Filter by completed status (default: False for active tasks).",
                                "default": False,
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of reminders to fetch (default: 10).",
                                "default": 10,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "macos_add_reminder",
                    "description": "Create and add a new reminder/to-do item into the macOS Apple Reminders app.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title or description of the task reminder.",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Optional notes or details for the reminder.",
                                "default": "",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "macos_list_calendar_events",
                    "description": "Query upcoming events and meetings from macOS Calendar app.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_ahead": {
                                "type": "integer",
                                "description": "Number of days ahead to search for events (default: 1).",
                                "default": 1,
                            }
                        },
                    },
                },
            },
        ]
