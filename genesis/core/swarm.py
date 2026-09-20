"""
Project Genesis: Autonomous Multi-Agent Swarm Orchestrator.
Spawns specialized worker agents that collaborate continuously until a target goal is achieved.
C6: Per-worker context isolation — each worker gets its own scoped context slice.
C2: Turn summarization — verbose worker outputs are compressed before passing to next worker.
A3: Async swarm workers — support async execution and parallel sub-scouting via thread pool.
Engineered with Memory Multiplexing to operate safely within 16 GB Apple Silicon bounds.
"""

import time
import json
import re
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel

from genesis.core.agent import GenesisAgent
from genesis.core.health_guard import SystemHealthWatchdog
from genesis.core.context import prune_context, estimate_tokens
from genesis.config import GENESIS_HOME

console = Console()
SWARM_DOSSIER_DIR = GENESIS_HOME / "swarm"
SWARM_DOSSIER_DIR.mkdir(parents=True, exist_ok=True)

# C6: Max tokens per worker's summary passed to the next worker (keeps inter-worker context lean)
_WORKER_SUMMARY_MAX_CHARS = 1200
# C2: Turn summarization — compress worker output above this char length
_SUMMARIZE_ABOVE_CHARS = 800


def _summarize_output(text: str, max_chars: int = _WORKER_SUMMARY_MAX_CHARS) -> str:
    """
    C2: Compress a long worker output to a concise summary stub.
    Strategy:
    1. If under limit, return as-is.
    2. Extract key lines: first paragraph, any "FOUND / ERROR / RESULT / PASS / FAIL" lines, last line.
    3. Truncate to max_chars with a marker.
    """
    if len(text) <= max_chars:
        return text

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    key_lines = []

    # First paragraph (up to 3 lines)
    key_lines.extend(lines[:3])

    # Signal lines containing important keywords
    keywords = ["found", "error", "fail", "pass", "result", "complete", "exit code",
                "fixed", "wrote", "created", "tests", "verified", "success"]
    for line in lines[3:]:
        if any(kw in line.lower() for kw in keywords):
            key_lines.append(line)
            if len(key_lines) >= 8:
                break

    # Last line (often contains outcome)
    if lines[-1] not in key_lines:
        key_lines.append(lines[-1])

    summary = "\n".join(key_lines)
    if len(summary) > max_chars:
        summary = summary[:max_chars] + f"\n... [{len(text)} chars total, compressed]"
    return summary




class SwarmWorker:
    """A specialized persona operating within the shared neural memory pool."""

    def __init__(self, name: str, role_title: str, system_prompt: str):
        self.name = name
        self.role_title = role_title
        self.system_prompt = system_prompt


