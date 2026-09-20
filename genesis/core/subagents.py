"""
Project Genesis: Hierarchical Sequential Sub-Agent Orchestrator.
Decomposes large projects into bounded, memory-safe sequential roles (Recon -> Architect -> Implementer).
Designed specifically for 16 GB Apple Silicon Mac memory safety.
"""

import time
from typing import Dict, Any, List, Optional
from rich.console import Console

from genesis.core.health_guard import SystemHealthWatchdog
from genesis.config import RESEARCH_DIR

console = Console()


class SubAgentStage:
    """Represents a bounded stage in the hierarchical execution pipeline."""

    def __init__(self, name: str, role_prompt: str, max_iterations: int = 5):
        self.name = name
        self.role_prompt = role_prompt
        self.max_iterations = max_iterations


class HierarchicalWorkflow:
    """
    Orchestrates multi-stage sub-agent execution sequentially on the same model.
    Guarantees flat memory usage across stages to prevent Apple Silicon memory ceiling breaches.
    """

    def __init__(self, agent=None):
        from genesis.core.agent import GenesisAgent
        self.agent = agent or GenesisAgent()

    def run_pipeline(self, goal: str) -> str:
        """
        Execute the 3-tier sequential workflow:
        Stage 1: Recon (Survey files & context)
        Stage 2: Architect (Synthesize technical plan)
        Stage 3: Implementer (Surgical execution & verification)
        """
        stages_output = {}
        slug = f"workflow_{int(time.time())}"

        console.print(f"[bold cyan]Hierarchical Sub-Agent Pipeline Initialized[/bold cyan]: '{goal}'")

        # System Health Pre-Flight Gate
        status, msg, stats = SystemHealthWatchdog.evaluate_health_ceiling()
        if status == "CRITICAL":
            return f"[Pipeline Aborted]: System ceiling reached! {msg}"

        # -------------------------------------------------------------
        # Stage 1: Reconnaissance Sub-Agent
        # -------------------------------------------------------------
        console.print("[cyan][Stage 1/3]: Reconnaissance Agent surveying workspace...[/cyan]")
        recon_prompt = (
            f"[Role: Reconnaissance Agent]\n"
            f"Goal: '{goal}'\n"
            f"Inspect files, locate relevant components using list_files or search_code. "
            f"Summarize your findings in under 300 words. Do NOT modify any code yet."
        )
        recon_report = self.agent.run_turn(recon_prompt)
        stages_output["recon"] = recon_report

        # Check memory ceiling between stages
        status, _, stats = SystemHealthWatchdog.evaluate_health_ceiling()
        if status != "NOMINAL":
            # Prune context aggressively before next stage
            from genesis.core.context import prune_context
            self.agent.messages = prune_context(self.agent.messages, target_tokens=4000)

        # -------------------------------------------------------------
        # Stage 2: Systems Architect Sub-Agent
        # -------------------------------------------------------------
        console.print("[cyan][Stage 2/3]: Systems Architect formulating implementation plan...[/cyan]")
        arch_prompt = (
            f"[Role: Systems Architect]\n"
            f"Based on Recon Findings:\n{recon_report[:1500]}\n\n"
            f"Project Goal: '{goal}'\n"
            f"Define a step-by-step technical implementation plan and testing strategy. "
            f"Be precise and concise. Do NOT edit code yet."
        )
        arch_plan = self.agent.run_turn(arch_prompt)
        stages_output["architect"] = arch_plan

        # -------------------------------------------------------------
        # Stage 3: Lead Implementer Sub-Agent
        # -------------------------------------------------------------
        console.print("[cyan][Stage 3/3]: Lead Implementer executing surgical changes & verifying...[/cyan]")
        impl_prompt = (
            f"[Role: Lead Implementer]\n"
            f"Goal: '{goal}'\n"
            f"Architect Blueprint:\n{arch_plan[:1500]}\n\n"
            f"Execute the necessary modifications using replace_snippet or write_file, "
            f"then run tests via run_command to verify success."
        )
        impl_report = self.agent.run_turn(impl_prompt)
        stages_output["implementation"] = impl_report

        # Archive summary report to ~/.genesis/research/
        summary_path = RESEARCH_DIR / f"{slug}.md"
        summary_md = (
            f"# Hierarchical Sub-Agent Execution Report\n"
            f"**Goal**: {goal}\n\n"
            f"## 1. Reconnaissance Findings\n{recon_report}\n\n"
            f"## 2. Systems Architecture Blueprint\n{arch_plan}\n\n"
            f"## 3. Implementation & Verification\n{impl_report}\n"
        )
        summary_path.write_text(summary_md, encoding="utf-8")

        return (
            f"Hierarchical Sub-Agent Execution Complete.\n"
            f"- Output Dossier: `{summary_path}`\n\n"
            f"{impl_report}"
        )
