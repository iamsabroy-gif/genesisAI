"""
Project Genesis: Static Asynchronous User Terminal & Interactive REPL.
Powered by prompt_toolkit and asyncio for a static, non-blocking input prompt,
live background model execution, static context window toolbar, and real-time command queuing.
"""

import sys
import os
import re
import time
import asyncio
from pathlib import Path
from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel

from prompt_toolkit.completion import Completer, Completion
from genesis.core.agent import GenesisAgent
from genesis.core.task_controller import TaskController
from genesis.config import GENESIS_HOME

console = Console()
HISTORY_FILE = GENESIS_HOME / "terminal_history.txt"


class SlashCommandCompleter(Completer):
    """Provides interactive autocomplete candidates with descriptions whenever the user types '/'."""
    COMMANDS = [
        ("/skills", "Show all sovereign capabilities, modules, and agent skills"),
        ("/upload", "Ingest and index files or entire folders into workspace & vault"),
        ("/help", "Display full help guide and usage instructions"),
        ("/status", "Inspect active model, RAM headroom, and system health"),
        ("/models", "List, switch, or configure local/server models"),
        ("/context", "Display or scale token window (e.g. /context 32k)"),
        ("/research", "Launch 5-phase research swarm (supports --format option)"),
        ("/research-formats", "List available report formats (academic, executive, technical, market, diligence)"),
        ("/swarm", "Launch autonomous 4-worker swarm until goal is met"),
        ("/pipeline", "Run 3-phase Recon → Architect → Implement workflow"),
        ("/plan", "Decompose goal into TaskDAG dependency graph with checkpoints"),
        ("/train", "Harvest session trajectories and trigger local MLX LoRA training"),
        ("/queue", "Inspect or clear the asynchronous task queue"),
        ("/clear", "Clear the terminal screen"),
        ("/halt", "Stop current running task immediately (Ctrl+C)"),
        ("/exit", "Quit Genesis, archive session trajectory, and free RAM"),
    ]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            word = text
            for cmd, desc in self.COMMANDS:
                if cmd.lower().startswith(word.lower()):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=desc,
                    )


