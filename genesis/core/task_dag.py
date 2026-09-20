"""
Project Genesis: Dynamic Task DAG & Checkpoint Engine.
Orchestrates long-horizon goals as a Directed Acyclic Graph with atomic step-level verification.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from genesis.config import TASKS_DIR


class TaskNode:
    """A discrete, verifiable unit of work within a multi-step project."""

    def __init__(
        self,
        node_id: str,
        title: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        status: str = "PENDING",
    ):
        self.node_id = node_id
        self.title = title
        self.description = description
        self.dependencies = dependencies or []
        self.status = status  # PENDING, RUNNING, COMPLETED, FAILED
        self.result: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        node = cls(
            node_id=data["node_id"],
            title=data["title"],
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "PENDING"),
        )
        node.result = data.get("result")
        node.error = data.get("error")
        return node


class TaskDAG:
    """
    Manages the Directed Acyclic Graph of subtasks for resilient, multi-stage autonomy.
    """

    def __init__(self, goal: str, task_id: Optional[str] = None):
        self.goal = goal
        self.task_id = task_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.nodes: Dict[str, TaskNode] = {}
        self.created_at = time.time()
        self.file_path = TASKS_DIR / f"{self.task_id}.json"

    def add_node(
        self,
        node_id: str,
        title: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
    ) -> TaskNode:
        """Add a step with optional prerequisite dependencies."""
        node = TaskNode(node_id, title, description, dependencies)
        self.nodes[node_id] = node
        self.save()
        return node

    def get_ready_nodes(self) -> List[TaskNode]:
        """Return nodes whose dependencies are all COMPLETED and status is PENDING."""
        ready = []
        for node in self.nodes.values():
            if node.status != "PENDING":
                continue
            deps_met = all(
                self.nodes[d].status == "COMPLETED"
                for d in node.dependencies
                if d in self.nodes
            )
            if deps_met:
                ready.append(node)
        return ready

    def mark_running(self, node_id: str):
        if node_id in self.nodes:
            self.nodes[node_id].status = "RUNNING"
            self.save()

    def mark_completed(self, node_id: str, result: str = ""):
        if node_id in self.nodes:
            self.nodes[node_id].status = "COMPLETED"
            self.nodes[node_id].result = result
            self.save()

    def mark_failed(self, node_id: str, error: str = ""):
        if node_id in self.nodes:
            self.nodes[node_id].status = "FAILED"
            self.nodes[node_id].error = error
            self.save()

    def is_all_completed(self) -> bool:
        return bool(self.nodes) and all(n.status == "COMPLETED" for n in self.nodes.values())

    def has_failed_nodes(self) -> bool:
        return any(n.status == "FAILED" for n in self.nodes.values())

    def render_progress(self) -> str:
        """Format the task graph into an executive status table."""
        lines = [f"# Task DAG: {self.goal} (`{self.task_id}`)\n"]
        for node in self.nodes.values():
            if node.status == "COMPLETED":
                icon = "✅"
            elif node.status == "RUNNING":
                icon = "⏳"
            elif node.status == "FAILED":
                icon = "❌"
            else:
                icon = "⚪"
            lines.append(f"{icon} **[{node.node_id}] {node.title}** ({node.status})")
            if node.description:
                lines.append(f"   *Detail*: {node.description}")
            if node.error:
                lines.append(f"   *Error*: `{node.error}`")
        return "\n".join(lines)

    def save(self):
        """Persist graph state to disk."""
        data = {
            "task_id": self.task_id,
            "goal": self.goal,
            "created_at": self.created_at,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, task_id: str) -> Optional["TaskDAG"]:
        """Load graph state from disk."""
        path = TASKS_DIR / f"{task_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            dag = cls(goal=data["goal"], task_id=data["task_id"])
            dag.created_at = data.get("created_at", time.time())
            for nid, ndata in data.get("nodes", {}).items():
                dag.nodes[nid] = TaskNode.from_dict(ndata)
            return dag
        except Exception:
            return None

    def run_dag(self, agent: Any) -> str:
        """
        A4: Execute the DAG — runs ready nodes in order, checkpointing to disk after each.
        Nodes are executed sequentially to respect the dependency graph.
        Returns a final summary of all completed/failed steps.
        """
        from rich.console import Console
        _console = Console()

        _console.print(f"\n[bold cyan]📋 TaskDAG: {self.goal}[/bold cyan]")
        _console.print(self.render_progress())

        max_iterations = len(self.nodes) * 3  # safety bound
        iteration = 0

        while not self.is_all_completed() and not self.has_failed_nodes():
            iteration += 1
            if iteration > max_iterations:
                break

            ready = self.get_ready_nodes()
            if not ready:
                break  # deadlock: no ready nodes but not done — likely circular deps

            node = ready[0]
            self.mark_running(node.node_id)
            _console.print(f"[yellow]⏳ Executing [{node.node_id}] {node.title}...[/yellow]")

            try:
                prompt = (
                    f"GOAL: {self.goal}\n\n"
                    f"CURRENT STEP [{node.node_id}]: {node.title}\n"
                    f"DESCRIPTION: {node.description}\n\n"
                    f"Execute this step precisely. Report what you did. Do NOT ask questions."
                )
                result = agent.run_turn(prompt)
                self.mark_completed(node.node_id, result=result[:500])
                _console.print(f"[green]✅ [{node.node_id}] done.[/green]")
            except Exception as e:
                self.mark_failed(node.node_id, error=str(e))
                _console.print(f"[red]❌ [{node.node_id}] failed: {e}[/red]")
                break

        return self.render_progress()

    @classmethod
    def plan_from_goal(cls, goal: str, agent: Any) -> "TaskDAG":
        """
        A4: Ask the LLM to decompose a goal into numbered subtasks, build a TaskDAG,
        then run it with checkpointing.
        """
        decompose_prompt = (
            f"Decompose this goal into 3-7 concrete, ordered implementation steps:\n\n"
            f"GOAL: {goal}\n\n"
            f"Output ONLY a numbered list. Each item: <step_id>. <step_title>: <short_description>\n"
            f"Example: 1. scaffold: Create the directory structure and __init__.py files\n"
            f"Do NOT include explanations or headers."
        )
        plan_text = agent.run_turn(decompose_prompt)

        dag = cls(goal=goal)
        prev_id = None

        for line in plan_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Parse "N. title: description" or "N. title"
            import re
            match = re.match(r"(\d+)\.\s*([^:]+?)(?::\s*(.+))?$", line)
            if match:
                step_num, title, desc = match.group(1), match.group(2).strip(), (match.group(3) or "").strip()
                node_id = f"step_{step_num}"
                deps = [f"step_{int(step_num)-1}"] if prev_id else []
                dag.add_node(node_id=node_id, title=title, description=desc, dependencies=deps)
                prev_id = node_id

        return dag