class SwarmCoordinator:
    """
    Coordinates a multi-agent swarm to execute tasks continuously
    until an empirical verification judge confirms the goal is 100% achieved.
    """

    def __init__(self, base_agent: Optional[GenesisAgent] = None):
        self.agent = base_agent or GenesisAgent()
        self.workers = self._initialize_default_swarm()

    def _initialize_default_swarm(self) -> Dict[str, SwarmWorker]:
        return {
            "researcher": SwarmWorker(
                name="Researcher",
                role_title="Codebase, Dependency & Intelligence Specialist",
                system_prompt=(
                    "You are the Swarm Reconnaissance & Research Specialist. Your role is to gather empirical facts, "
                    "technical ground-truth, and background information to achieve the overarching goal. "
                    "For software engineering goals, inspect directory structures and symbols using list_files, search_code, or read_file. "
                    "For domain research, analysis, or report requests (e.g. ethanol blending, system architectures, market reports), "
                    "use web_search, web_research, or internal technical knowledge to compile complete, substantive findings. "
                    "CRITICAL: You are running in an AUTONOMOUS SWARM. There is NO human to answer questions. "
                    "NEVER ask the user for directory paths or clarification. Take decisive action and report findings directly."
                ),
            ),
            "implementer": SwarmWorker(
                name="Implementer",
                role_title="Lead Surgical Systems Builder & Author",
                system_prompt=(
                    "You are the Swarm Lead Implementer & Author. Your role is to build the concrete deliverables required by the goal. "
                    "For software goals, write, modify, or patch code using replace_snippet and write_file. "
                    "For report, document, or analytical requests, author a thorough, professional, and comprehensive Markdown report "
                    "and write it directly to an appropriate workspace file (e.g. '<topic>_report.md' or 'documents/<topic>_report.md') using write_file. "
                    "CRITICAL: NEVER ask the user clarifying questions or ask where to save files. Write the deliverable directly to disk."
                ),
            ),
            "tester": SwarmWorker(
                name="Tester",
                role_title="Autonomous QA & Verification Lead",
                system_prompt=(
                    "You are the Swarm QA Tester. Your role is to empirically verify that the deliverable exists and satisfies the goal. "
                    "For code: execute tests, linters, or syntax checks using run_command. "
                    "For reports or documents: verify the file exists on disk, check line count and word count using run_command "
                    "(e.g. 'wc -w <filename>' or 'ls -lh <filename>'), and inspect the structure. "
                    "Report exact verification evidence and exit codes."
                ),
            ),
            "judge": SwarmWorker(
                name="Judge",
                role_title="Empirical Goal Verification Arbiter",
                system_prompt=(
                    "You are the Swarm Goal Verification Judge. Your sole responsibility is to evaluate whether "
                    "the user's overarching goal has been completely achieved based on empirical deliverables and verification evidence. "
                    "If the requested code tests pass OR if the requested report/document has been thoroughly written and verified on disk, "
                    "emit 'GOAL_ACHIEVED: YES'. Otherwise, emit 'GOAL_ACHIEVED: NO' and list exact concrete missing artifacts. "
                    "CRITICAL: NEVER ask the human user questions. State only objective criteria for the next swarm iteration."
                ),
            ),
        }

    def _render_context_status(self, label: str = ""):
        """Render real-time context status concisely without polluting user logs."""
        usage = self.agent.get_context_usage()
        if usage.usage_percentage >= 75:
            console.print(f"[yellow dim]  ⚠ Context at {usage.usage_percentage:.0f}% ({usage.remaining_tokens:,} tokens left)[/yellow dim]")

    def run_swarm(
        self,
        goal: str,
        max_rounds: int = 5,
        target_verification_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the continuous swarm loop until the goal is achieved or max_rounds is reached.
        Includes real-time context tracking and anti-stalling autonomous directives.
        """
        swarm_id = f"swarm_{int(time.time())}"
        session_dossier = {
            "swarm_id": swarm_id,
            "goal": goal,
            "start_time": time.time(),
            "rounds": [],
            "status": "IN_PROGRESS",
            "summary": "",
        }

        console.print(
            Panel(
                f"[bold cyan]Swarm Goal:[/bold cyan] [white]{goal}[/white]\n"
                f"[dim]Multi-agent loop: Researcher → Implementer → Tester → Judge[/dim]\n"
                f"[dim]Press [bold]Ctrl+C[/bold] anytime to stop swarm.[/dim]",
                title="[bold white]🐝 Multi-Agent Swarm[/bold white]",
                border_style="cyan",
            )
        )

        current_instructions = goal
        accumulated_context = ""

        # Detect if goal explicitly invokes the 5-phase deep research swarm
        is_deep_research = (
            goal.lower().strip().startswith("research:") or
            goal.lower().strip().startswith("/research") or
            goal.lower().strip().startswith("deep research")
        )

        if is_deep_research:
            clean_topic = goal
            format_choice = "comprehensive"
            fmt_match = re.search(r'(?:--format|-f)\s+([a-zA-Z_-]+)', clean_topic, re.IGNORECASE)
            if fmt_match:
                format_choice = fmt_match.group(1).lower()
                clean_topic = re.sub(r'(?:--format|-f)\s+[a-zA-Z_-]+', '', clean_topic).strip()

            urls_match = re.search(r'(?:--urls|-u)\s+(\d+)', clean_topic, re.IGNORECASE)
            target_urls = int(urls_match.group(1)) if urls_match else 10
            if urls_match:
                clean_topic = re.sub(r'(?:--urls|-u)\s+\d+', '', clean_topic).strip()

            for prefix in ["research:", "/research", "deep research"]:
                if clean_topic.lower().startswith(prefix):
                    clean_topic = clean_topic[len(prefix):].strip()
                    break
            from genesis.core.research_swarm import ResearchSwarmCoordinator
            res_swarm = ResearchSwarmCoordinator(base_agent=self.agent)
            return res_swarm.run_research_swarm(clean_topic or goal, report_format=format_choice, target_urls=target_urls)

        # Detect if goal is primarily an analytical report or documentation
        is_report_task = any(w in goal.lower() for w in ["report", "research", "analyze", "analysis", "summary", "document", "overview"])


        try:
            for round_idx in range(1, max_rounds + 1):
                if self.agent.is_aborted():
                    session_dossier["status"] = "ABORTED_BY_MASTER"
                    session_dossier["summary"] = "Swarm execution aborted by Master interrupt."
                    console.print("\n[bold red]Swarm aborted by Master interrupt.[/bold red]")
                    return session_dossier

                round_data = {"round": round_idx, "actions": []}
                console.print(f"\n[bold yellow]── Swarm Round {round_idx} of {max_rounds} ─────────────────────────────[/bold yellow]")

                # Health Guard check before each round
                status, msg, _ = SystemHealthWatchdog.evaluate_health_ceiling()
                if status == "CRITICAL":
                    session_dossier["status"] = "ABORTED_HEALTH_CEILING"
                    session_dossier["summary"] = f"Swarm halted: System health warning ({msg})"
                    return session_dossier

                # -------------------------------------------------------------
                # C6: Per-worker context isolation — save & restore agent messages
                # Workers communicate via summarized output strings only
                # -------------------------------------------------------------
                _saved_messages = list(self.agent.messages)  # snapshot before workers start

                # Worker 1: Researcher / Reconnaissance
                # -------------------------------------------------------------
                console.print("[cyan]🔍 [1/4] Researching requirements & codebase...[/cyan]")
                if is_report_task:
                    recon_guidance = (
                        "For this report/research goal: use web_search, web_research, or internal domain expertise "
                        "to synthesize key facts, statistics, policies, challenges, and solutions. "
                        "Do NOT ask for paths. Provide complete research notes to feed into the report."
                    )
                else:
                    recon_guidance = "Explore files using list_files or search_code. Report exact symbols, paths and requirements."

                recon_prompt = (
                    f"[{self.workers['researcher'].system_prompt}]\n\n"
                    f"OVERARCHING GOAL: '{goal}'\n"
                    f"CURRENT FOCUS: '{current_instructions}'\n"
                    f"PRIOR CONTEXT:\n{accumulated_context[-1200:] if accumulated_context else 'None'}\n\n"
                    f"{recon_guidance}\n"
                    f"CRITICAL: Do NOT ask questions. Report concrete findings in under 300 words."
                )
                # C6: Isolated context for researcher
                self.agent.messages = [_saved_messages[0]]  # keep only system prompt
                recon_output = self.agent.run_turn(recon_prompt)
                recon_summary = _summarize_output(recon_output)  # C2: compress for next worker
                round_data["actions"].append({"worker": "researcher", "output": recon_output})
                self._render_context_status("Researcher")

                if self.agent.is_aborted():
                    self.agent.messages = _saved_messages  # restore on abort
                    session_dossier["status"] = "ABORTED_BY_MASTER"
                    session_dossier["summary"] = "Swarm halted after Researcher by Master interrupt."
                    return session_dossier

                # -------------------------------------------------------------
                # Worker 2: Implementer / Builder
                # -------------------------------------------------------------
                console.print("[green]✍️ [2/4] Implementing changes & deliverables...[/green]")
                if is_report_task:
                    # Formulate default report filename
                    clean_slug = re.sub(r'[^a-zA-Z0-9_]+', '_', goal.lower().replace("report", "").replace("give me a", "").replace("complete", "").strip())
                    clean_slug = clean_slug.strip("_") or "report"
                    target_report_file = f"{clean_slug}_report.md"
                    impl_guidance = (
                        f"Author a comprehensive, detailed, professional Markdown report and write it directly to '{target_report_file}' using write_file. "
                        f"Include Executive Summary, Technical Architecture/Mechanisms, Policy/Standards, Challenges, and Strategic Recommendations. "
                        f"Write the full file immediately."
                    )
                else:
                    impl_guidance = "Implement the necessary changes using write_file or replace_snippet. Do not guess paths; use exact paths identified by Researcher."

                impl_prompt = (
                    f"[{self.workers['implementer'].system_prompt}]\n\n"
                    f"GOAL: '{goal}'\n"
                    f"RECONNAISSANCE FINDINGS:\n{recon_summary}\n\n"
                    f"{impl_guidance}\n"
                    f"CRITICAL: Do NOT ask the user where to save or what to do. Execute the action immediately."
                )
                # C6: Isolated context for implementer
                self.agent.messages = [_saved_messages[0]]
                impl_output = self.agent.run_turn(impl_prompt)
                impl_summary = _summarize_output(impl_output)  # C2: compress for next worker
                round_data["actions"].append({"worker": "implementer", "output": impl_output})
                self._render_context_status("Implementer")

                if self.agent.is_aborted():
                    self.agent.messages = _saved_messages
                    session_dossier["status"] = "ABORTED_BY_MASTER"
                    session_dossier["summary"] = "Swarm halted after Implementer by Master interrupt."
                    return session_dossier

                # -------------------------------------------------------------
                # Worker 3: QA Tester / Test Execution
                # -------------------------------------------------------------
                console.print("[magenta]🧪 [3/4] Verifying and testing deliverables...[/magenta]")
                if is_report_task:
                    test_guidance = (
                        f"Verify that '{target_report_file}' exists on disk and has substantial content. "
                        f"Use run_command with 'ls -lh {target_report_file} && wc -w {target_report_file}' to inspect file size and word count. "
                        f"Report whether the deliverable is complete."
                    )
                else:
                    test_target = target_verification_command or "run relevant pytest or syntax check"
                    test_guidance = f"Execute the test verification ({test_target}) using run_command. Report exact exit codes and test output summaries."

                test_prompt = (
                    f"[{self.workers['tester'].system_prompt}]\n\n"
                    f"GOAL: '{goal}'\n"
                    f"RECENT ACTIONS:\n{impl_summary}\n\n"
                    f"{test_guidance}"
                )
                # C6: Isolated context for tester
                self.agent.messages = [_saved_messages[0]]
                test_output = self.agent.run_turn(test_prompt)
                test_summary = _summarize_output(test_output)  # C2: compress for judge
                round_data["actions"].append({"worker": "tester", "output": test_output})
                self._render_context_status("Tester")

                if self.agent.is_aborted():
                    self.agent.messages = _saved_messages
                    session_dossier["status"] = "ABORTED_BY_MASTER"
                    session_dossier["summary"] = "Swarm halted after Tester by Master interrupt."
                    return session_dossier

                # -------------------------------------------------------------
                # Worker 4: Judge / Goal Verifier (The Stopping Condition)
                # -------------------------------------------------------------
                console.print("[bold cyan]⚖️ [4/4] Reviewing goal completion criteria...[/bold cyan]")
                judge_prompt = (
                    f"[{self.workers['judge'].system_prompt}]\n\n"
                    f"USER GOAL: '{goal}'\n"
                    f"DELIVERABLES & VERIFICATION EVIDENCE:\n{test_summary}\n\n"
                    f"Did the swarm achieve the goal? "
                    f"If the deliverable exists and verification shows successful outcome, emit 'GOAL_ACHIEVED: YES'. "
                    f"Otherwise, respond with 'GOAL_ACHIEVED: NO' and specify what needs fixing. "
                    f"Do NOT ask the user questions."
                )
                # C6: Isolated context for judge
                self.agent.messages = [_saved_messages[0]]
                judge_output = self.agent.run_turn(judge_prompt)
                round_data["actions"].append({"worker": "judge", "output": judge_output})
                session_dossier["rounds"].append(round_data)
                self._render_context_status("Judge")

                # Restore agent messages after all 4 workers finish this round
                self.agent.messages = _saved_messages

                # Check if judge certified goal completion
                if "GOAL_ACHIEVED: YES" in judge_output.upper():
                    console.print(f"\n[bold green]🎯 Goal verified and achieved in round {round_idx}![/bold green]")
                    session_dossier["status"] = "GOAL_ACHIEVED"
                    session_dossier["summary"] = f"Goal successfully verified and achieved in round {round_idx}."
                    break
                else:
                    console.print(f"[yellow]⚠️ Round {round_idx} needed adjustments. Continuing to round {round_idx + 1}...[/yellow]")
                    # Sanitize judge output to prevent recursive echoing of questions
                    clean_defects = re.sub(r'(?i)(could you|please)\s+provide.*', '', judge_output).strip()
                    if not clean_defects:
                        clean_defects = f"Create the required deliverable for '{goal}' and verify on disk."
                    current_instructions = f"Fix defects identified by Judge:\n{clean_defects}"
                    # C2: Use summarized test output for accumulated context (not raw)
                    accumulated_context = f"Round {round_idx} Tester Report: {test_summary}\nJudge Defects: {clean_defects}"

        except KeyboardInterrupt:
            self.agent.abort_current_task()
            session_dossier["status"] = "INTERRUPTED_KEYBOARD"
            session_dossier["summary"] = "Swarm execution interrupted by user (Ctrl+C)."
            console.print("\n[bold red]Swarm stopped by user (Ctrl+C).[/bold red]")
            return session_dossier

        if session_dossier["status"] != "GOAL_ACHIEVED":
            session_dossier["status"] = "MAX_ROUNDS_REACHED"
            session_dossier["summary"] = f"Swarm reached maximum round budget ({max_rounds}) without full convergence."

        session_dossier["end_time"] = time.time()

        # Final Summary
        console.print(
            Panel(
                f"[bold cyan]Goal:[/bold cyan] {goal}\n"
                f"[bold green]Status:[/bold green] {session_dossier['summary'] or session_dossier['status']}\n"
                f"[dim]Rounds executed: {len(session_dossier['rounds'])} / {max_rounds}[/dim]",
                title="[bold white]✨ Swarm Complete[/bold white]",
                border_style="green" if session_dossier['status'] == "GOAL_ACHIEVED" else "yellow",
            )
        )

        # Archive Swarm Dossier
        dossier_file = SWARM_DOSSIER_DIR / f"{swarm_id}.json"
        dossier_file.write_text(json.dumps(session_dossier, indent=2), encoding="utf-8")
        console.print(f"[dim]Swarm trajectory dossier archived to {dossier_file}[/dim]")

        return session_dossier

    async def run_swarm_async(
        self,
        goal: str,
        max_rounds: int = 5,
        target_verification_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        A3: Asynchronous execution wrapper for SwarmCoordinator.
        Dispatches the CPU/LLM loop to a thread pool without stalling the asyncio event loop.
        """
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(
                pool,
                self.run_swarm,
                goal,
                max_rounds,
                target_verification_command,
            )

    def run_research_swarm(self, topic: str, report_format: str = "comprehensive", target_urls: int = 10) -> Dict[str, Any]:
        """Direct entrypoint to launch the 5-phase research swarm."""
        from genesis.core.research_swarm import ResearchSwarmCoordinator
        coordinator = ResearchSwarmCoordinator(base_agent=self.agent)
        return coordinator.run_research_swarm(topic, report_format=report_format, target_urls=target_urls)



