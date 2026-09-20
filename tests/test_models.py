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

        switch_res = api.switch_model(
            model_name="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-fake",
            provider="openai",
        )
        assert switch_res["status"] == "success"
        assert agent.model_name == "gpt-4o"
