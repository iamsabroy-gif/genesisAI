"""
Project Genesis: Model & Server Provider Management.
Supports switching between Local (Ollama, LM Studio, vLLM, llama.cpp)
and Server/Cloud endpoints (OpenAI, DeepSeek, Groq, OpenRouter, Custom Server).
"""

import os
import json
import subprocess
import shutil
import socket
import urllib.request
import gc
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
from genesis.config import GENESIS_HOME, OLLAMA_BASE_URL, OLLAMA_API_KEY, DEFAULT_MODEL

MODEL_CONFIG_FILE = GENESIS_HOME / "model_config.json"


def resolve_binary(name: str) -> Optional[str]:
    """Finds binary path in PATH or standard macOS installation directories."""
    found = shutil.which(name)
    if found and os.access(found, os.X_OK):
        return found
    candidates = [
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        os.path.expanduser(f"~/.lmstudio/bin/{name}"),
        f"/Applications/Ollama.app/Contents/Resources/{name}",
        f"/opt/homebrew/opt/ollama/bin/{name}",
    ]
    for path in candidates:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    return None


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Fast non-blocking check if a localhost port is actively listening."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


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
                    if "auto_stop_when_done" not in data:
                        data["auto_stop_when_done"] = False
                    return data
            except Exception:
                pass

        # Default configuration
        return {
            "provider": "ollama",
            "base_url": OLLAMA_BASE_URL,
            "api_key": OLLAMA_API_KEY,
            "model": DEFAULT_MODEL,
            "auto_stop_when_done": False,
        }

    @staticmethod
    def save_config(config: Dict[str, Any]):
        """Persists model configuration to ~/.genesis/model_config.json."""
        try:
            MODEL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            MODEL_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ModelManager] Warning: could not save config: {e}")

    @classmethod
    def get_presets(cls) -> List[Dict[str, Any]]:
        """Returns list of presets with auto-discovered environment keys and live status."""
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

            # Live port check
            if pid == "ollama":
                item["is_running"] = is_port_open(11434)
            elif pid == "lmstudio":
                item["is_running"] = is_port_open(1234)
            elif pid == "vllm":
                item["is_running"] = is_port_open(8000)
            else:
                item["is_running"] = True  # Cloud endpoints are online

            res.append(item)
        return res

    @classmethod
    def get_provider_status(cls, provider_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns real-time status of local server/daemon, loaded models in RAM/VRAM,
        and binary availability.
        """
        cfg = cls.load_config()
        pid = (provider_id or cfg.get("provider", "ollama")).lower().strip()
        preset = PROVIDER_PRESETS.get(pid, {})
        ptype = preset.get("type", "local" if pid in ["ollama", "lmstudio", "vllm"] else "server")

        if ptype == "server":
            env_var = preset.get("env_var")
            has_key = bool(os.getenv(env_var)) if env_var else bool(cfg.get("api_key"))
            return {
                "provider": pid,
                "name": preset.get("name", pid),
                "type": "server",
                "is_running": True,
                "port": None,
                "cli_available": True,
                "cli_path": None,
                "loaded_models": [],
                "has_key": has_key,
                "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
                "message": "Cloud API Active" if has_key else "API Key required",
            }

        if pid == "ollama":
            port = 11434
            is_running = is_port_open(port)
            cli_path = resolve_binary("ollama")
            loaded_models: List[str] = []
            if is_running:
                try:
                    req = urllib.request.Request("http://127.0.0.1:11434/api/ps")
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        for m in data.get("models", []):
                            m_name = m.get("name") or m.get("model")
                            if m_name and m_name not in loaded_models:
                                loaded_models.append(m_name)
                except Exception:
                    pass
            return {
                "provider": "ollama",
                "name": "Ollama (Local Apple Silicon)",
                "type": "local",
                "is_running": is_running,
                "port": port,
                "cli_available": bool(cli_path),
                "cli_path": cli_path,
                "loaded_models": loaded_models,
                "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
                "message": f"Running (Port {port})" if is_running else "Stopped (Offline)",
            }

        if pid == "lmstudio":
            port = 1234
            is_running = is_port_open(port)
            cli_path = resolve_binary("lms")
            loaded_models: List[str] = []
            if cli_path and is_running:
                try:
                    out = subprocess.check_output([cli_path, "ps", "--json"], text=True, timeout=2)
                    ps_data = json.loads(out)
                    if isinstance(ps_data, list):
                        for m in ps_data:
                            if isinstance(m, dict) and "identifier" in m:
                                loaded_models.append(m["identifier"])
                            elif isinstance(m, str):
                                loaded_models.append(m)
                except Exception:
                    pass
            return {
                "provider": "lmstudio",
                "name": "LM Studio (Local Apple Silicon)",
                "type": "local",
                "is_running": is_running,
                "port": port,
                "cli_available": bool(cli_path),
                "cli_path": cli_path,
                "loaded_models": loaded_models,
                "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
                "message": f"Running (Port {port})" if is_running else "Stopped (Offline)",
            }

        if pid == "vllm":
            port = 8000
            is_running = is_port_open(port)
            return {
                "provider": "vllm",
                "name": "vLLM / llama.cpp (Local)",
                "type": "local",
                "is_running": is_running,
                "port": port,
                "cli_available": False,
                "cli_path": None,
                "loaded_models": [],
                "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
                "message": f"Running (Port {port})" if is_running else "Stopped (Offline)",
            }

        # Custom or unknown
        return {
            "provider": pid,
            "name": pid,
            "type": "local",
            "is_running": False,
            "port": None,
            "cli_available": False,
            "cli_path": None,
            "loaded_models": [],
            "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
            "message": "Custom Endpoint",
        }

    @classmethod
    def start_provider(cls, provider_id: str) -> Dict[str, Any]:
        """
        Starts the local inference provider daemon (Ollama or LM Studio).
        Polls until the server port is open.
        """
        pid = provider_id.lower().strip()
        status = cls.get_provider_status(pid)
        if status.get("type") == "server":
            return {
                "status": "ok",
                "provider": pid,
                "message": f"{status.get('name', pid)} is a cloud endpoint and is always active.",
            }

        if status.get("is_running"):
            return {
                "status": "already_running",
                "provider": pid,
                "message": f"{status.get('name', pid)} server is already running.",
            }

        if pid == "ollama":
            cli_path = resolve_binary("ollama")
            # 1. Try Homebrew service if available
            try:
                out = subprocess.run(["brew", "services", "start", "ollama"], capture_output=True, text=True, timeout=5)
                if out.returncode == 0:
                    time.sleep(1)
            except Exception:
                pass

            if not is_port_open(11434):
                if cli_path:
                    subprocess.Popen(
                        [cli_path, "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                elif os.path.exists("/Applications/Ollama.app"):
                    subprocess.run(["open", "-a", "Ollama"], check=False)
                else:
                    return {
                        "status": "error",
                        "provider": pid,
                        "message": "Ollama CLI or Application not found. Please install Ollama.",
                    }

            # Poll for port 11434 to open
            for _ in range(12):
                time.sleep(0.5)
                if is_port_open(11434):
                    return {
                        "status": "ok",
                        "provider": pid,
                        "message": "Ollama server started successfully on port 11434.",
                    }
            return {
                "status": "error",
                "provider": pid,
                "message": "Timed out waiting for Ollama to bind to port 11434.",
            }

        if pid == "lmstudio":
            cli_path = resolve_binary("lms")
            if cli_path:
                try:
                    subprocess.run([cli_path, "server", "start"], capture_output=True, text=True, timeout=10)
                except Exception as e:
                    return {"status": "error", "provider": pid, "message": str(e)}
            elif os.path.exists("/Applications/LM Studio.app"):
                subprocess.run(["open", "-a", "LM Studio"], check=False)
            else:
                return {
                    "status": "error",
                    "provider": pid,
                    "message": "LM Studio CLI (lms) not found. Enable 'lms' in LM Studio Settings.",
                }

            # Poll for port 1234 to open
            for _ in range(12):
                time.sleep(0.5)
                if is_port_open(1234):
                    return {
                        "status": "ok",
                        "provider": pid,
                        "message": "LM Studio server started successfully on port 1234.",
                    }
            return {
                "status": "error",
                "provider": pid,
                "message": "Timed out waiting for LM Studio server to bind to port 1234.",
            }

        if status.get("type") == "server":
            return {
                "status": "ok",
                "provider": pid,
                "message": f"{provider_id} is a cloud endpoint and is always active.",
            }

        return {
            "status": "error",
            "provider": pid,
            "message": f"Automated startup is not supported for provider '{provider_id}'.",
        }

    @classmethod
    def stop_provider(cls, provider_id: Optional[str] = None, unload_only: bool = False) -> Dict[str, Any]:
        """
        Stops the provider server or unloads all models from Unified RAM/VRAM.
        If unload_only is True, server keeps running but frees VRAM.
        If unload_only is False, shuts down the server process.
        """
        cfg = cls.load_config()
        pid = (provider_id or cfg.get("provider", "ollama")).lower().strip()
        freed_items: List[str] = []

        # 1. Unload models from memory
        if pid == "ollama" or unload_only:
            try:
                from genesis.core.kill_switch import evict_all_models_from_vram
                evicted = evict_all_models_from_vram()
                if evicted:
                    freed_items.append(f"Ollama models: {', '.join(evicted)}")
            except Exception:
                pass

        if pid == "lmstudio" or unload_only:
            cli_path = resolve_binary("lms")
            if cli_path:
                try:
                    subprocess.run([cli_path, "unload", "--all"], capture_output=True, timeout=5)
                    freed_items.append("LM Studio models unloaded")
                except Exception:
                    pass

        gc.collect()

        if unload_only:
            msg = f"Purged RAM: {'; '.join(freed_items)}" if freed_items else "Unified RAM purged; models unloaded."
            return {
                "status": "ok",
                "provider": pid,
                "action": "unload",
                "message": msg,
            }

        # 2. Shut down server process
        if pid == "ollama":
            # Try brew services stop if active
            try:
                subprocess.run(["brew", "services", "stop", "ollama"], capture_output=True, timeout=5)
            except Exception:
                pass
            try:
                subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True, timeout=3)
            except Exception:
                pass
            try:
                subprocess.run(["osascript", "-e", 'quit app "Ollama"'], capture_output=True, timeout=3)
            except Exception:
                pass

            for _ in range(10):
                time.sleep(0.3)
                if not is_port_open(11434):
                    break

            return {
                "status": "ok",
                "provider": pid,
                "action": "stop",
                "message": "Ollama server stopped cleanly and RAM purged.",
            }

        if pid == "lmstudio":
            cli_path = resolve_binary("lms")
            if cli_path:
                try:
                    subprocess.run([cli_path, "server", "stop"], capture_output=True, timeout=5)
                except Exception:
                    pass
            try:
                subprocess.run(["osascript", "-e", 'quit app "LM Studio"'], capture_output=True, timeout=3)
            except Exception:
                pass

            for _ in range(10):
                time.sleep(0.3)
                if not is_port_open(1234):
                    break

            return {
                "status": "ok",
                "provider": pid,
                "action": "stop",
                "message": "LM Studio server stopped cleanly.",
            }

        return {
            "status": "ok",
            "provider": pid,
            "action": "stop",
            "message": f"Provider '{pid}' server stopped.",
        }

    @classmethod
    def set_auto_stop(cls, enabled: bool) -> Dict[str, Any]:
        """Persists auto-stop / auto-unload preference upon task completion."""
        cfg = cls.load_config()
        cfg["auto_stop_when_done"] = bool(enabled)
        cls.save_config(cfg)
        return {"status": "ok", "auto_stop_when_done": bool(enabled)}

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
            "auto_stop_when_done": current_cfg.get("auto_stop_when_done", False),
        }
        cls.save_config(new_config)

        return {
            "status": "success",
            "model": new_model,
            "base_url": new_base_url,
            "provider": provider,
            "message": f"Switched active model to '{new_model}' on {new_base_url}",
        }

