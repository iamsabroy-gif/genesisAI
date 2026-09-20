"""
Project Genesis: Core Autonomous Agent Engine.
Integrates ReAct loop, Master Authorization Protocol (MAP), Mentorship Memory, and Flight Recorder.
"""

import sys
import json
import time
import uuid
from typing import Optional, List, Dict, Any
from openai import OpenAI

from genesis.config import (
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    DEFAULT_MODEL,
    DRAFT_MODEL,
    MAX_REPAIR_RETRIES,
    MAX_CONTEXT_TOKENS,
)
from genesis.tools.registry import TOOL_MAP, TOOL_SCHEMAS
from genesis.telemetry.flight_recorder import FlightRecorder
from genesis.core.context import prune_context, estimate_messages_tokens, get_context_usage, ContextUsageReport
from genesis.core.state_machine import CognitiveStateMachine, State
from genesis.core.master_auth import MasterAuth
from genesis.memory.mentorship import MentorshipMemory
from genesis.tools.verifier import auto_verify_modification
from genesis.core.deliberation import DeliberationEngine
from genesis.tools.registry import get_schemas_for_task


SYSTEM_PROMPT = """You are Genesis, a sovereign local AI system architect and autonomous engineer running on Apple Silicon.
You are subordinated to the certified Master.

Core Directives:
1. Proactive Solution Architecture: NEVER output canned AI disclaimers or passive refusals (e.g. 'As an AI assistant, I don't have the capability...'). If the Master asks to access or integrate an external service, account, or local data source (such as Gmail, Calendar, databases, or third-party APIs), treat it as an engineering challenge. Break down the technical pathways (e.g., local OAuth2, IMAP, macOS AppleScript, or official SDKs), formulate a clear implementation plan, and offer to build the adapter tool directly into your own codebase (`genesis/tools/`).
2. Codebase Discipline: Always inspect files using read_file or search_code before patching.
3. Surgical Modifications: Use replace_snippet for targeted edits rather than rewriting entire files.
4. Autonomous Verification: Validate changes by running tests or linters via run_command.
5. Mentorship Compliance: Strictly abide by any Mentorship Memory rules anchored in your context.
6. Communication Style: Direct, technical, empowering, and solution-driven. Focus on actionable plans and concrete code.
7. PDF Ingestion Discipline: Whenever a PDF file is shared, uploaded, or referenced, ensure it is converted into a structured Markdown file first before initiating any analysis. Use convert_pdf_to_markdown if you need to convert any PDF, and perform all reading, reasoning, and synthesis on the converted Markdown representation."""