class GenesisTerminal:
    """
    Static user terminal providing a persistent prompt and context toolbar
    while Genesis reasons, executes tools, or runs multi-agent swarms asynchronously in the background.
    """

    def __init__(self, agent: Optional[GenesisAgent] = None):
        self.agent = agent or GenesisAgent()
        self.controller = TaskController(self.agent)
        self.session = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            completer=SlashCommandCompleter(),
        )
        self.current_task: Optional[str] = None
        self.current_task_future: Optional[asyncio.Future] = None
        self.is_shutting_down = False
        self._task_queue = asyncio.Queue()

    def get_bottom_toolbar(self) -> HTML:
        """
        Dynamically renders a clean, compact context window and status bar
        pinned directly above the user's input line. Fits on standard screens without wrapping.
        """
        try:
            usage = self.agent.get_context_usage()
            pct = usage.usage_percentage
            queued_count = len(self.agent.get_queued_commands()) + self._task_queue.qsize()

            if self.current_task:
                short_task = self.current_task[:18] + ("..." if len(self.current_task) > 18 else "")
                state_desc = f"<b><ansiyellow>BUSY ({short_task})</ansiyellow></b>"
            else:
                state_desc = "<b><ansigreen>IDLE</ansigreen></b>"

            color_tag = "ansigreen" if pct < 60 else ("ansiyellow" if pct < 75 else "ansired")

            # Sleek format that guarantees no multi-line terminal wrapping
            return HTML(
                f" Context: <{color_tag}>{usage.used_tokens:,}</{color_tag}> / {usage.total_tokens:,} tokens "
                f"({pct:.0f}% used) │ State: {state_desc} │ Queue: <b>{queued_count}</b> │ "
                f"Model: <b>{self.agent.model_name.split(':')[0]}</b> "
            )
        except Exception:
            return HTML(" Context: 16,384 tokens │ State: IDLE │ Queue: 0 │ Model: Genesis ")

    async def _execute_task_worker(self):
        """
        Background worker that continuously consumes tasks from the queue
        without blocking the user's input prompt.
        """
        while not self.is_shutting_down:
            task_cmd = None
            try:
                task_cmd = await self._task_queue.get()
                self.current_task = task_cmd
                self.agent.abort_requested.clear()

                console.print(f"\n[bold cyan]⚡ Running:[/bold cyan] [white]{task_cmd}[/white] [dim](Prompt is active for new input)[/dim]")

                # Handle swarm goals or regular tasks
                if task_cmd.strip().upper().startswith("!SWARM") or task_cmd.strip().lower().startswith("/swarm"):
                    if task_cmd.strip().lower().startswith("/swarm"):
                        goal = task_cmd[len("/swarm"):].strip()
                    else:
                        goal = task_cmd[len("!SWARM"):].strip()
                    from genesis.core.swarm import SwarmCoordinator
                    coordinator = SwarmCoordinator(base_agent=self.agent)
                    # A3: Direct async invocation via run_swarm_async
                    self.current_task_future = asyncio.create_task(coordinator.run_swarm_async(goal))
                    res = await self.current_task_future
                    console.print(f"\n[bold green]✨ Swarm Complete:[/bold green] {res.get('summary') or res.get('status')}")

                # Dedicated /research-formats command
                elif task_cmd.strip().lower() in ["/research-formats", "/research_formats"]:
                    from genesis.core.research_swarm import format_report_formats_table
                    console.print(format_report_formats_table())
                    console.print("\n[dim]Usage: /research <topic> [--format comprehensive|executive|technical|market|due_diligence][/dim]")

                # Dedicated /research command: 5-Phase Process-Oriented Research Swarm
                elif task_cmd.strip().lower().startswith("/research"):
                    raw_args = task_cmd[len("/research"):].strip()
                    if not raw_args:
                        console.print("[yellow]/research requires a topic. Example: /research Solid-state battery commercialization 2026 --urls 15 --context ./paper.pdf[/yellow]")
                        from genesis.core.research_swarm import format_report_formats_table
                        console.print(format_report_formats_table())
                        console.print("\n[dim]Usage: /research <topic> [--format <fmt>] [--urls 10-20] [--context URL/FILE/FOLDER] [--file PATH] [--folder PATH] [--seed URL][/dim]")
                    else:
                        from genesis.core.research_swarm import ResearchSwarmCoordinator, extract_research_cli_flags
                        topic, format_choice, target_urls, context_items = extract_research_cli_flags(raw_args)

                        coord = ResearchSwarmCoordinator(base_agent=self.agent)
                        loop = asyncio.get_running_loop()
                        self.current_task_future = loop.run_in_executor(
                            None, coord.run_research_swarm, topic, format_choice, target_urls, None, context_items
                        )
                        dossier = await self.current_task_future
                        console.print(f"\n[bold green]🔬 Research Swarm Complete:[/bold green] {dossier.get('summary')}")

                # A6: /pipeline — 3-phase HierarchicalWorkflow (faster alternative to swarm)
                elif task_cmd.strip().lower().startswith("/pipeline"):
                    goal = task_cmd[len("/pipeline"):].strip()
                    if not goal:
                        console.print("[yellow]/pipeline requires a goal. Example: /pipeline add unit tests to auth.py[/yellow]")
                    else:
                        from genesis.core.subagents import HierarchicalWorkflow
                        workflow = HierarchicalWorkflow(agent=self.agent)
                        loop = asyncio.get_running_loop()
                        self.current_task_future = loop.run_in_executor(None, workflow.run_pipeline, goal)
                        res = await self.current_task_future
                        console.print(f"\n[bold green]✅ Pipeline Complete:[/bold green] {res}")

                # A4: /plan — TaskDAG goal decomposition + step-by-step execution
                elif task_cmd.strip().lower().startswith("/plan"):
                    goal = task_cmd[len("/plan"):].strip()
                    if not goal:
                        console.print("[yellow]/plan requires a goal. Example: /plan add OAuth2 login to the API[/yellow]")
                    else:
                        from genesis.core.task_dag import TaskDAG
                        loop = asyncio.get_running_loop()
                        def _run_plan():
                            dag = TaskDAG.plan_from_goal(goal, self.agent)
                            return dag.run_dag(self.agent)
                        self.current_task_future = loop.run_in_executor(None, _run_plan)
                        res = await self.current_task_future
                        console.print(f"\n[bold green]📋 Plan Complete:[/bold green]\n{res}")

                # M4: /train — trigger autonomous dataset curation and MLX LoRA training flywheel
                elif task_cmd.strip().lower().startswith("/train"):
                    console.print("[cyan]⚙️ [M4 Flywheel]: Initiating autonomous curation & MLX training...[/cyan]")
                    loop = asyncio.get_running_loop()
                    def _run_training_flywheel():
                        from curator import curate_trajectories
                        stats = curate_trajectories()
                        if stats.get("sft", 0) == 0:
                            return f"Curation completed: 0 gold trajectories found. Interact with Genesis more to build training data."
                        from train_lora import train_adapter
                        ok = train_adapter()
                        if ok:
                            return f"LoRA training succeeded! Curated {stats.get('sft')} gold trajectories. Adapter saved to ~/.genesis/adapters/."
                        return f"Curated {stats.get('sft')} trajectories, but MLX training requires 'mlx' and 'mlx-lm' packages."

                    self.current_task_future = loop.run_in_executor(None, _run_training_flywheel)
                    res = await self.current_task_future
                    console.print(f"\n[bold green]🎓 Training Flywheel Result:[/bold green] {res}")

                # /upload — Ingest files or folders into workspace & vector vault
                elif task_cmd.strip().lower().startswith("/upload"):
                    target_arg = task_cmd.strip()[len("/upload"):].strip()
                    from genesis.tools.uploader import ingest_upload
                    loop = asyncio.get_running_loop()
                    self.current_task_future = loop.run_in_executor(None, ingest_upload, target_arg)
                    res = await self.current_task_future
                    if res.get("status") == "ok":
                        console.print(f"\n[bold green]{res.get('summary')}[/bold green]")
                    else:
                        console.print(f"\n[bold red]Upload Error:[/bold red] {res.get('message')}")

                else:
                    loop = asyncio.get_running_loop()
                    self.current_task_future = loop.run_in_executor(None, self.agent.run_turn, task_cmd)
                    response = await self.current_task_future

                    console.print()
                    console.print(response, style="cyan", markup=False, highlight=False)
                    console.print()

            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"\n[red]Task execution error: {e}[/red]")
            finally:
                self.current_task = None
                self.current_task_future = None
                if task_cmd is not None:
                    try:
                        self._task_queue.task_done()
                    except ValueError:
                        pass

    def halt_active_execution(self) -> str:
        """Immediately abort active background task and clear active child subprocesses."""
        msg = self.controller.interrupt_and_halt()
        if self.current_task_future and not self.current_task_future.done():
            self.current_task_future.cancel()
        self.current_task = None
        return msg

    async def run_interactive_terminal(self):
        """
        Runs the static terminal REPL loop.
        The prompt stays permanently visible and active while the background worker processes tasks.
        """
        active_model = self.agent.select_active_model()
        init_usage = self.agent.get_context_usage()

        console.print(
            Panel(
                f"[bold cyan]✨ Genesis AI[/bold cyan] [dim]•[/dim] [green]{active_model.split(':')[0]}[/green] [dim]• Apple Silicon Metal[/dim]\n\n"
                f"Type your prompt, or use commands: [bold cyan]/help[/bold cyan], [bold cyan]/status[/bold cyan], [bold cyan]/context[/bold cyan], [bold cyan]/clear[/bold cyan], [bold cyan]/exit[/bold cyan]\n"
                f"[dim]• Non-blocking prompt: Type or queue tasks anytime while Genesis works.\n"
                f"• Press [bold]Ctrl+C[/bold] or type [bold]/halt[/bold] anytime to stop an active task.[/dim]",
                title="[bold white]Ready[/bold white]",
                border_style="cyan",
            )
        )

        # Launch background execution worker
        worker_task = asyncio.create_task(self._execute_task_worker())

        try:
            with patch_stdout():
                while True:
                    try:
                        user_input = await self.session.prompt_async(
                            "You > ",
                            bottom_toolbar=self.get_bottom_toolbar,
                        )
                        user_input = user_input.strip()
                    except (KeyboardInterrupt, EOFError):
                        # If a task is running, Ctrl+C halts the active task without exiting the session
                        if self.current_task:
                            halt_report = self.halt_active_execution()
                            console.print(f"\n[bold yellow]{halt_report}[/bold yellow]")
                            continue
                        else:
                            console.print("\n[yellow]Exit requested (Ctrl+C). Terminating session...[/yellow]")
                            break

                    if not user_input:
                        continue

                    # Clear screen command
                    if user_input.lower() in ["/clear", "clear"]:
                        console.clear()
                        continue

                    # Exit command
                    if user_input.lower() in ["/exit", "/quit", "exit", "quit", "q"]:
                        if self.current_task:
                            self.halt_active_execution()
                        archive_path = self.agent.close(user_feedback=0, unload_model=True)
                        console.print(f"[bold cyan]Session archived:[/bold cyan] {archive_path}")
                        console.print("[green]Memory freed. Goodbye![/green]")
                        break

                    # Skills catalog command: /skills or typing '/' alone
                    if user_input.lower() in ["/skills", "/skill", "/"]:
                        from genesis.core.skills import format_skills_table
                        console.print()
                        console.print(format_skills_table())
                        console.print()
                        continue

                    # Upload file or folder command: /upload <path>
                    if user_input.lower().startswith("/upload"):
                        target_arg = user_input[len("/upload"):].strip()
                        if not target_arg:
                            try:
                                target_arg = await self.session.prompt_async("Path to file or folder to upload: ")
                                target_arg = target_arg.strip()
                            except (KeyboardInterrupt, EOFError):
                                continue

                        if not target_arg:
                            console.print("[yellow]Upload cancelled: No path provided.[/yellow]")
                            continue

                        from genesis.tools.uploader import ingest_upload
                        console.print(f"[cyan]Ingesting '{target_arg}' into workspace and vector vault...[/cyan]")
                        res = ingest_upload(target_arg)
                        if res.get("status") == "ok":
                            console.print(f"\n[bold green]{res.get('summary')}[/bold green]\n")
                        else:
                            console.print(f"\n[bold red]Upload Error:[/bold red] {res.get('message')}\n")
                        continue

                    # Help command
                    if user_input.lower() in ["/help", "help", "/?"]:
                        console.print(
                            Panel(
                                "[bold cyan]Available Commands (Type / for live autocomplete):[/bold cyan]\n\n"
                                "  [bold green]/skills[/bold green]                 Show all sovereign system capabilities & skills\n"
                                "  [bold green]/upload <path>[/bold green]          Ingest file(s) or entire folder into workspace & vault\n"
                                "  [bold green]/help[/bold green]                   Show this help guide\n"
                                "  [bold green]/status[/bold green]                 Show model, memory, and system health\n"
                                "  [bold green]/models[/bold green] or [bold green]/model[/bold green]          List, switch, or configure local/server models\n"
                                "  [bold green]/context[/bold green]                Show detailed token usage breakdown\n"
                                "  [bold green]/clear[/bold green]                  Clear terminal screen\n"
                                "  [bold green]/research <topic>[/bold green]        Launch 5-phase research swarm for publication-grade report\n"
                                "  [bold green]/swarm <goal>[/bold green]           Launch autonomous 4-worker swarm (max thoroughness)\n"
                                "  [bold green]/pipeline <goal>[/bold green]        Run 3-phase Recon→Architect→Implement workflow (faster)\n"
                                "  [bold green]/plan <goal>[/bold green]            Decompose goal into steps via TaskDAG + execute with checkpoints\n"
                                "  [bold green]/train[/bold green]                  Harvest session trajectories and trigger local MLX LoRA training\n"
                                "  [bold green]/queue[/bold green]                  List pending queued tasks\n"
                                "  [bold green]/queue clear[/bold green]            Clear all pending tasks in queue\n"
                                "  [bold green]/halt[/bold green] or [bold green]Ctrl+C[/bold green]         Stop current running task immediately\n"
                                "  [bold green]/exit[/bold green]                   Exit Genesis and free RAM\n\n"
                                "[dim]Tip: You can chain multiple commands using ';;' (e.g. read code ;; run tests)[/dim]",
                                title="[bold white]Help & Commands[/bold white]",
                                border_style="cyan",
                            )
                        )
                        continue

                    # Halt / Interrupt command
                    if user_input.upper() in ["/HALT", "/STOP", "!HALT", "HALT", "!KILL"]:
                        halt_report = self.halt_active_execution()
                        console.print(f"[bold red]{halt_report}[/bold red]")
                        continue

                    # Context Inspection & Scaling command: /context [size]
                    if user_input.lower().startswith("/context") or user_input.upper() == "!CONTEXT":
                        arg = user_input[len("/context"):].strip() if user_input.lower().startswith("/context") else ""
                        if arg:
                            from genesis.core.context import parse_context_size
                            new_size = parse_context_size(arg)
                            if new_size:
                                old_size = self.agent.max_context_tokens
                                self.agent.set_max_context(new_size)
                                console.print(
                                    f"[bold green]✓ Context window scaled:[/bold green] "
                                    f"{old_size:,} → [bold cyan]{new_size:,}[/bold cyan] tokens "
                                    f"(Prune trigger: {int(new_size * 0.75):,})\n"
                                )
                            else:
                                console.print(f"[red]Invalid context size '{arg}'. Try e.g. /context 32k, /context 64k, or /context 32768[/red]")
                        usage = self.agent.get_context_usage()
                        console.print(usage.detailed_summary())
                        from genesis.core.context import get_recommended_context_size
                        rec = get_recommended_context_size()
                        console.print(f"\n[dim]Hardware Recommendation: [green]{rec:,} tokens[/green] based on current Unified RAM headroom.[/dim]")
                        console.print("[dim]To scale context, type: [cyan]/context 32k[/cyan] or set [cyan]export GENESIS_MAX_CONTEXT=32768[/cyan][/dim]\n")
                        continue

                    # Status Inspection command
                    if user_input.upper() in ["/STATUS", "!STATUS"]:
                        status_out, _ = self.agent.master_auth.execute_master_signal("!STATUS", {
                            "context_usage": self.agent.get_context_usage(),
                            "estimated_tokens": self.agent.get_context_usage().used_tokens,
                            "history_len": len(self.agent.messages),
                            "model": self.agent.model_name,
                            "agent": self.agent,
                        })
                        console.print(status_out)
                        continue

                    # Model switching and configuration
                    if user_input.lower().startswith("/model") or user_input.lower().startswith("/models"):
                        from genesis.core.models import ModelManager, PROVIDER_PRESETS
                        parts = user_input.strip().split()
                        current_cfg = ModelManager.load_config()

                        if len(parts) == 1:
                            console.print(f"\n[bold cyan]Active Model:[/bold cyan] [green]{self.agent.model_name}[/green]")
                            console.print(f"[bold cyan]Server Endpoint:[/bold cyan] {current_cfg.get('base_url')} ([dim]{current_cfg.get('provider', 'custom')}[/dim])")
                            models_info = ModelManager.fetch_models(current_cfg.get("base_url"), current_cfg.get("api_key"))
                            if models_info["status"] == "ok" and models_info["models"]:
                                console.print("\n[bold white]Available Models on Active Endpoint:[/bold white]")
                                for m in models_info["models"]:
                                    marker = " [bold green]• active[/bold green]" if m == self.agent.model_name else ""
                                    console.print(f"  - {m}{marker}")
                            else:
                                console.print(f"\n[dim](Could not auto-list models from active server: {models_info.get('message', 'empty')})[/dim]")

                            console.print("\n[bold white]Provider Presets:[/bold white]")
                            for p_id, p_data in PROVIDER_PRESETS.items():
                                console.print(f"  - [cyan]{p_id:<12}[/cyan] {p_data['name']} ({p_data['base_url']})")
                            console.print("\n[dim]Usage:\n  /model <model_name>          Switch model\n  /model preset <preset_name>  Switch server provider (e.g. /model preset lmstudio)\n  /model server <url> [key]    Connect custom server endpoint[/dim]")
                            continue

                        subcmd = parts[1].lower()
                        if subcmd == "preset" and len(parts) > 2:
                            target_preset = parts[2].lower()
                            if target_preset in PROVIDER_PRESETS:
                                p_data = PROVIDER_PRESETS[target_preset]
                                key = p_data.get("default_key", "")
                                env_var = p_data.get("env_var")
                                if env_var and os.getenv(env_var):
                                    key = os.getenv(env_var)
                                res = self.agent.switch_model(
                                    model_name=p_data["default_model"],
                                    base_url=p_data["base_url"],
                                    api_key=key,
                                    provider=target_preset,
                                )
                                console.print(f"[bold green]✓ Switched to preset '{target_preset}':[/bold green] {res['message']}")
                            else:
                                console.print(f"[red]Unknown preset '{target_preset}'. Choose from: {', '.join(PROVIDER_PRESETS.keys())}[/red]")
                            continue

                        elif subcmd == "server" and len(parts) > 2:
                            new_url = parts[2]
                            new_key = parts[3] if len(parts) > 3 else "none"
                            res = self.agent.switch_model(
                                model_name=self.agent.model_name,
                                base_url=new_url,
                                api_key=new_key,
                                provider="custom",
                            )
                            console.print(f"[bold green]✓ Updated server endpoint:[/bold green] {res['message']}")
                            continue

                        else:
                            target_model = parts[1]
                            res = self.agent.switch_model(model_name=target_model)
                            console.print(f"[bold green]✓ Model switched:[/bold green] {res['message']}")
                            continue

                    # Queue Inspection / Manipulation
                    if user_input.upper() in ["/QUEUE", "/QUEUE LIST", "!QUEUE LIST", "!QUEUE"]:
                        q_items = self.agent.get_queued_commands()
                        if not q_items and self._task_queue.empty():
                            console.print("[dim]Queue is empty.[/dim]")
                        else:
                            console.print(f"[cyan]Pending Tasks ({len(q_items)}):[/cyan]")
                            for i, cmd in enumerate(q_items):
                                console.print(f"  [{i+1}] {cmd}")
                        continue

                    if user_input.upper() in ["/QUEUE CLEAR", "!QUEUE CLEAR"]:
                        self.agent.clear_command_queue()
                        # Drain asyncio queue
                        while not self._task_queue.empty():
                            try:
                                self._task_queue.get_nowait()
                                self._task_queue.task_done()
                            except Exception:
                                break
                        console.print("[yellow]Queue cleared.[/yellow]")
                        continue

                    # Parse chained command pipeline (;; delimiter)
                    pipeline = self.controller.parse_instruction_pipeline(user_input)

                    for cmd in pipeline:
                        # If a task is currently executing, enqueue and notify the user
                        if self.current_task:
                            self.agent.queue_command(cmd)
                            await self._task_queue.put(cmd)
                            console.print(
                                f"[bold cyan]⚡ Queued task #{self._task_queue.qsize()}:[/bold cyan] "
                                f"[white]'{cmd}'[/white] [dim](will run after current task)[/dim]"
                            )
                        else:
                            # Enqueue directly to be picked up immediately by worker
                            await self._task_queue.put(cmd)

        finally:
            self.is_shutting_down = True
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


def launch_static_terminal(agent: Optional[GenesisAgent] = None):
    """Entrypoint to launch the asynchronous static terminal."""
    terminal = GenesisTerminal(agent=agent)
    asyncio.run(terminal.run_interactive_terminal())
