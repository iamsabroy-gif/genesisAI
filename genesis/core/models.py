"""
Project Genesis: Model & Server Provider Management.
Supports switching between Local (Ollama, LM Studio, vLLM, llama.cpp)
and Server/Cloud endpoints (OpenAI, DeepSeek, Groq, OpenRouter, Custom Server).
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
from genesis.config import GENESIS_HOME, OLLAMA_BASE_URL, OLLAMA_API_KEY, DEFAULT_MODEL

MODEL_CONFIG_FILE = GENESIS_HOME / "model_config.json"

PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "id": "ollama",
        "name": "Ollama (Local Apple Silicon)",
        "type": "local",
        "base_url": OLLAMA_BASE_URL,
        "default_key": "ollama",
        "default_model": DEFAULT_MODEL,
        "env_var": "OLLAMA_API_KEY",
    },
    "lmstudio": {
        "id": "lmstudio",
        "name": "LM Studio (Local Apple Silicon)",
        "type": "local",
        "base_url": "http://localhost:1234/v1",
        "default_key": "lm-studio",
        "default_model": "local-model",
        "env_var": None,
    },
    "vllm": {
        "id": "vllm",
        "name": "vLLM / llama.cpp / LocalAI (Local)",
        "type": "local",
        "base_url": "http://localhost:8000/v1",
        "default_key": "token",
        "default_model": "default",
        "env_var": None,
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI (Cloud Server)",
        "type": "server",
        "base_url": "https://api.openai.com/v1",
        "default_key": "",
        "default_model": "gpt-4o",
        "env_var": "OPENAI_API_KEY",
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek (Cloud Server)",
        "type": "server",
        "base_url": "https://api.deepseek.com/v1",
        "default_key": "",
        "default_model": "deepseek-chat",
        "env_var": "DEEPSEEK_API_KEY",
    },
    "groq": {
        "id": "groq",
        "name": "Groq Cloud (Fast Llama/Qwen)",
        "type": "server",
        "base_url": "https://api.groq.com/openai/v1",
        "default_key": "",
        "default_model": "llama-3.3-70b-versatile",
        "env_var": "GROQ_API_KEY",
    },
    "openrouter": {
        "id": "openrouter",
        "name": "OpenRouter (Unified Server)",
        "type": "server",
        "base_url": "https://openrouter.ai/api/v1",
        "default_key": "",
        "default_model": "anthropic/claude-3.5-sonnet",
        "env_var": "OPENROUTER_API_KEY",
    },
}


class ModelManager:
    """Manages active LLM provider configurations, models list, and hot-switching."""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Loads saved model configuration or returns system default."""
        if MODEL_CONFIG_FILE.exists():
            try:
                data = json.loads(MODEL_CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "base_url" in data and "model" in data:
                    return data
            except Exception:
                pass

        # Default configuration
        return {
            "provider": "ollama",
            "base_url": OLLAMA_BASE_URL,
            "api_key": OLLAMA_API_KEY,
            "model": DEFAULT_MODEL,
        }

    @staticmethod
    def save_config(config: Dict[str, Any]):
        """Persists model configuration to ~/.genesis/model_config.json."""
        try:
            MODEL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            MODEL_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ModelManager] Warning: could not save config: {e}")

    @staticmethod
    def get_presets() -> List[Dict[str, Any]]:
        """Returns list of presets with auto-discovered environment keys."""
        res = []
        for pid, preset in PROVIDER_PRESETS.items():
            item = dict(preset)
            env_var = preset.get("env_var")
            env_val = os.getenv(env_var) if env_var else None
            item["has_env_key"] = bool(env_val)
            if env_val:
                item["effective_key"] = env_val
            else:
                item["effective_key"] = preset.get("default_key", "")
            res.append(item)
        return res

    @staticmethod
    def fetch_models(base_url: str, api_key: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Attempts to list models from the target base_url using an OpenAI-compatible client.
        Returns {"status": "ok", "models": [...]} or {"status": "error", "message": "..."}.
        """
        try:
            client = OpenAI(base_url=base_url, api_key=api_key or "none", timeout=timeout)
            resp = client.models.list()
            models = sorted([m.id for m in resp.data])
            return {"status": "ok", "models": models}
        except Exception as e:
            return {"status": "error", "message": str(e), "models": []}

    @classmethod
    def switch_model(
        cls,
        agent,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Hot-switches the agent's active model and client without restarting the application.
        """
        current_cfg = cls.load_config()

        new_base_url = (base_url or current_cfg.get("base_url") or OLLAMA_BASE_URL).rstrip("/")
        # Ensure /v1 suffix if not already present and not root
        if not new_base_url.endswith("/v1") and not new_base_url.endswith("/v1/"):
            # Check if user passed bare host like http://localhost:11434
            if "localhost:11434" in new_base_url or "localhost:1234" in new_base_url:
                new_base_url = f"{new_base_url}/v1"

        new_api_key = api_key if api_key is not None else current_cfg.get("api_key", "ollama")
        new_model = model_name.strip()

        # Update the agent
        agent.client = OpenAI(base_url=new_base_url, api_key=new_api_key or "none")
        agent.model_name = new_model

        # Determine provider name
        if not provider:
            provider = "custom"
            for p_id, p_info in PROVIDER_PRESETS.items():
                if p_info["base_url"].rstrip("/") == new_base_url:
                    provider = p_id
                    break

        new_config = {
            "provider": provider,
            "base_url": new_base_url,
            "api_key": new_api_key,
            "model": new_model,
        }
        cls.save_config(new_config)

        return {
            "status": "success",
            "model": new_model,
            "base_url": new_base_url,
            "provider": provider,
            "message": f"Switched active model to '{new_model}' on {new_base_url}",
        }
