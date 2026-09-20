"""
Project Genesis: Native macOS Accessibility & UI Automation Engine.
Enables programmatic desktop control without computer-vision latency or GPU memory overhead.
Uses macOS System Events and CoreGraphics AppleScript primitives.
"""

import subprocess
import shlex
from typing import List, Dict, Any, Optional


def run_applescript(script: str) -> Tuple[bool, str]:
    """Execute an AppleScript snippet securely via osascript."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Error: AppleScript execution timed out (10s)."
    except Exception as e:
        return False, f"Error: Failed to execute AppleScript: {e}"


def macos_list_visible_apps() -> str:
    """List all currently running applications visible in the macOS GUI."""
    script = 'tell application "System Events" to get name of every process whose visible is true'
    ok, out = run_applescript(script)
    if not ok:
        return f"Error listing visible apps: {out}"
    apps = [a.strip() for a in out.split(",")]
    lines = ["# Running Visible macOS Applications:"]
    for app in apps:
        lines.append(f"- {app}")
    return "\n".join(lines)


def macos_get_frontmost_window() -> str:
    """Get the name and active window of the current frontmost application."""
    script = '''
    tell application "System Events"
        set frontApp to first process whose frontmost is true
        set appName to name of frontApp
        set winTitle to "No active window"
        try
            set winTitle to name of front window of frontApp
        end try
        return appName & " ||| " & winTitle
    end tell
    '''
    ok, out = run_applescript(script)
    if not ok:
        return f"Error getting frontmost window: {out}"
    parts = out.split(" ||| ")
    app_name = parts[0] if len(parts) > 0 else "Unknown"
    win_title = parts[1] if len(parts) > 1 else "Unknown"
    return f"Frontmost App: **{app_name}** | Active Window: `{win_title}`"


def macos_inspect_app_elements(app_name: str) -> str:
    """
    Inspect the interactive UI elements (buttons, menus, text fields) of an application window.
    """
    clean_app = app_name.strip().replace('"', '\\"')
    script = f'''
    tell application "System Events"
        if not (exists process "{clean_app}") then
            return "APP_NOT_RUNNING"
        end if
        tell process "{clean_app}"
            set btnList to {{}}
            try
                set btnList to name of every button of front window
            end try
            set menuList to {{}}
            try
                set menuList to name of every menu bar item of menu bar 1
            end try
            return (btnList as string) & " ||| " & (menuList as string)
        end tell
    end tell
    '''
    ok, out = run_applescript(script)
    if not ok:
        return f"Error inspecting UI elements for '{app_name}': {out}"
    if out == "APP_NOT_RUNNING":
        return f"Application '{app_name}' is not currently running."

    parts = out.split(" ||| ")
    buttons = parts[0].strip() if len(parts) > 0 else "None detected"
    menu_items = parts[1].strip() if len(parts) > 1 else "None detected"

    return (
        f"# UI Accessibility Hierarchy for '{app_name}':\n"
        f"- **Buttons Detected**: {buttons or 'None'}\n"
        f"- **Menu Bar Items**: {menu_items or 'None'}"
    )


def macos_click_button(app_name: str, button_name: str) -> str:
    """
    Click a specific button in a running application window via accessibility tree.
    """
    clean_app = app_name.strip().replace('"', '\\"')
    clean_btn = button_name.strip().replace('"', '\\"')

    script = f'''
    tell application "System Events"
        tell process "{clean_app}"
            set frontmost to true
            click button "{clean_btn}" of front window
        end tell
    end tell
    '''
    ok, out = run_applescript(script)
    if not ok:
        return f"Failed to click button '{button_name}' in '{app_name}': {out}"
    return f"Successfully clicked button '{button_name}' in application '{app_name}'."


def macos_type_text(text: str) -> str:
    """
    Type text into the currently focused window or field.
    """
    clean_text = text.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''
    tell application "System Events"
        keystroke "{clean_text}"
    end tell
    '''
    ok, out = run_applescript(script)
    if not ok:
        return f"Failed to keystroke text: {out}"
    return f"Successfully typed {len(text)} characters into the focused application."


def macos_press_hotkey(key: str, modifier: str = "command down") -> str:
    """
    Press a keyboard shortcut in the active application (e.g. key='s', modifier='command down').
    """
    clean_key = key.strip().replace('"', '\\"')
    clean_mod = modifier.strip()
    script = f'''
    tell application "System Events"
        keystroke "{clean_key}" using {{{clean_mod}}}
    end tell
    '''
    ok, out = run_applescript(script)
    if not ok:
        return f"Failed to trigger hotkey: {out}"
    return f"Triggered hotkey [{clean_mod} + '{clean_key}']."
