"""
Tests for Project Genesis Model Manager and Multi-Backend Support.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from genesis.core.agent import GenesisAgent
from genesis.core.models import ModelManager, PROVIDER_PRESETS


def test_model_manager_load_and_save_config(tmp_path):
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        cfg = ModelManager.load_config()
        assert "base_url" in cfg
        assert "model" in cfg

        new_cfg = {
            "provider": "lmstudio",
            "base_url": "http://localhost:1234/v1",
            "api_key": "lm-studio",
            "model": "deepseek-coder",
        }
        ModelManager.save_config(new_cfg)
        loaded = ModelManager.load_config()
        assert loaded["provider"] == "lmstudio"
        assert loaded["model"] == "deepseek-coder"


def test_model_manager_get_presets():
    presets = ModelManager.get_presets()
    preset_ids = [p["id"] for p in presets]
    assert "ollama" in preset_ids
    assert "lmstudio" in preset_ids
    assert "openai" in preset_ids
    assert "deepseek" in preset_ids
    assert "groq" in preset_ids


def test_model_manager_fetch_models_error_handling():
    # Calling on unreachable port should return clean error dict, not raise exception
    res = ModelManager.fetch_models("http://localhost:9999/v1", "test_key", timeout=0.5)
    assert res["status"] == "error"
    assert "models" in res
    assert isinstance(res["models"], list)


def test_agent_switch_model(tmp_path):
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        agent = GenesisAgent()
        res = agent.switch_model(
            model_name="mistral-large",
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            provider="lmstudio",
        )
        assert res["status"] == "success"
        assert res["model"] == "mistral-large"
        assert agent.model_name == "mistral-large"
        assert "1234" in str(agent.client.base_url)


def test_gui_api_model_endpoints(tmp_path):
    from genesis.gui.api import GenesisDesktopApi
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        agent = GenesisAgent()
        api = GenesisDesktopApi(agent=agent)

        cfg = api.get_model_config()
        assert "current_model" in cfg
        assert "presets" in cfg
        assert "provider_status" in cfg
        assert "auto_stop_when_done" in cfg

        switch_res = api.switch_model(
            model_name="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-fake",
            provider="openai",
        )
        assert switch_res["status"] == "success"
        assert agent.model_name == "gpt-4o"


def test_resolve_binary_and_port():
    from genesis.core.models import resolve_binary, is_port_open
    # ollama or python binary should resolve
    py_bin = resolve_binary("python3")
    assert py_bin is not None

    # non-existent binary
    assert resolve_binary("non_existent_binary_xyz_123") is None

    # port check on an unused high port should return False
    assert is_port_open(59876) is False


def test_get_provider_status(tmp_path):
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        # Cloud provider
        status_openai = ModelManager.get_provider_status("openai")
        assert status_openai["provider"] == "openai"
        assert status_openai["type"] == "server"
        assert status_openai["is_running"] is True

        # Local provider (Ollama)
        status_ollama = ModelManager.get_provider_status("ollama")
        assert status_ollama["provider"] == "ollama"
        assert status_ollama["port"] == 11434
        assert "loaded_models" in status_ollama
        assert "cli_available" in status_ollama


def test_start_and_stop_provider(tmp_path):
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        # Starting cloud provider is always ok
        cloud_start = ModelManager.start_provider("groq")
        assert cloud_start["status"] == "ok"

        # Mock start provider when already running
        with patch("genesis.core.models.is_port_open", return_value=True):
            res_running = ModelManager.start_provider("ollama")
            assert res_running["status"] == "already_running"

        # Unload models test
        with patch("genesis.core.kill_switch.evict_all_models_from_vram", return_value=["qwen2.5-coder:7b"]):
            unload_res = ModelManager.stop_provider("ollama", unload_only=True)
            assert unload_res["status"] == "ok"
            assert unload_res["action"] == "unload"
            assert "Ollama models" in unload_res["message"]

        # Full stop provider test
        with patch("subprocess.run") as mock_run:
            stop_res = ModelManager.stop_provider("lmstudio", unload_only=False)
            assert stop_res["status"] == "ok"
            assert stop_res["action"] == "stop"


def test_auto_stop_configuration_and_agent_hook(tmp_path):
    from genesis.gui.api import GenesisDesktopApi
    fake_config_file = tmp_path / "model_config.json"
    with patch("genesis.core.models.MODEL_CONFIG_FILE", fake_config_file):
        agent = GenesisAgent()
        api = GenesisDesktopApi(agent=agent)

        # Toggle auto-stop
        set_res = api.set_auto_stop(True)
        assert set_res["status"] == "ok"
        assert set_res["auto_stop_when_done"] is True

        cfg = api.get_model_config()
        assert cfg["auto_stop_when_done"] is True

        # Test agent unload_model calls stop_provider
        with patch("genesis.core.models.ModelManager.stop_provider", return_value={"status": "ok"}) as mock_stop:
            agent.unload_model()
            mock_stop.assert_called_once_with(unload_only=True)

