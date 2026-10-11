"""
Context and Token Budget Manager for Project Genesis.
Implements the 16k context window partition and priority-weighted eviction from algo.md.
C5: Exact Ollama tokenizer with LRU cache.
C1: Priority-weighted pruning replaces naive FIFO.
"""

import time
import json
import hashlib
import urllib.request
from functools import lru_cache
from typing import List, Dict, Any, Optional
from genesis.config import (
    MAX_CONTEXT_TOKENS,
    PRUNE_TRIGGER_TOKENS,
    TARGET_HISTORY_TOKENS,
    DEFAULT_MODEL,
    OLLAMA_BASE_URL,
)

from dataclasses import dataclass, field

# ── C5: Exact Ollama Tokenizer ──────────────────────────────────────────────
# Cache keyed by (model, hash(text)) — repeated content (system prompt, file reads) costs 0 ms
_TOKENIZE_ENDPOINT = OLLAMA_BASE_URL.replace("/v1", "") + "/api/tokenize"
_TOKENIZER_TIMEOUT_S = 2.0  # Fall back to heuristic if Ollama responds slowly


@lru_cache(maxsize=2048)
def _exact_token_count(text_hash: str, text: str, model: str) -> int:
    """LRU-cached exact token count via Ollama /api/tokenize."""
    try:
        payload = json.dumps({"model": model, "prompt": text}).encode()
        req = urllib.request.Request(
            _TOKENIZE_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=_TOKENIZER_TIMEOUT_S) as resp:
            data = json.loads(resp.read())
            return len(data.get("tokens", []))
    except Exception:
        # Graceful fallback: Qwen2.5 averages ~3 chars/token
        return max(1, len(text) // 3)


def estimate_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    C5: Exact token count via Ollama tokenizer API, LRU-cached by text hash.
    Falls back to the //3 heuristic on connection failure (e.g., Ollama not running).
    """
    if not text:
        return 0
    text_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
    return _exact_token_count(text_hash, text, model)


def _get_field(m: Any, field: str, default=None):
    if isinstance(m, dict):
        return m.get(field, default)
    return getattr(m, field, default)


def estimate_messages_tokens(messages: List[Any]) -> int:
    """Estimate total token consumption across a list of chat messages."""
    total = 0
    for m in messages:
        content = _get_field(m, "content") or ""
        total += estimate_tokens(str(content))
        tool_calls = _get_field(m, "tool_calls")
        if tool_calls:
            for tc in tool_calls:
                fn = _get_field(tc, "function", {})
                total += estimate_tokens(_get_field(fn, "name", ""))
                total += estimate_tokens(str(_get_field(fn, "arguments", "")))
    return total


@dataclass
class ContextUsageReport:
    """Real-time representation of context window capacity and token consumption."""
    used_tokens: int
    total_tokens: int = MAX_CONTEXT_TOKENS
    prune_trigger_tokens: int = PRUNE_TRIGGER_TOKENS
    breakdown: Dict[str, int] = field(default_factory=lambda: {
        "system": 0, "user": 0, "assistant": 0, "tool": 0
    })

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.total_tokens - self.used_tokens)

    @property
    def usage_percentage(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return min(100.0, (self.used_tokens / self.total_tokens) * 100.0)

    @property
    def is_pruning_needed(self) -> bool:
        return self.used_tokens >= self.prune_trigger_tokens

    def render_bar(self, width: int = 20) -> str:
        """Render an ASCII progress gauge representing current context occupancy."""
        filled = int((self.used_tokens / max(1, self.total_tokens)) * width)
        filled = max(0, min(width, filled))
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def single_line_badge(self) -> str:
        """Formatted one-liner badge for CLI prompts and status bars."""
        bar = self.render_bar(width=16)
        pct = self.usage_percentage
        color = "green" if pct < 60 else ("yellow" if pct < 75 else "red")
        return (
            f"Context: {self.used_tokens:,} / {self.total_tokens:,} tokens "
            f"({self.remaining_tokens:,} remaining | {pct:.1f}% used) {bar}"
        )

    def detailed_summary(self) -> str:
        """Formatted detailed multi-line report."""
        bar = self.render_bar(width=24)
        status = "CRITICAL (Pruning Imminent)" if self.is_pruning_needed else (
            "WARNING (Elevated)" if self.usage_percentage >= 60 else "NOMINAL"
        )
        return (
            f"=== CONTEXT WINDOW USAGE ===\n"
            f"• Total Capacity   : {self.total_tokens:,} tokens\n"
            f"• Current Occupancy: {self.used_tokens:,} tokens ({self.usage_percentage:.1f}%)\n"
            f"• Remaining Buffer : {self.remaining_tokens:,} tokens\n"
            f"• Prune Threshold  : {self.prune_trigger_tokens:,} tokens (auto-evicts at 75%)\n"
            f"• Health Status    : {status}\n"
            f"• Gauge            : {bar}\n"
            f"• Breakdown        :\n"
            f"    - System Anchor   : {self.breakdown.get('system', 0):,} tokens\n"
            f"    - User Prompts    : {self.breakdown.get('user', 0):,} tokens\n"
            f"    - Model Reasoning : {self.breakdown.get('assistant', 0):,} tokens\n"
            f"    - Tool Executions : {self.breakdown.get('tool', 0):,} tokens\n"
            f"============================"
        )


def get_context_usage(messages: List[Any], max_tokens: int = MAX_CONTEXT_TOKENS) -> ContextUsageReport:
    """
    Compute structured context usage metrics across active message history.
    """
    breakdown = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
    total_tokens = 0

    for m in messages:
        role = _get_field(m, "role", "user")
        content = _get_field(m, "content") or ""
        tokens = estimate_tokens(str(content))
        tool_calls = _get_field(m, "tool_calls")
        if tool_calls:
            for tc in tool_calls:
                fn = _get_field(tc, "function", {})
                tokens += estimate_tokens(_get_field(fn, "name", ""))
                tokens += estimate_tokens(str(_get_field(fn, "arguments", "")))

        if role in breakdown:
            breakdown[role] += tokens
        else:
            breakdown["user"] += tokens
        total_tokens += tokens

    return ContextUsageReport(
        used_tokens=total_tokens,
        total_tokens=max_tokens,
        prune_trigger_tokens=int(max_tokens * 0.75),
        breakdown=breakdown,
    )


# ── C1: Priority-Weighted Pruning ───────────────────────────────────────────
# Score weights — lower score = evict first.
# messages[0] (system) and messages[1] (initial user goal) are IMMUTABLE (∞ score).
def _message_priority(msg: Any, idx: int, total: int, now: float = 0.0) -> float:
    """
    C1: Assign eviction priority score to a message.
    Higher score = more valuable = keep longer.

    Scoring rules:
    - System anchor (idx 0)         → ∞  (never evict)
    - Initial user goal (idx 1)     → ∞  (never evict)
    - Current active prompt (last)  → ∞  (never evict)
    - Tool observation (large)      → 0.1 → 0.3 based on recency
    - Old assistant turns (>3 back) → 0.3
    - Recent assistant (last 2)     → 0.9
    - User turn (non-goal)          → 0.5
    """
    if idx <= 1 or idx >= total - 1:
        return float("inf")

    role = _get_field(msg, "role", "user")
    recency = idx / max(1, total - 1)  # 0.0 = oldest, 1.0 = newest

    if role == "tool":
        content = str(_get_field(msg, "content", ""))
        size_penalty = min(0.2, len(content) / 10000)  # big output = lower score
        return max(0.05, 0.3 * recency - size_penalty)

    if role == "assistant":
        return 0.3 + 0.6 * recency  # recent assistant = high value

    if role == "user":
        return 0.5 + 0.3 * recency  # user context is moderately important

    return 0.2


def _smart_compress_tool_output(content: str) -> str:
    """
    C1: Intelligent tool output compression.
    Extracts exit code line and first meaningful result instead of first+last lines.
    """
    lines = [l for l in content.splitlines() if l.strip()]
    if len(lines) <= 4:
        return content

    # Find the exit code line if present
    exit_line = next((l for l in lines if "exit code" in l.lower()), "")
    # First substantive result line (skip headers/blanks)
    result_line = lines[0] if lines else ""

    compressed = result_line
    if exit_line and exit_line != result_line:
        compressed += f"\n{exit_line}"
    compressed += f"\n... [{len(lines)} lines compressed — {len(content)} chars] ..."
    return compressed


def sanitize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """
    Normalizes, repairs, and sanitizes chat completion message sequences to guarantee
    strict compliance with OpenAI, Ollama, Anthropic, and vLLM API contracts.

    Guarantees:
    1. Never allows consecutive messages of the same role (merges assistant+assistant, user+user).
    2. Never allows 2 or more assistant messages at the end of the list.
    3. Guarantees every tool response has a valid preceding assistant tool_call.
    4. Converts orphaned tool observations into valid user observations.
    5. Returns clean dictionaries with valid string content.
    """
    if not messages:
        return []

    cleaned: List[Dict[str, Any]] = []
    for m in messages:
        if isinstance(m, dict):
            item = dict(m)
        elif hasattr(m, "model_dump"):
            item = m.model_dump(exclude_unset=True)
        else:
            item = {
                "role": getattr(m, "role", "user"),
                "content": getattr(m, "content", ""),
            }
        if "role" not in item:
            item["role"] = "user"
        if "content" not in item or item["content"] is None:
            item["content"] = ""
        cleaned.append(item)

    # Step 1: Merge consecutive messages with the same role (assistant + assistant, user + user)
    merged: List[Dict[str, Any]] = []
    for msg in cleaned:
        if not merged:
            merged.append(msg)
            continue

        prev = merged[-1]
        prev_role = prev.get("role")
        curr_role = msg.get("role")

        if prev_role == curr_role and curr_role in ["assistant", "user", "system"]:
            prev_content = str(prev.get("content") or "").strip()
            curr_content = str(msg.get("content") or "").strip()
            if prev_content and curr_content:
                prev["content"] = f"{prev_content}\n\n{curr_content}"
            elif curr_content:
                prev["content"] = curr_content

            if curr_role == "assistant":
                prev_tc = prev.get("tool_calls") or []
                curr_tc = msg.get("tool_calls") or []
                if curr_tc:
                    prev["tool_calls"] = prev_tc + curr_tc
        else:
            merged.append(msg)

    # Step 2: Validate tool call sequencing
    validated: List[Dict[str, Any]] = []
    active_tool_ids = set()
    for msg in merged:
        role = msg.get("role")
        if role == "assistant":
            tc_list = msg.get("tool_calls") or []
            active_tool_ids = {tc.get("id") for tc in tc_list if isinstance(tc, dict) and tc.get("id")}
            validated.append(msg)
        elif role == "tool":
            tc_id = msg.get("tool_call_id")
            if tc_id and tc_id in active_tool_ids:
                validated.append(msg)
            else:
                # Convert orphaned tool observation to user observation
                tool_name = msg.get("name", "tool")
                content = msg.get("content", "")
                validated.append({
                    "role": "user",
                    "content": f"[Observation from {tool_name}]:\n{content}",
                })
                active_tool_ids.clear()
        else:
            active_tool_ids.clear()
            validated.append(msg)

    # Step 3: Second merge pass after orphaned tool conversion
    final_msgs: List[Dict[str, Any]] = []
    for msg in validated:
        if not final_msgs:
            final_msgs.append(msg)
            continue
        prev = final_msgs[-1]
        if prev.get("role") == msg.get("role") and msg.get("role") in ["assistant", "user"]:
            p_c = str(prev.get("content") or "").strip()
            c_c = str(msg.get("content") or "").strip()
            prev["content"] = f"{p_c}\n\n{c_c}" if (p_c and c_c) else (c_c or p_c)
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                prev["tool_calls"] = (prev.get("tool_calls") or []) + msg["tool_calls"]
        else:
            final_msgs.append(msg)

    # Step 4: Ensure never ending with 2 or more assistant messages
    while len(final_msgs) >= 2 and final_msgs[-1].get("role") == "assistant" and final_msgs[-2].get("role") == "assistant":
        last = final_msgs.pop()
        pen = final_msgs[-1]
        p_c = str(pen.get("content") or "").strip()
        l_c = str(last.get("content") or "").strip()
        pen["content"] = f"{p_c}\n\n{l_c}" if (p_c and l_c) else (l_c or p_c)

    return final_msgs


def prune_context(
    messages: List[Any],
    trigger_tokens: int = PRUNE_TRIGGER_TOKENS,
    target_tokens: int = TARGET_HISTORY_TOKENS,
) -> List[Any]:
    """
    C1: Priority-Weighted Pruning with Conversation Structure Integrity.

    Algorithm:
    1. Skip if under trigger threshold.
    2. Score all non-anchor messages (idx 0, 1, and latest are protected).
    3. Phase 1: Compress large tool observations (>300 chars) using smart extraction.
    4. Phase 2: Evict lowest-scored messages until under target.
    5. Phase 3: Sanitize message chain to guarantee alternating roles & no consecutive assistants.
    """
    current_tokens = estimate_messages_tokens(messages)
    if current_tokens <= trigger_tokens:
        return sanitize_messages(messages)

    pruned = list(messages)
    now = time.time()

    # Phase 1: Smart-compress oversized tool observations
    for i in range(2, len(pruned) - 1):
        role = _get_field(pruned[i], "role")
        if role == "tool":
            content = str(_get_field(pruned[i], "content", ""))
            if len(content) > 300:
                compressed = _smart_compress_tool_output(content)
                if isinstance(pruned[i], dict):
                    pruned[i] = dict(pruned[i])  # don't mutate original
                    pruned[i]["content"] = compressed

        if estimate_messages_tokens(pruned) <= target_tokens:
            return sanitize_messages(pruned)

    # Phase 2: Priority-weighted eviction — lowest score evicted first
    while len(pruned) > 4 and estimate_messages_tokens(pruned) > target_tokens:
        total = len(pruned)
        # Score all non-anchored messages (0, 1, and last message are protected)
        scored = [
            (i, _message_priority(pruned[i], i, total, now))
            for i in range(2, total - 1)
        ]
        if not scored:
            break
        # Evict the message with the lowest priority score
        evict_idx = min(scored, key=lambda x: x[1])[0]
        pruned.pop(evict_idx)

    return sanitize_messages(pruned)


def parse_context_size(size_str: str) -> Optional[int]:
    """Parse user-friendly context size string like '32k', '64k', '128k', or '32768'."""
    s = size_str.strip().lower().replace(",", "").replace("_", "")
    if s.endswith("k"):
        try:
            val = float(s[:-1])
            return int(val * 1024)
        except ValueError:
            return None
    elif s.endswith("m"):
        try:
            val = float(s[:-1])
            return int(val * 1024 * 1024)
        except ValueError:
            return None
    try:
        val = int(s)
        return val if val >= 1024 else None
    except ValueError:
        return None


def get_recommended_context_size() -> int:
    """
    Recommend safe context window size based on unified RAM headroom.
    - 32GB+ RAM: 32,768 or 65,536
    - 16GB RAM: 16,384 (safe ceiling)
    - 8GB RAM: 8,192
    """
    try:
        from genesis.core.health_guard import SystemHealthWatchdog
        _, _, stats = SystemHealthWatchdog.evaluate_health_ceiling()
        free_mb = stats.get("available_ram_mb", 8000)
        if free_mb > 20000:
            return 65536
        elif free_mb > 9000:
            return 32768
        elif free_mb < 4000:
            return 8192
        return 16384
    except Exception:
        return 16384

