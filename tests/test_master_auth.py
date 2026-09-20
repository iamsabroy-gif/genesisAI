"""
Tests for Project Genesis Master Authorization Protocol (MAP).
Authored by Test-Harness (Staff QA Lead).
"""

import time
from genesis.core.master_auth import MasterAuth


def test_master_key_and_token():
    auth = MasterAuth()
    assert auth.key is not None
    assert len(auth.key) == 32

    session_id = "test-session-123"
    ts = time.time()
    token = auth.generate_session_token(session_id, ts)

    assert auth.verify_session_token(session_id, ts, token) is True
    assert auth.verify_session_token(session_id, ts + 10, token) is False


def test_master_preemptive_signals():
    auth = MasterAuth()
    assert auth.is_master_signal("!HALT") is True
    assert auth.is_master_signal("!status") is True
    assert auth.is_master_signal("!lock") is True
    assert auth.is_master_signal("regular prompt") is False

    # Test lock / unlock toggle
    out, target = auth.execute_master_signal("!LOCK", {})
    assert auth.read_only_lock is True
    assert target == "READ_ONLY_LOCK"

    out, target = auth.execute_master_signal("!UNLOCK", {})
    assert auth.read_only_lock is False
    assert target == "IDLE"


def test_master_remember_and_purge():
    auth = MasterAuth()
    assert auth.is_master_signal("!REMEMBER python: use pydantic v2") is True
    assert auth.is_master_signal("!RULES") is True
    assert auth.is_master_signal("!PURGE") is True

    from genesis.memory.mentorship import MentorshipMemory
    from genesis.telemetry.flight_recorder import FlightRecorder

    mem = MentorshipMemory()
    recorder = FlightRecorder()
    ctx = {"memory": mem, "recorder": recorder}

    # Test !REMEMBER
    msg, _ = auth.execute_master_signal("!REMEMBER test_domain: always test code avoid: skip tests", ctx)
    assert "Rule recorded" in msg

    # Test !RULES
    rules_msg, _ = auth.execute_master_signal("!RULES", ctx)
    assert "test_domain" in rules_msg
    assert "always test code" in rules_msg

    # Test !PURGE
    purge_msg, _ = auth.execute_master_signal("!PURGE", ctx)
    assert "purge" in purge_msg.lower()
    assert recorder.purged is True
