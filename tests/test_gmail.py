"""Unit tests for the Gmail tool adapter."""

from genesis.tools.gmail import gmail_status, gmail_get_integration_plan


def test_gmail_status():
    status = gmail_status()
    assert "Gmail Status" in status
    assert "Google Workspace OAuth2" in status or "READY" in status


def test_gmail_get_integration_plan():
    plan = gmail_get_integration_plan()
    assert "Sovereign Gmail Integration Plan" in plan
    assert "Google OAuth2" in plan
    assert "Local IMAP" in plan
