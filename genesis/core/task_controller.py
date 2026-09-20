"""
Project Genesis: Command-Line Task Controller & Interruption Engine.
Provides non-blocking task cancellation, signal interception, and sequential command queuing.
"""

import sys
import time
from typing import Optional, List, Callable
from rich.console import Console
from rich.markdown import Markdown

from genesis.core.agent import GenesisAgent
from genesis.tools.shell import terminate_active_processes

console = Console()


class TaskController:
    """
    Manages task execution flow, Master interruption signals (Ctrl+C, !HALT),
    and sequential command-queuing for Project Genesis.
    """

    def __init__(self, agent: GenesisAgent):
        self.agent = agent

    def parse_instruction_pipeline(self, raw_input: str) -> List[str]:
        """
        Parse single or chained commands separated by ';;'.
        Example: 'read_file foo.py ;; run_command pytest ;; fix tests'
        """
        if ";;" in raw_input:
            parts = [p.strip() for p in raw_input.split(";;") if p.strip()]
            return parts
        return [raw_input.strip()] if raw_input.strip() else []

    def enqueue_instructions(self, instructions: List[str]) -> int:
        """Enqueue multiple instructions for sequential execution."""
        count = 0
        for inst in instructions:
            self.agent.queue_command(inst)
            count += 1
        return count

    def interrupt_and_halt(self) -> str:
        """Immediately interrupt active execution, killing subprocesses and reverting agent state to IDLE."""
        msg = self.agent.abort_current_task()
        terminate_active_processes()
        return msg

    def execute_with_interrupt_protection(self, instruction: str) -> str:
        """
        Execute an instruction turn with immediate KeyboardInterrupt (Ctrl+C) interception.
        Prevents session death and cleanly restores agent to IDLE state.
        """
        try:
            response = self.agent.run_turn(instruction)
            return response
        except KeyboardInterrupt:
            console.print("\n[bold red]⚡ [MASTER INTERRUPT]: Ctrl+C detected.[/bold red]")
            halt_msg = self.interrupt_and_halt()
            console.print(f"[yellow]{halt_msg}[/yellow]")
            return "[HALTED]: Task execution interrupted by Master."
        except Exception as e:
            return f"Execution Error: {e}"

    def drain_queue(self, on_turn_complete: Optional[Callable[[str, str], None]] = None) -> None:
        """
        Sequentially execute all commands in the command queue until empty or interrupted.
        """
        while True:
            next_cmd = self.agent.pop_next_command()
            if not next_cmd:
                break

            remaining = len(self.agent.get_queued_commands())
            console.print(
                f"\n[bold cyan]► Executing Queued Task:[/bold cyan] [white]{next_cmd}[/white] "
                f"[dim]({remaining} remaining in queue | Press Ctrl+C to halt)[/dim]"
            )

            with console.status("[cyan]Genesis is executing queued task...[/cyan]", spinner="dots"):
                result = self.execute_with_interrupt_protection(next_cmd)

            if on_turn_complete:
                on_turn_complete(next_cmd, result)

            # If user halted, stop draining the queue and ask what to do
            if self.agent.is_aborted():
                remaining_tasks = self.agent.get_queued_commands()
                if remaining_tasks:
                    console.print(
                        f"[yellow]Queue paused. There are still {len(remaining_tasks)} task(s) in queue.[/yellow]"
                    )
                break
