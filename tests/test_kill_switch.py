"""
Unit tests for Genesis Sovereign Hardware Kill Switch and Memory Purge Engine.
"""

from genesis.core.kill_switch import evict_all_models_from_vram, execute_kill_switch
from genesis.core.master_auth import MasterAuth


def test_evict_all_models_from_vram():
    evicted = evict_all_models_from_vram()
    assert isinstance(evicted, list)


def test_execute_kill_switch():
    report = execute_kill_switch(terminate_self=False)
    assert "# Genesis Kill Switch Engaged" in report
    assert "Current Available Headroom" in report
    assert "Hardware Status" in report
    assert "All Genesis neural resources have been discharged." in report


def test_master_auth_kill_signal():
    auth = MasterAuth()
    assert auth.is_master_signal("!KILL") is True
    assert auth.is_master_signal("!PURGE") is True

    context = {"model": "qwen2.5-coder-agent:latest", "history_len": 1}
    msg, target_state = auth.execute_master_signal("!KILL", context)
    assert "MASTER OVERRIDE: !KILL executed." in msg
    assert target_state == "MASTER_HOLD"
