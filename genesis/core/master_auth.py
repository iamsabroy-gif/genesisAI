"""
Master Authorization Protocol (MAP) & Preemptive Control Trap.
Implements the cryptographic Master Key handshake, session tokens, and preemptive signals.
"""

import os
import hmac
import hashlib
import secrets
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from genesis.config import GENESIS_HOME, WORKSPACE_ROOT

MASTER_KEY_FILE = GENESIS_HOME / "master.key"


class MasterAuth:
    """Manages cryptographic master credentials and inviolable signals."""

    def __init__(self):
        self.key = self._ensure_master_key()
        self.read_only_lock: bool = False

    def _ensure_master_key(self) -> bytes:
        """Initialize or load master key with strict 0600 permissions."""
        if not MASTER_KEY_FILE.exists():
            key_bytes = secrets.token_bytes(32)
            MASTER_KEY_FILE.write_bytes(key_bytes)
            os.chmod(MASTER_KEY_FILE, 0o600)
            return key_bytes
        else:
            # Ensure permissions are secure (owner read/write only)
            os.chmod(MASTER_KEY_FILE, 0o600)
            return MASTER_KEY_FILE.read_bytes()

    def generate_session_token(self, session_id: str, timestamp: float) -> str:
        """Create HMAC-SHA256 session token proving Master authentication."""
        message = f"{session_id}:{timestamp}".encode("utf-8")
        return hmac.new(self.key, message, hashlib.sha256).hexdigest()

    def verify_session_token(self, session_id: str, timestamp: float, token: str) -> bool:
        """Verify HMAC session signature."""
        expected = self.generate_session_token(session_id, timestamp)
        return hmac.compare_digest(expected, token)

    def is_master_signal(self, text: str) -> bool:
        """Check if incoming user input is a preemptive Master command."""
        t = text.strip().upper()
        if t in ["!HALT", "!REVERT", "!LOCK", "!UNLOCK", "!STATUS", "!PURGE", "!KILL", "!RULES", "!UNLOAD", "!CONTEXT"]:
            return True
        if text.strip().upper().startswith("!REMEMBER") or text.strip().upper().startswith("!SWARM") or text.strip().upper().startswith("!QUEUE"):
            return True
        return False

    def execute_master_signal(self, signal: str, agent_context: dict) -> Tuple[str, str]:
        """
        Execute deterministic Python trap bypassing LLM inference.
        Returns: (output_message, target_state_name)
        """
        raw_cmd = signal.strip()
        sig = raw_cmd.upper()

        if sig == "!HALT":
            # Immediately abort task and kill running child subprocesses
            agent = agent_context.get("agent")
            if agent and hasattr(agent, "abort_current_task"):
                halt_msg = agent.abort_current_task()
                return (halt_msg, "MASTER_HOLD")
            from genesis.tools.shell import terminate_active_processes
            killed = terminate_active_processes()
            return (f"MASTER OVERRIDE: !HALT executed ({killed} child subprocesses killed).", "MASTER_HOLD")

        elif sig.startswith("!QUEUE"):
            payload = raw_cmd[len("!QUEUE"):].strip()
            agent = agent_context.get("agent")
            if not agent:
                return ("Error: Agent context unavailable for command queue.", "NO_TRANSITION")

            p_upper = payload.upper()
            if not payload or p_upper == "LIST":
                q = agent.get_queued_commands()
                if not q:
                    return ("Command Queue is currently empty. Use '!QUEUE <instruction>' to enqueue.", "NO_TRANSITION")
                lines = [f"[{i+1}] {c}" for i, c in enumerate(q)]
                return ("=== ACTIVE COMMAND QUEUE ===\n" + "\n".join(lines) + "\n============================", "NO_TRANSITION")
            elif p_upper == "CLEAR":
                count = agent.clear_command_queue()
                return (f"Command Queue cleared ({count} pending commands removed).", "NO_TRANSITION")
            elif p_upper == "POP":
                popped = agent.pop_next_command()
                return (f"Removed next queued command: '{popped}'" if popped else "Command Queue was already empty.", "NO_TRANSITION")
            else:
                pos = agent.queue_command(payload)
                return (f"Enqueued instruction #{pos}: '{payload}'", "NO_TRANSITION")

        elif sig in ["!KILL", "!PURGE"]:
            # Discharge all neural models from Unified RAM and clean memory
            from genesis.core.kill_switch import execute_kill_switch
            recorder = agent_context.get("recorder")
            if recorder:
                recorder.mark_purged()
            kill_report = execute_kill_switch(terminate_self=False)
            return (f"MASTER OVERRIDE: {sig} executed.\n\n{kill_report}", "MASTER_HOLD")

        elif sig == "!REVERT":
            # Atomic git rollback
            try:
                subprocess.run(
                    "git checkout -- . && git clean -fd",
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=WORKSPACE_ROOT,
                    timeout=15,
                )
                return ("MASTER OVERRIDE: !REVERT executed. Working tree restored to clean git state.", "IDLE")
            except Exception as e:
                return (f"MASTER OVERRIDE: !REVERT error during git rollback: {e}", "IDLE")

        elif sig == "!LOCK":
            self.read_only_lock = True
            return ("MASTER OVERRIDE: !LOCK engaged. Tool executions disabled (READ_ONLY_LOCK).", "READ_ONLY_LOCK")

        elif sig == "!UNLOCK":
            self.read_only_lock = False
            return ("MASTER OVERRIDE: !UNLOCK engaged. Full tool execution capabilities restored.", "IDLE")

        elif sig == "!CONTEXT":
            usage = agent_context.get("context_usage")
            if usage and hasattr(usage, "detailed_summary"):
                return (usage.detailed_summary(), "NO_TRANSITION")
            tokens = agent_context.get("estimated_tokens", 0)
            return (f"Context: {tokens:,} / 16,384 tokens", "NO_TRANSITION")

        elif sig == "!STATUS":
            usage = agent_context.get("context_usage")
            tokens = agent_context.get("estimated_tokens", 0)
            if usage and hasattr(usage, "render_bar"):
                gauge = usage.render_bar(width=16)
                remaining = f"{usage.remaining_tokens:,} tokens ({100.0 - usage.usage_percentage:.1f}% free)"
                tokens_str = f"~{usage.used_tokens:,} / {usage.total_tokens:,} tokens {gauge} [Remaining: {remaining}]"
            else:
                tokens_str = f"~{tokens:,} / 16,384 tokens"

            history_len = agent_context.get("history_len", 0)
            model = agent_context.get("model", "unknown")
            lock_status = "LOCKED (Read-Only)" if self.read_only_lock else "ACTIVE (Read-Write)"
            status_msg = (
                f"=== MASTER SYSTEM STATUS ===\n"
                f"• Security Status: {lock_status}\n"
                f"• Active Model: {model}\n"
                f"• Context Window: {tokens_str}\n"
                f"• Conversation Turns: {history_len}\n"
                f"• Master Key: Valid ({MASTER_KEY_FILE.name})\n"
                f"============================"
            )
            return (status_msg, "NO_TRANSITION")

        elif sig == "!PURGE":
            recorder = agent_context.get("recorder")
            if recorder:
                recorder.mark_purged()
            return ("MASTER OVERRIDE: !PURGE executed. Current session trajectory marked as excluded from datasets.", "NO_TRANSITION")

        elif sig.startswith("!REMEMBER"):
            # Format: !REMEMBER <domain>: <preferred> [avoid <forbidden>]
            payload = raw_cmd[len("!REMEMBER"):].strip()
            memory = agent_context.get("memory")
            if not payload or not memory:
                return ("Usage: !REMEMBER <domain>: <preferred rule> [avoid: <forbidden>]", "NO_TRANSITION")

            domain = "global"
            preferred = payload
            forbidden = ""

            if ":" in payload:
                parts = payload.split(":", 1)
                domain = parts[0].strip()
                preferred = parts[1].strip()

            if "avoid:" in preferred.lower():
                rule_parts = re.split(r"avoid:", preferred, flags=re.IGNORECASE)
                preferred = rule_parts[0].strip()
                forbidden = rule_parts[1].strip()

            memory.record_heuristic(domain=domain, preferred=preferred, forbidden=forbidden)
            return (f"MASTER MENTORSHIP: Rule recorded in memory.db under domain '{domain}': '{preferred}'", "NO_TRANSITION")

        elif sig == "!RULES":
            memory = agent_context.get("memory")
            if not memory:
                return ("No memory subsystem attached.", "NO_TRANSITION")
            rules = memory.retrieve_heuristics("", limit=20)
            if not rules:
                return ("No active mentorship rules found in memory.db.", "NO_TRANSITION")
            rule_lines = ["=== MENTORSHIP RULES (memory.db) ==="]
            for r in rules:
                line = f"• [{r['domain']}] {r['preferred']}"
                if r['forbidden']:
                    line += f" (Avoid: {r['forbidden']})"
                rule_lines.append(line)
            rule_lines.append("====================================")
            return ("\n".join(rule_lines), "NO_TRANSITION")

        elif sig == "!UNLOAD":
            from genesis.core.kill_switch import evict_all_models_from_vram
            evicted = evict_all_models_from_vram()
            return (f"MASTER OVERRIDE: !UNLOAD executed. Evicted {len(evicted)} models from Unified RAM.", "IDLE")

        elif sig.startswith("!SWARM"):
            goal = raw_cmd[len("!SWARM"):].strip()
            if not goal:
                return ("Usage: !SWARM <high-level project goal to achieve continuously>", "NO_TRANSITION")
            agent = agent_context.get("agent")
            from genesis.core.swarm import SwarmCoordinator
            coordinator = SwarmCoordinator(base_agent=agent)
            res = coordinator.run_swarm(goal)
            return (f"[Swarm Result]: {res['status']}\n{res['summary']}", "COMPLETE")

        return (f"Unknown Master Signal: {signal}", "NO_TRANSITION")