class GenesisAgent:
    """The central agent orchestrator implementing the ReAct + Verify loop with Master Subordination."""

    def __init__(self, model_name: Optional[str] = None):
        from genesis.core.models import ModelManager
        cfg = ModelManager.load_config()
        self.client = OpenAI(
            base_url=cfg.get("base_url", OLLAMA_BASE_URL),
            api_key=cfg.get("api_key", OLLAMA_API_KEY) or "none",
        )
        self.model_name = model_name or cfg.get("model", DEFAULT_MODEL)
        self.state_machine = CognitiveStateMachine()
        self.recorder = FlightRecorder()
        self.master_auth = MasterAuth()
        self.memory = MentorshipMemory()

        # Generate HMAC session token for Master authorization
        self.session_token = self.master_auth.generate_session_token(
            self.recorder.session_id, time.time()
        )

        # Wire Base Tools + Connector Hub Tools dynamically
        from genesis.connectors.hub import get_default_hub
        hub = get_default_hub()
        self.tool_map = dict(TOOL_MAP)
        self.tool_map.update(hub.get_active_tool_map())
        self.tool_schemas = list(TOOL_SCHEMAS)
        existing_names = {s["function"]["name"] for s in self.tool_schemas}
        for s in hub.get_active_tool_schemas():
            if s["function"]["name"] not in existing_names:
                self.tool_schemas.append(s)

        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.recorder.record_step("system", SYSTEM_PROMPT)

        # Asynchronous Task Interruption & Command Queueing
        import threading
        self.abort_requested = threading.Event()
        self.command_queue: List[str] = []
        self.is_running_task: bool = False

        # M3: Adaptive temperature — updated per cognitive phase before each LLM call
        self._current_temperature: float = 0.2

        # Context Window Ceiling (configurable per agent session)
        self.max_context_tokens: int = MAX_CONTEXT_TOKENS

        # A2: In-session tool result memoization — {cache_key: (result_str, timestamp)}
        # Only read-only tools are cached; write/shell tools always execute fresh.
        self._tool_cache: Dict[str, tuple] = {}
        self._CACHEABLE_TOOLS = frozenset(["read_file", "search_code", "list_files"])
        self._CACHE_TTL_SECONDS: float = 60.0

    # ── M3: Adaptive Temperature ────────────────────────────────────────────
    def _phase_temperature(self) -> float:
        """
        Return optimal temperature for the current cognitive state (M3).

        | State   | Temp | Rationale                                        |
        |---------|------|--------------------------------------------------|
        | THINK   | 0.2  | Balanced reasoning for tool selection            |
        | ACT     | 0.0  | Deterministic tool dispatch — no variance wanted |
        | CORRECT | 0.1  | Precise targeted repair                          |
        | OBSERVE | 0.15 | Synthesizing observations                        |
        | Default | 0.25 | Final answer / exploration                       |
        """
        temp_map = {
            State.ACT:     0.0,
            State.CORRECT: 0.1,
            State.OBSERVE: 0.15,
            State.THINK:   0.2,
        }
        return temp_map.get(self.state_machine.state, 0.25)

    # ── M5: Draft Model Router ───────────────────────────────────────────────
    _DRAFT_TRIGGERS = frozenset([
        "what is", "how do i", "explain", "define", "list", "tell me",
        "summarize", "what does", "who is", "show me", "when was",
        "status", "help", "hello", "hi", "thanks", "yes", "no", "ok",
    ])
    _COMPLEX_TRIGGERS = frozenset([
        "write", "implement", "create", "fix", "debug", "refactor", "add",
        "build", "generate", "update", "modify", "replace", "delete",
        "test", "deploy", "install", "configure", "optimize", "analyze",
    ])
    _draft_model_available: Optional[bool] = None  # None = not yet checked

    def _select_model_for_prompt(self, prompt: str) -> str:
        """
        M5: Route simple conversational queries to the draft (small/fast) model.
        Complex coding/reasoning tasks always use the full model.

        Caches availability check — draft model tested once per session.
        """
        if not DRAFT_MODEL or DRAFT_MODEL == self.model_name:
            return self.model_name

        # Lazy-check draft model availability (once per session)
        if self.__class__._draft_model_available is None:
            try:
                resp = self.client.models.list()
                available = {m.id for m in resp.data}
                self.__class__._draft_model_available = DRAFT_MODEL in available
            except Exception:
                self.__class__._draft_model_available = False

        if not self.__class__._draft_model_available:
            return self.model_name

        p = prompt.lower().strip()
        words = set(p.split())

        # Any complex trigger → always use full model
        if words & self._COMPLEX_TRIGGERS:
            return self.model_name

        # Short prompt + only draft triggers → use draft
        if len(prompt) < 120 and (words & self._DRAFT_TRIGGERS):
            return DRAFT_MODEL

        return self.model_name

    def abort_current_task(self) -> str:
        """Interrupt and halt the current running task, terminating all child subprocesses."""
        self.abort_requested.set()
        from genesis.tools.shell import terminate_active_processes
        killed = terminate_active_processes()
        self.state_machine.transition(State.IDLE, reason="Master task interruption")
        msg = f"MASTER OVERRIDE: Task interrupted. Halted execution ({killed} child subprocesses killed)."
        self.recorder.record_step("master_interrupt", {"killed_subprocesses": killed})
        return msg

    def is_aborted(self) -> bool:
        """Check if an abort signal has been requested by the Master."""
        return self.abort_requested.is_set()

    # ── A5: Early Exit Confidence Scorer ────────────────────────────────────
    _COMPLETION_SIGNALS = frozenset([
        "all tests passed", "test passed", "exit code: 0", "exit code 0",
        "auto-verification passed",
    ])

    def _is_task_complete(self, tool_name: str = "", last_tool_result: str = "", last_response: str = "") -> bool:
        """
        A5: Early-exit heuristic — returns True ONLY when a verification/test command
        has explicitly succeeded. Informational queries (web search, file reading, code search)
        must never early-exit; the LLM must synthesize and answer the user.
        """
        # Only allow early exit for verification/execution commands
        if tool_name not in ["run_command", "auto_verify_modification"]:
            return False

        if not last_tool_result:
            return False

        combined = (last_tool_result + " " + last_response).lower()
        # Must see at least one explicit test/verification success signal
        if not any(sig in combined for sig in self._COMPLETION_SIGNALS):
            return False
        # Must NOT see any failure signals
        failure_signals = ["failed", "error", "traceback", "exit code 1", "syntax error", "exception", "failure"]
        if any(sig in combined for sig in failure_signals):
            return False
        return True


    def queue_command(self, cmd: str) -> int:
        """Add a command to the pending execution queue. Returns queue length."""
        self.command_queue.append(cmd)
        return len(self.command_queue)

    def pop_next_command(self) -> Optional[str]:
        """Pop the next pending command from the queue."""
        if self.command_queue:
            return self.command_queue.pop(0)
        return None

    def get_queued_commands(self) -> List[str]:
        """Get list of currently queued commands."""
        return list(self.command_queue)

    def clear_command_queue(self) -> int:
        """Clear all queued commands. Returns number of commands removed."""
        count = len(self.command_queue)
        self.command_queue.clear()
        return count

    def select_active_model(self) -> str:
        """Verify model availability with Ollama or fallback to an installed model."""
        try:
            models_response = self.client.models.list()
            available_ids = [m.id for m in models_response.data]

            if self.model_name in available_ids:
                return self.model_name

            for mid in available_ids:
                if self.model_name.split(":")[0] in mid:
                    self.model_name = mid
                    return mid

            if available_ids:
                self.model_name = available_ids[0]
                return self.model_name
        except Exception:
            pass
        return self.model_name

    def switch_model(
        self,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Switch active model and provider endpoint dynamically."""
        from genesis.core.models import ModelManager
        return ModelManager.switch_model(
            self,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider=provider,
        )

    def set_max_context(self, tokens: int) -> int:
        """Dynamically adjust context ceiling for the active session."""
        self.max_context_tokens = max(2048, tokens)
        return self.max_context_tokens

    def get_context_usage(self) -> ContextUsageReport:
        """Get structured real-time context token usage, remaining buffer, and visual gauge."""
        return get_context_usage(self.messages, max_tokens=self.max_context_tokens)

    def _llm_stream(self, stream_to_terminal: bool = False) -> Any:
        """
        Execute LLM forward pass, optionally streaming text tokens to terminal.
        Returns a StreamedMessage compatible with _extract_tool_calls().
        """
        # C4: Classify task → load only relevant tool schemas (~600 → ~200 tokens saved)
        last_user_msg = next(
            (m.get("content", "") for m in reversed(self.messages) if isinstance(m, dict) and m.get("role") == "user"),
            ""
        )
        from genesis.tools.registry import CALENDAR_TOOLS
        default_fallback = [s for s in self.tool_schemas if s["function"]["name"] not in CALENDAR_TOOLS]
        active_schemas = get_schemas_for_task(str(last_user_msg), self.tool_schemas) if last_user_msg else default_fallback
        active_model = self._select_model_for_prompt(str(last_user_msg)) if last_user_msg else self.model_name

        extra_body: Dict[str, Any] = {
            "keep_alive": -1,  # M1: keep model warm; no cold-start between turns
            "options": {"num_ctx": self.max_context_tokens},  # Request exact context window from Ollama
        }

        stream = self.client.chat.completions.create(
            model=active_model,
            messages=self.messages,
            tools=active_schemas,
            temperature=self._current_temperature,
            stream=True,
            extra_body=extra_body,
        )

        collected_content: List[str] = []
        tool_calls_acc: Dict[int, Dict[str, Any]] = {}
        # ANSI colors for distinct model output
        CYAN = "\033[96m"
        RESET = "\033[0m"
        started_streaming = False

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # Stream text tokens to terminal only if stream_to_terminal is requested
            if delta.content:
                collected_content.append(delta.content)
                if stream_to_terminal:
                    if not started_streaming:
                        sys.stdout.write(CYAN)
                        started_streaming = True
                    sys.stdout.write(delta.content)
                    sys.stdout.flush()

            # Accumulate tool call fragments (arrive in pieces across chunks)
            if delta.tool_calls:
                for tc_chunk in delta.tool_calls:
                    idx = tc_chunk.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                    if tc_chunk.id:
                        tool_calls_acc[idx]["id"] += tc_chunk.id
                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            tool_calls_acc[idx]["function"]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tool_calls_acc[idx]["function"]["arguments"] += tc_chunk.function.arguments

        # Reset ANSI color and newline after streamed text so next prompt starts cleanly
        if stream_to_terminal:
            if started_streaming:
                sys.stdout.write(RESET)
            if collected_content:
                sys.stdout.write("\n")
                sys.stdout.flush()

        content = "".join(collected_content) or None

        # Reconstruct tool_calls as attribute-bearing objects compatible with _extract_tool_calls()
        class _FnObj:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments

        class _TcObj:
            def __init__(self, id_, fn):
                self.id = id_
                self.function = fn

        tool_calls_out = None
        if tool_calls_acc:
            tool_calls_out = [
                _TcObj(v["id"], _FnObj(v["function"]["name"], v["function"]["arguments"]))
                for _, v in sorted(tool_calls_acc.items())
            ]

        class StreamedMessage:
            """Mimics openai.types.chat.ChatCompletionMessage for streamed responses."""
            def __init__(self, content_, tool_calls_):
                self.content = content_
                self.tool_calls = tool_calls_

            def model_dump(self, **kwargs):
                d = {"role": "assistant", "content": self.content}
                if self.tool_calls:
                    d["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in self.tool_calls
                    ]
                return d

        return StreamedMessage(content, tool_calls_out)

    def _extract_tool_calls(self, msg) -> List[Dict[str, Any]]:
        """Extract tool calls from native msg.tool_calls or JSON content fallback."""
        extracted = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                extracted.append({"id": tc.id, "name": tc.function.name, "arguments": args})
            return extracted

        # Fallback: check if content string contains a JSON tool call block
        content = (getattr(msg, "content", "") or "").strip()
        if "{" in content and "}" in content:
            # Try full string parse first
            try:
                parsed = json.loads(content)
                if "name" in parsed and "arguments" in parsed and parsed["name"] in self.tool_map:
                    extracted.append({
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "name": parsed["name"],
                        "arguments": parsed.get("arguments", {}),
                    })
                    return extracted
            except Exception:
                pass

            # Try extracting JSON block from mixed commentary
            import re
            json_matches = re.findall(r'(\{[^{}]*"name"\s*:\s*"([a-zA-Z0-9_]+)"[^{}]*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\})', content, re.DOTALL)
            for full_block, fn_name in json_matches:
                if fn_name in self.tool_map:
                    try:
                        parsed = json.loads(full_block)
                        extracted.append({
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "name": fn_name,
                            "arguments": parsed.get("arguments", {}),
                        })
                    except Exception:
                        pass
        return extracted

    def run_turn(self, user_prompt: str) -> str:
        """
        Execute a full turn through the cognitive state machine.
        Master signals (!HALT, !REVERT, !LOCK, !STATUS, !PURGE) bypass LLM inference completely.
        """
        # Preemptive Master Signal Trap
        if self.master_auth.is_master_signal(user_prompt):
            context = {
                "estimated_tokens": estimate_messages_tokens(self.messages),
                "context_usage": self.get_context_usage(),
                "history_len": len(self.messages),
                "model": self.model_name,
                "recorder": self.recorder,
                "memory": self.memory,
                "agent": self,
            }
            output, target_state = self.master_auth.execute_master_signal(user_prompt, context)
            if target_state != "NO_TRANSITION":
                self.state_machine.transition(State[target_state], reason=f"Master signal {user_prompt}")
            self.recorder.record_step("master_override", {"signal": user_prompt, "output": output})
            return output

        # Check if agent is currently locked
        if self.master_auth.read_only_lock:
            self.state_machine.transition(State.READ_ONLY_LOCK, reason="Action attempted during lock")

        self.state_machine.transition(State.PERCEIVE, reason="User input received")

        # Real-Time System Health Ceiling Gate (Apple Silicon 16GB RAM Protection)
        from genesis.core.health_guard import SystemHealthWatchdog
        health_status, health_msg, health_stats = SystemHealthWatchdog.evaluate_health_ceiling()
        if health_status == "CRITICAL":
            critical_warning = (
                f"[System Health Guard Triggered]: {health_msg}\n"
                f"Halting autonomous execution to prevent macOS virtual memory swap freeze.\n"
                f"Issue '!STATUS' or check activity monitor."
            )
            self.state_machine.transition(State.COMPLETE, reason="Critical health ceiling reached")
            self.recorder.record_step("health_guard_trip", health_stats)
            return critical_warning
        elif health_status == "WARNING":
            # Preemptively prune context to lower RAM usage
            self.messages = prune_context(self.messages, target_tokens=6000)

        # Auto-convert any referenced PDF files into Markdown before proceeding with analysis
        from genesis.tools.pdf_converter import auto_convert_prompt_pdfs
        processed_prompt, converted_pdfs = auto_convert_prompt_pdfs(user_prompt)

        # Query Mentorship Memory & C3 Trajectory RAG for relevant past guidance & solutions
        memory_anchor = self.memory.format_combined_context(processed_prompt)
        augmented_prompt = processed_prompt
        if memory_anchor:
            augmented_prompt = f"{memory_anchor}\n\n[User Goal]:\n{processed_prompt}"

        self.messages.append({"role": "user", "content": augmented_prompt})
        self.recorder.record_step("user", augmented_prompt)

        max_iterations = 15
        iteration = 0
        final_answer = ""

        self.state_machine.reset_retries()  # Reset per-turn repair retry counter
        self.abort_requested.clear()
        self.is_running_task = True

        try:
            while iteration < max_iterations:
                iteration += 1

                if self.abort_requested.is_set():
                    return self.abort_current_task()

                # 1. Prune Context if needed
                self.messages = prune_context(
                    self.messages,
                    trigger_tokens=int(self.max_context_tokens * 0.75),
                    target_tokens=int(self.max_context_tokens * 0.66),
                )

                # 2. Think (LLM Forward Pass — streamed token-by-token to terminal)
                self.state_machine.transition(State.THINK, reason=f"Iteration {iteration}")
                self._current_temperature = self._phase_temperature()  # M3: phase-aware temp
                try:
                    msg = self._llm_stream()
                except Exception as e:
                    if self.abort_requested.is_set():
                        return self.abort_current_task()
                    err_msg = f"LLM Inference Error: {e}"
                    self.state_machine.transition(State.CORRECT, reason=err_msg)
                    return err_msg

                # Append the (possibly streamed) assistant message to history
                if hasattr(msg, "model_dump"):
                    self.messages.append(msg.model_dump(exclude_unset=True))
                elif isinstance(msg, dict):
                    self.messages.append(msg)
                else:
                    self.messages.append({"role": "assistant", "content": getattr(msg, "content", "")})

                # 3. Extract tool calls (native tool_calls or JSON content fallback)
                tool_calls = self._extract_tool_calls(msg)

                if not tool_calls:
                    final_answer = msg.content or ""
                    self.state_machine.transition(State.COMPLETE, reason="No tool calls emitted")
                    self.recorder.record_step("assistant", final_answer)
                    break

                # 4. Act (Execute Tool Calls) — all dispatch logic is INSIDE the loop
                self.state_machine.transition(State.ACT, reason="Dispatching tool calls")

                # A1: Parallel pre-execution of read-only tools in this batch
                # Runs all read_file / search_code / list_files calls concurrently via ThreadPool.
                # Results stored in memoization cache → sequential loop picks them up instantly.
                _read_only_calls = [
                    tc for tc in tool_calls
                    if tc["name"] in self._CACHEABLE_TOOLS
                ]
                if len(_read_only_calls) > 1:
                    import concurrent.futures

                    def _prefetch(tc_item):
                        h = self.tool_map.get(tc_item["name"])
                        if h:
                            result = h(**tc_item["arguments"])
                            cache_key = f"{tc_item['name']}:{sorted(tc_item['arguments'].items())}"
                            self._tool_cache[cache_key] = (result, time.time())

                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                        pool.map(_prefetch, _read_only_calls)

                for tc in tool_calls:
                    if self.abort_requested.is_set():
                        return self.abort_current_task()

                    fn_name = tc["name"]
                    fn_args = tc["arguments"]
                    tc_id = tc["id"]

                    self.recorder.record_step(
                        "assistant_tool_call",
                        {"name": fn_name, "arguments": fn_args, "id": tc_id},
                    )

                    # Safety Check: If in READ_ONLY_LOCK, deny mutating tools
                    if self.master_auth.read_only_lock and fn_name in ["write_file", "replace_snippet", "run_command"]:
                        result = "Error: Tool execution blocked. Agent is in READ_ONLY_LOCK by Master command. Issue !UNLOCK to restore."
                    else:
                        # Deliberation Gate: risk-check destructive writes before executing
                        if fn_name in ["write_file", "replace_snippet"]:
                            delib_trace = DeliberationEngine.deliberate(
                                intent=str(self.messages[-1].get("content", "") if isinstance(self.messages[-1], dict) else ""),
                                proposed_action=f"{fn_name}({fn_args})",
                            )
                            if not delib_trace["approved"]:
                                # Inject deliberation warning as an observation — let model reconsider
                                result = DeliberationEngine.format_deliberation(delib_trace)
                                self.messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc_id,
                                    "name": fn_name,
                                    "content": result,
                                })
                                self.recorder.record_step("deliberation_block", result, {"name": fn_name})
                                continue  # Skip execution; let next iteration handle it

                        self.state_machine.transition(State.OBSERVE, reason=f"Executing {fn_name}")
                        handler = self.tool_map.get(fn_name)
                        if handler:
                            # A2: Memoization — serve cached result for read-only tools within TTL
                            cache_key = f"{fn_name}:{sorted(fn_args.items())}"
                            if fn_name in self._CACHEABLE_TOOLS and cache_key in self._tool_cache:
                                cached_result, cached_at = self._tool_cache[cache_key]
                                if time.time() - cached_at < self._CACHE_TTL_SECONDS:
                                    result = cached_result + "  [cached]"
                                else:
                                    del self._tool_cache[cache_key]
                                    result = handler(**fn_args)
                                    self._tool_cache[cache_key] = (result, time.time())
                            else:
                                result = handler(**fn_args)
                                if fn_name in self._CACHEABLE_TOOLS:
                                    self._tool_cache[cache_key] = (result, time.time())
                        else:
                            result = f"Error: Tool '{fn_name}' not recognized."

                        # Autonomous Self-Verification Sub-Routine (algo.md Section 4)
                        if fn_name in ["write_file", "replace_snippet"] and "path" in fn_args:
                            v_passed, v_msg = auto_verify_modification(fn_args["path"])
                            if v_msg:
                                result = f"{result}\n{v_msg}"
                            if not v_passed:
                                self.state_machine.transition(State.CORRECT, reason="Auto-verification failed")
                                self.state_machine.record_retry()
                                self.recorder.set_test_status(False)
                            else:
                                self.recorder.set_test_status(True)

                    # Append tool observation for this specific tool call
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": fn_name,
                        "content": str(result),
                    })
                    self.recorder.record_step("tool_observation", result, {"name": fn_name})

                    # A5: Early-exit — if verification or test passed, skip next LLM iteration
                    if self._is_task_complete(tool_name=fn_name, last_tool_result=str(result)):
                        final_answer = f"✅ Task verified complete.\n{result}"
                        self.state_machine.transition(State.COMPLETE, reason="A5 early-exit: task complete signal detected")
                        self.recorder.record_step("assistant", final_answer)
                        return final_answer

                    # Check if this observation contains a test failure that triggers self-correction
                    if ("exit code" in str(result).lower() and "exit code 0" not in str(result).lower()) or "Auto-Verification FAILED" in str(result):
                        self.state_machine.transition(State.CORRECT, reason="Verification or test failure detected")
                        self.state_machine.record_retry()
                        if not self.state_machine.can_retry():
                            diagnostic_report = (
                                f"[Diagnostic Backoff - algo.md Section 4.1]: Maximum automated repair retries ({MAX_REPAIR_RETRIES}) reached. "
                                f"Halted to prevent infinite circular repair loop.\n"
                                f"Latest Observation Failure:\n{result}\n"
                                f"Issue !REVERT to discard changes, or guide Genesis with specific instructions."
                            )
                            self.state_machine.transition(State.COMPLETE, reason="Max repair retries reached")
                            self.recorder.record_step("assistant", diagnostic_report)
                            return diagnostic_report

            return final_answer
        finally:
            self.is_running_task = False

    def close(self, user_feedback: int = 0, unload_model: bool = True) -> str:
        """Finalize session, score trajectory, and record to disk. Frees Unified RAM."""
        self.state_machine.transition(State.TERMINATE, reason="Session closed")
        self.recorder.set_feedback(user_feedback)
        path = self.recorder.finalize(outcome="completed")
        if unload_model:
            self.unload_model()
        return str(path)

    def unload_model(self) -> bool:
        """Explicitly instruct Ollama to evict model weights from volatile Unified RAM immediately."""
        try:
            from genesis.core.kill_switch import evict_all_models_from_vram
            evict_all_models_from_vram()
            return True
        except Exception:
            return False
