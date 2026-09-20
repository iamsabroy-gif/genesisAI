"""
Project Genesis: Desktop GUI API Bridge.
Provides thread-safe Python methods exposed to the WebKit JavaScript frontend.
"""

import json
import threading
import time
from typing import Optional, Dict, Any, List

from genesis.core.agent import GenesisAgent
from genesis.core.master_auth import MasterAuth
from genesis.core.health_guard import SystemHealthWatchdog
from genesis.core.task_controller import TaskController
from genesis.config import DEFAULT_MODEL


class GenesisDesktopApi:
    """
    Exposed JS API for pywebview.
    JavaScript in WKWebView calls `window.pywebview.api.<method>()`.
    """

    def __init__(self, agent: Optional[GenesisAgent] = None):
        self.agent = agent or GenesisAgent()
        self.controller = TaskController(self.agent)
        self.window = None  # Injected after window creation
        self._current_worker_thread: Optional[threading.Thread] = None
        self._is_busy = False

    def _check_auto_stop(self):
        """Purges loaded models from RAM if auto-stop is enabled."""
        try:
            from genesis.core.models import ModelManager
            cfg = ModelManager.load_config()
            if cfg.get("auto_stop_when_done", False):
                ModelManager.stop_provider(unload_only=True)
                st = ModelManager.get_provider_status()
                self._emit("provider_status_changed", st)
        except Exception:
            pass

    def set_window(self, window):
        """Set pywebview window handle for evaluate_js callbacks."""
        self.window = window

    def _emit(self, event_name: str, payload: Any):
        """Send asynchronous event to JavaScript frontend."""
        if not self.window:
            return
        try:
            data_json = json.dumps({"event": event_name, "data": payload})
            script = f"if (window.onGenesisEvent) {{ window.onGenesisEvent({data_json}); }}"
            self.window.evaluate_js(script)
        except Exception as e:
            print(f"[GUI Bridge Event Error]: {e}")

    def init_session(self) -> Dict[str, Any]:
        """Initial state passed to the UI upon startup."""
        usage = self.agent.get_context_usage()
        status_health, health_msg, health_stats = SystemHealthWatchdog.evaluate_health_ceiling()

        return {
            "model": self.agent.model_name,
            "read_only_lock": self.agent.master_auth.read_only_lock,
            "used_tokens": usage.used_tokens,
            "total_tokens": usage.total_tokens,
            "usage_pct": round(usage.usage_percentage, 1),
            "ram_free_mb": round(health_stats.get("available_ram_mb", 0)),
            "health_status": status_health,
            "is_busy": self._is_busy,
        }

    def send_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """
        Executes a user prompt through the agent in a background thread.
        Notifies UI via events and returns final response.
        """
        user_prompt = user_prompt.strip()
        if not user_prompt:
            return {"status": "error", "message": "Prompt is empty"}

        # Instant Local Slash Command Interceptors
        if user_prompt.lower() in ["/skills", "/skill", "/"]:
            from genesis.core.skills import format_skills_markdown
            response = format_skills_markdown()
            usage = self.agent.get_context_usage()
            self._emit("task_completed", {
                "prompt": user_prompt,
                "response": response,
                "used_tokens": usage.used_tokens,
                "usage_pct": round(usage.usage_percentage, 1),
            })
            return {"status": "completed", "response": response}

        if user_prompt.lower().startswith("/upload"):
            target_arg = user_prompt[len("/upload"):].strip()
            if not target_arg:
                return self.open_file_dialog(folder_mode=False)
            res = self.upload_path(target_arg)
            summary_msg = res.get("summary", res.get("message", "Upload complete"))
            usage = self.agent.get_context_usage()
            self._emit("task_completed", {
                "prompt": user_prompt,
                "response": summary_msg,
                "used_tokens": usage.used_tokens,
                "usage_pct": round(usage.usage_percentage, 1),
            })
            return {"status": "completed", "response": summary_msg}

        if user_prompt.lower() in ["/research-formats", "/research_formats", "/research formats"]:
            from genesis.core.research_swarm import format_report_formats_markdown
            md_table = format_report_formats_markdown()
            usage = self.agent.get_context_usage()
            self._emit("task_completed", {
                "prompt": user_prompt,
                "response": md_table,
                "used_tokens": usage.used_tokens,
                "usage_pct": round(usage.usage_percentage, 1),
            })
            return {"status": "completed", "response": md_table}

        if user_prompt.lower().startswith("/research"):
            raw_arg = user_prompt[len("/research"):].strip()
            if not raw_arg:
                from genesis.core.research_swarm import format_report_formats_markdown
                help_msg = (
                    "**Usage:** `/research <topic> [--format <format>]`\n\n"
                    + format_report_formats_markdown()
                )
                usage = self.agent.get_context_usage()
                self._emit("task_completed", {
                    "prompt": user_prompt,
                    "response": help_msg,
                    "used_tokens": usage.used_tokens,
                    "usage_pct": round(usage.usage_percentage, 1),
                })
                return {"status": "completed", "response": help_msg}
            from genesis.core.research_swarm import extract_research_cli_flags
            topic_clean, format_choice, target_urls, context_items = extract_research_cli_flags(raw_arg)
            return self.run_research_swarm(
                topic_clean,
                report_format=format_choice,
                target_urls=target_urls,
                starting_context=context_items,
            )

        if user_prompt.lower().startswith("/context") or user_prompt.upper() == "!CONTEXT":
            arg = user_prompt[len("/context"):].strip() if user_prompt.lower().startswith("/context") else ""
            scaling_msg = ""
            if arg:
                from genesis.core.context import parse_context_size
                new_size = parse_context_size(arg)
                if new_size:
                    old_size = self.agent.max_context_tokens
                    self.agent.set_max_context(new_size)
                    scaling_msg = f"✓ **Context window scaled:** {old_size:,} → **{new_size:,} tokens** (Auto-prune threshold: {int(new_size * 0.75):,})\n\n"
                else:
                    scaling_msg = f"⚠️ Unrecognized context size '{arg}'. Try e.g. `/context 32k` or `/context 64k`.\n\n"
            usage = self.agent.get_context_usage()
            from genesis.core.context import get_recommended_context_size
            rec = get_recommended_context_size()
            summary = scaling_msg + "```\n" + usage.detailed_summary() + "\n```\n\n" + f"*Hardware Recommendation: {rec:,} tokens based on current RAM headroom.*"
            self._emit("task_completed", {
                "prompt": user_prompt,
                "response": summary,
                "used_tokens": usage.used_tokens,
                "usage_pct": round(usage.usage_percentage, 1),
            })
            return {"status": "completed", "response": summary}

        if self._is_busy:
            # Enqueue command
            pos = self.agent.queue_command(user_prompt)
            return {
                "status": "queued",
                "position": pos,
                "message": f"Queued task #{pos}: '{user_prompt}'",
            }

        self._is_busy = True
        self._emit("task_started", {"prompt": user_prompt})

        def _worker():
            try:
                response = self.agent.run_turn(user_prompt)
                usage = self.agent.get_context_usage()
                self._emit("task_completed", {
                    "prompt": user_prompt,
                    "response": response,
                    "used_tokens": usage.used_tokens,
                    "usage_pct": round(usage.usage_percentage, 1),
                })
            except Exception as e:
                self._emit("task_error", {"error": str(e)})
            finally:
                self._is_busy = False
                self._check_auto_stop()
                self._emit("idle", {})

        self._current_worker_thread = threading.Thread(target=_worker, daemon=True)
        self._current_worker_thread.start()

        return {"status": "started", "prompt": user_prompt}

    def run_swarm(self, goal: str) -> Dict[str, Any]:
        """Runs the 4-agent swarm and sends live telemetry to the visualizer."""
        goal = goal.strip()
        if not goal:
            return {"status": "error", "message": "Goal is empty"}

        if self._is_busy:
            return {"status": "error", "message": "Agent is currently busy"}

        self._is_busy = True
        self._emit("swarm_started", {"goal": goal})

        def _worker():
            try:
                from genesis.core.swarm import SwarmCoordinator
                coordinator = SwarmCoordinator(base_agent=self.agent)

                # Execute swarm rounds with real-time feedback
                dossier = coordinator.run_swarm(goal)
                self._emit("swarm_completed", dossier)
            except Exception as e:
                self._emit("swarm_error", {"error": str(e)})
            finally:
                self._is_busy = False
                self._check_auto_stop()
                self._emit("idle", {})

        self._current_worker_thread = threading.Thread(target=_worker, daemon=True)
        self._current_worker_thread.start()
        return {"status": "started", "goal": goal}

    def run_research_swarm(
        self,
        topic: str,
        report_format: str = "comprehensive",
        target_urls: int = 10,
        starting_context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs the 5-phase research swarm with chosen report format and starting context, emitting live updates."""
        topic = topic.strip()
        if not topic:
            return {"status": "error", "message": "Research topic is empty"}

        if self._is_busy:
            return {"status": "error", "message": "Agent is currently busy"}

        self._is_busy = True
        self._emit("research_swarm_started", {
            "topic": topic,
            "report_format": report_format,
            "target_urls": target_urls,
            "has_starting_context": bool(starting_context),
        })

        def _callback(phase_num, phase_id, label, details):
            self._emit("research_phase_update", {
                "phase_num": phase_num,
                "phase_id": phase_id,
                "label": label,
                "details": details,
            })

        def _worker():
            try:
                from genesis.core.research_swarm import ResearchSwarmCoordinator
                coordinator = ResearchSwarmCoordinator(base_agent=self.agent)
                dossier = coordinator.run_research_swarm(
                    topic,
                    report_format=report_format,
                    target_urls=target_urls,
                    on_event_callback=_callback,
                    starting_context=starting_context,
                )
                self._emit("research_swarm_completed", dossier)
            except Exception as e:
                self._emit("research_swarm_error", {"error": str(e)})
            finally:
                self._is_busy = False
                self._check_auto_stop()
                self._emit("idle", {})

        self._current_worker_thread = threading.Thread(target=_worker, daemon=True)
        self._current_worker_thread.start()
        return {
            "status": "started",
            "topic": topic,
            "report_format": report_format,
            "target_urls": target_urls,
            "has_starting_context": bool(starting_context),
        }


    def run_pipeline(self, goal: str) -> Dict[str, Any]:
        """Runs the 3-phase HierarchicalWorkflow (Recon -> Architect -> Implement)."""
        goal = goal.strip()
        if not goal:
            return {"status": "error", "message": "Goal is empty"}

        if self._is_busy:
            return {"status": "error", "message": "Agent is currently busy"}

        self._is_busy = True
        self._emit("pipeline_started", {"goal": goal})

        def _worker():
            try:
                from genesis.core.subagents import HierarchicalWorkflow
                hw = HierarchicalWorkflow(agent=self.agent)
                result = hw.run_pipeline(goal)
                self._emit("pipeline_completed", {"result": result})
            except Exception as e:
                self._emit("pipeline_error", {"error": str(e)})
            finally:
                self._is_busy = False
                self._check_auto_stop()
                self._emit("idle", {})

        self._current_worker_thread = threading.Thread(target=_worker, daemon=True)
        self._current_worker_thread.start()
        return {"status": "started", "goal": goal}

    def halt(self) -> Dict[str, Any]:
        """Halts the active background task and child processes immediately."""
        msg = self.controller.interrupt_and_halt()
        self._is_busy = False
        self._emit("halted", {"message": msg})
        return {"status": "halted", "message": msg}

    def execute_master_signal(self, signal: str) -> Dict[str, Any]:
        """Executes a deterministic MAP master signal (e.g. !LOCK, !REVERT, !KILL, !STATUS)."""
        context = {
            "estimated_tokens": self.agent.get_context_usage().used_tokens,
            "context_usage": self.agent.get_context_usage(),
            "history_len": len(self.agent.messages),
            "model": self.agent.model_name,
            "recorder": self.agent.recorder,
            "memory": self.agent.memory,
            "agent": self.agent,
        }
        output, target_state = self.agent.master_auth.execute_master_signal(signal, context)
        usage = self.agent.get_context_usage()

        return {
            "signal": signal,
            "output": output,
            "state": target_state,
            "read_only_lock": self.agent.master_auth.read_only_lock,
            "used_tokens": usage.used_tokens,
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns live hardware health, token metrics, and queue status."""
        usage = self.agent.get_context_usage()
        status_health, health_msg, health_stats = SystemHealthWatchdog.evaluate_health_ceiling()
        queue = self.agent.get_queued_commands()

        return {
            "model": self.agent.model_name,
            "read_only_lock": self.agent.master_auth.read_only_lock,
            "used_tokens": usage.used_tokens,
            "total_tokens": usage.total_tokens,
            "usage_pct": round(usage.usage_percentage, 1),
            "ram_free_mb": round(health_stats.get("available_ram_mb", 0)),
            "health_status": status_health,
            "health_msg": health_msg,
            "is_busy": self._is_busy,
            "queue_count": len(queue),
        }

    def clear_chat(self) -> Dict[str, Any]:
        """Clears memory messages in the current session."""
        self.agent.messages = []
        return {"status": "cleared"}

    def get_model_config(self) -> Dict[str, Any]:
        """Returns current model, server URL, provider, presets, and auto_stop preference."""
        from genesis.core.models import ModelManager
        cfg = ModelManager.load_config()
        presets = ModelManager.get_presets()
        provider_status = ModelManager.get_provider_status(cfg.get("provider", "ollama"))
        return {
            "current_model": self.agent.model_name,
            "current_base_url": cfg.get("base_url"),
            "current_provider": cfg.get("provider", "ollama"),
            "auto_stop_when_done": cfg.get("auto_stop_when_done", False),
            "provider_status": provider_status,
            "presets": presets,
        }

    def get_provider_status(self, provider_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns live server status, loaded models, and CLI availability for provider."""
        from genesis.core.models import ModelManager
        return ModelManager.get_provider_status(provider_id)

    def start_provider(self, provider_id: str) -> Dict[str, Any]:
        """Starts the local provider server (e.g. Ollama or LM Studio)."""
        from genesis.core.models import ModelManager
        res = ModelManager.start_provider(provider_id)
        status = ModelManager.get_provider_status(provider_id)
        self._emit("provider_status_changed", status)
        return res

    def stop_provider(self, provider_id: Optional[str] = None, unload_only: bool = False) -> Dict[str, Any]:
        """Stops the provider server or unloads models from Unified RAM."""
        from genesis.core.models import ModelManager
        res = ModelManager.stop_provider(provider_id, unload_only=unload_only)
        status = ModelManager.get_provider_status(provider_id)
        self._emit("provider_status_changed", status)
        return res

    def set_auto_stop(self, enabled: bool) -> Dict[str, Any]:
        """Configures auto-stop / auto-unload upon task completion."""
        from genesis.core.models import ModelManager
        res = ModelManager.set_auto_stop(enabled)
        self._emit("auto_stop_changed", res)
        return res

    def fetch_server_models(self, base_url: str, api_key: str = "") -> Dict[str, Any]:
        """Fetches models available at the specified server endpoint."""
        from genesis.core.models import ModelManager
        return ModelManager.fetch_models(base_url, api_key)

    def switch_model(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Switches agent's active model and persists configuration."""
        from genesis.core.models import ModelManager
        res = ModelManager.switch_model(
            self.agent,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider=provider,
        )
        self._emit("model_switched", res)
        status = ModelManager.get_provider_status(res.get("provider"))
        self._emit("provider_status_changed", status)
        return res

    def get_skills(self) -> List[Dict[str, Any]]:
        """Returns the complete catalog of Genesis sovereign skills."""
        from genesis.core.skills import get_skills_catalog
        return get_skills_catalog()

    def get_research_formats(self) -> List[Dict[str, Any]]:
        """Returns the list of available report formats for research swarm."""
        from genesis.core.research_swarm import get_report_formats
        return get_report_formats()

    def set_max_context(self, tokens: int) -> Dict[str, Any]:
        """Sets the active context window capacity in tokens."""
        new_size = self.agent.set_max_context(tokens)
        usage = self.agent.get_context_usage()
        self._emit("context_scaled", {
            "max_tokens": new_size,
            "used_tokens": usage.used_tokens,
            "usage_pct": round(usage.usage_percentage, 1),
        })
        return {
            "status": "ok",
            "max_tokens": new_size,
            "prune_trigger": int(new_size * 0.75),
        }

    def upload_path(self, target_path: str) -> Dict[str, Any]:
        """Ingests a file or folder into the workspace and vector vault."""
        from genesis.tools.uploader import ingest_upload
        res = ingest_upload(target_path)
        self._emit("upload_completed", res)
        return res

    def open_file_dialog(self, folder_mode: bool = False) -> Dict[str, Any]:
        """Opens native macOS file/folder picker dialog and ingests selected items."""
        if not self.window:
            return {"status": "error", "message": "Window reference not available"}
        try:
            import webview
            dialog_type = webview.FOLDER_DIALOG if folder_mode else webview.OPEN_DIALOG
            selected = self.window.create_file_dialog(dialog_type, allow_multiple=True)
            if not selected:
                return {"status": "cancelled", "message": "No file or folder selected"}

            from genesis.tools.uploader import ingest_upload
            results = []
            for item_path in selected:
                res = ingest_upload(item_path)
                results.append(res)

            combined_summary = "\n\n".join([r.get("summary", "") for r in results if r.get("status") == "ok"])
            if not combined_summary:
                combined_summary = f"Selected {len(selected)} item(s), but encountered errors."
            self._emit("upload_completed", {
                "status": "ok",
                "results": results,
                "summary": combined_summary,
                "count": len(results),
            })
            return {"status": "ok", "results": results, "summary": combined_summary}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def pick_research_context(self, folder_mode: bool = False) -> Dict[str, Any]:
        """Opens native macOS file/folder picker dialog for selecting research starting context."""
        if not self.window:
            return {"status": "error", "message": "Window reference not available"}
        try:
            import webview
            dialog_type = webview.FOLDER_DIALOG if folder_mode else webview.OPEN_DIALOG
            selected = self.window.create_file_dialog(dialog_type, allow_multiple=True)
            if not selected:
                return {"status": "cancelled", "message": "No file or folder selected"}
            return {"status": "ok", "paths": list(selected)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

