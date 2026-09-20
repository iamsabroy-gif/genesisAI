"""
Project Genesis: Native macOS Desktop Application Launcher.
Wraps the modern web interface inside a native macOS WebKit (WKWebView) window.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from genesis.core.agent import GenesisAgent
from genesis.gui.api import GenesisDesktopApi

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    candidate = Path(sys._MEIPASS) / "genesis" / "gui" / "web"
    if candidate.exists():
        WEB_DIR = candidate
    else:
        WEB_DIR = Path(__file__).resolve().parent / "web"
else:
    WEB_DIR = Path(__file__).resolve().parent / "web"

INDEX_HTML = WEB_DIR / "index.html"


def launch_desktop_gui(agent: Optional[GenesisAgent] = None, debug: bool = False):
    """
    Launches the Project Genesis native macOS desktop window.
    Uses pywebview with Apple's native WebKit bindings.
    """
    try:
        import webview
    except ImportError:
        print("[Error]: 'pywebview' is not installed. Run 'pip install pywebview' to use the desktop UI.")
        sys.exit(1)

    if not INDEX_HTML.exists():
        raise FileNotFoundError(f"Desktop GUI HTML asset not found at {INDEX_HTML}")

    api = GenesisDesktopApi(agent=agent)

    # Configure native macOS WebKit window
    window = webview.create_window(
        title="Genesis AI",
        url=str(INDEX_HTML),
        js_api=api,
        width=1160,
        height=780,
        min_size=(920, 620),
        background_color="#0d1117",
        text_select=True,
        zoomable=True,
    )

    api.set_window(window)

    # Launch Cocoa event loop
    webview.start(debug=debug)


if __name__ == "__main__":
    launch_desktop_gui()
