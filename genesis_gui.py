#!/usr/bin/env python3
"""
Project Genesis: Top-level Native macOS Desktop UI Entrypoint.
Usage: python genesis_gui.py
"""

import sys
from genesis.gui.app import launch_desktop_gui

if __name__ == "__main__":
    debug_mode = "--debug" in sys.argv
    launch_desktop_gui(debug=debug_mode)
