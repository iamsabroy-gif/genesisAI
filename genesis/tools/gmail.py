"""
Project Genesis: Gmail Integration Adapter.
Provides local, sovereign access to Gmail via Google OAuth2 or Local IMAP.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

from genesis.config import GENESIS_HOME

CREDENTIALS_DIR = GENESIS_HOME / "credentials"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

GMAIL_TOKEN_PATH = CREDENTIALS_DIR / "gmail_token.json"
GMAIL_CREDENTIALS_PATH = CREDENTIALS_DIR / "gmail_credentials.json"
GMAIL_CONFIG_PATH = CREDENTIALS_DIR / "gmail_config.json"


def gmail_status() -> str:
    """
    Check the current configuration and readiness of the Gmail adapter.
    Returns status and next actionable steps.
    """
    oauth_ready = GMAIL_TOKEN_PATH.exists()
    config_ready = GMAIL_CONFIG_PATH.exists()

    if oauth_ready:
        return "Gmail Status: [READY] Google OAuth2 token is active. Full read/write API access available."
    elif config_ready:
        try:
            cfg = json.loads(GMAIL_CONFIG_PATH.read_text())
            auth_type = cfg.get("auth_type", "imap")
            return f"Gmail Status: [CONFIGURED] {auth_type.upper()} credentials configured. Ready for sync."
        except Exception:
            pass

    return (
        "Gmail Status: [NOT CONFIGURED]\n"
        "To connect your Gmail account securely to Genesis, choose one of two sovereign local methods:\n"
        "1. Google Workspace OAuth2 API (Recommended for rich search, labels, and drafting):\n"
        "   - Download 'credentials.json' (Desktop App) from Google Cloud Console.\n"
        f"   - Place it at: {GMAIL_CREDENTIALS_PATH}\n"
        "   - Run: 'genesis gmail auth' to authenticate via local browser loopback.\n\n"
        "2. Google App Password / IMAP (Zero cloud setup):\n"
        "   - Generate a 16-character App Password at https://myaccount.google.com/apppasswords\n"
        f"   - Run: 'genesis gmail config-imap <email> <app_password>'"
    )


def gmail_get_integration_plan() -> str:
    """
    Returns the comprehensive engineering architecture plan to connect Genesis with Gmail.
    """
    return (
        "# Sovereign Gmail Integration Plan for Project Genesis\n\n"
        "## Architecture Pathways\n"
        "### Pathway 1: Google OAuth2 API (Rich Features)\n"
        "- Scope: `https://www.googleapis.com/auth/gmail.readonly`, `gmail.compose`\n"
        "- Storage: Refresh token stored in `~/.genesis/credentials/gmail_token.json` (chmod 600)\n"
        "- Tools: `gmail_search_emails`, `gmail_read_thread`, `gmail_create_draft`\n\n"
        "### Pathway 2: Local IMAP/SSL (Direct & Lightweight)\n"
        "- Protocol: Python built-in `imaplib` via `imap.gmail.com:993` with TLS\n"
        "- Authentication: Google App Password stored in macOS Keychain or encrypted local file\n"
        "- Zero external GCP project required\n\n"
        "### Pathway 3: Local macOS Apple Mail Bridge (Zero API Setup)\n"
        "- If your Gmail is already configured in Apple Mail on this Mac, Genesis can query\n"
        "  messages directly using AppleScript (`osascript`) without any credentials.\n\n"
        "## Next Steps\n"
        "Let me know which pathway you prefer (OAuth2, App Password, or Apple Mail), and I will\n"
        "activate the corresponding adapter immediately."
    )
