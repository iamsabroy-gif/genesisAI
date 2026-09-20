#!/usr/bin/env python3
"""
Project Genesis: Interactive Terminal Interface (CLI).
The sovereign local AI agent with Master Authorization Protocol.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from genesis.core.agent import GenesisAgent
from genesis.config import DEFAULT_MODEL

console = Console()


def show_status(agent: GenesisAgent):
    """Display current system and agent status."""
    from pathlib import Path
    from genesis.config import GENESIS_DIR, TRAJECTORY_DIR
    from genesis.connectors.hub import get_default_hub

    hub = get_default_hub()
    conn_list = hub.list_connectors()
    conn_names = [c['name'] for c in conn_list if c['configured']]
    conn_str = ", ".join(conn_names) if conn_names else "Standard tools (fs, shell, search)"

    from genesis.core.health_guard import SystemHealthWatchdog
    h_status, h_msg, h_stats = SystemHealthWatchdog.evaluate_health_ceiling()
    h_color = "green" if h_status == "NOMINAL" else ("yellow" if h_status == "WARNING" else "red")
    health_str = f"[{h_color}]{h_stats['available_ram_mb']:.0f} MB RAM free[/{h_color}] (Healthy)"

    usage = agent.get_context_usage()

    console.print(
        Panel(
            f"[bold cyan]Model:[/bold cyan] {agent.select_active_model()}\n"
            f"[bold cyan]Memory:[/bold cyan] {health_str}\n"
            f"[bold cyan]Context Window:[/bold cyan] {usage.used_tokens:,} / {usage.total_tokens:,} tokens ({usage.remaining_tokens:,} free • {usage.usage_percentage:.0f}% used)\n"
            f"[bold cyan]Connectors:[/bold cyan] {conn_str}\n"
            f"[bold cyan]Platform:[/bold cyan] Apple Silicon Metal (Hardware Accelerated)",
            title="[bold white]Genesis Status[/bold white]",
            border_style="cyan",
        )
    )


def show_help():
    console.print(
        Panel(
            "[bold cyan]Genesis CLI Usage[/bold cyan]\n\n"
            "  [bold green]genesis[/bold green]                  Start interactive terminal assistant\n"
            "  [bold green]genesis gui[/bold green]              Launch native macOS desktop application\n"
            "  [bold green]genesis skills[/bold green]           Display all sovereign capabilities & skills\n"
            "  [bold green]genesis upload <path>[/bold green]    Ingest files or folders into workspace & vault\n"
            "  [bold green]genesis research <topic>[/bold green] 5-phase research swarm (supports --format)\n"
            "  [bold green]genesis \"<prompt>\"[/bold green]       Run a single prompt or instruction\n"
            "  [bold green]genesis swarm \"<goal>\"[/bold green]   Run autonomous multi-agent swarm until goal is met\n"
            "  [bold green]genesis status[/bold green]           Display agent and memory status\n"
            "  [bold green]genesis models[/bold green]           List, scan, and switch local/server models\n"
            "  [bold green]genesis health[/bold green]           Check Apple Silicon RAM and swap levels\n"
            "  [bold green]genesis kill[/bold green]             Emergency stop: evict models from RAM\n"
            "  [bold green]genesis vault <cmd>[/bold green]       Local semantic search & document vault\n"
            "  [bold green]genesis pdf <file.pdf>[/bold green]        Convert PDF to structured Markdown\n\n"
            "[bold cyan]Interactive Commands (Type / in Terminal):[/bold cyan]\n"
            "  [bold green]/skills[/bold green]                  Show all system capabilities & tools\n"
            "  [bold green]/upload <path>[/bold green]           Ingest file(s) or entire folder\n"
            "  [bold green]/research <topic>[/bold green]       5-phase deep research swarm (supports --format)\n"
            "  [bold green]/research-formats[/bold green]       List available report format options\n"
            "  [bold green]/help[/bold green]                    Show command list\n"
            "  [bold green]/status[/bold green]                  Inspect system and model status\n"
            "  [bold green]/models[/bold green]                  List, switch, or configure local/server models\n"
            "  [bold green]/context[/bold green]                 Display token window usage\n"
            "  [bold green]/swarm <goal>[/bold green]            Launch autonomous multi-agent swarm\n"
            "  [bold green]/clear[/bold green]                   Clear the screen\n"
            "  [bold green]/halt[/bold green] or [bold green]Ctrl+C[/bold green]          Cancel active running task\n"
            "  [bold green]/exit[/bold green]                    Quit and free RAM",
            title="[bold white]Help & Usage[/bold white]",
            border_style="cyan",
        )
    )


def main():
    args = sys.argv[1:]

    # Help flag
    if args and args[0] in ["--help", "-h", "help"]:
        show_help()
        return

    # Native macOS Desktop GUI: genesis gui / genesis --gui / genesis app
    if args and args[0] in ["gui", "--gui", "app", "desktop"]:
        from genesis.gui.app import launch_desktop_gui
        debug_mode = "--debug" in args
        launch_desktop_gui(debug=debug_mode)
        return

    # Emergency Kill Switch: genesis kill / genesis stop / genesis purge
    if args and args[0] in ["kill", "stop", "purge"]:
        from genesis.core.kill_switch import execute_kill_switch
        with console.status("[red]Engaging Sovereign Kill Switch: evicting neural models from Unified RAM...[/red]", spinner="dots"):
            report = execute_kill_switch(terminate_self=False)
        console.print(Markdown(report))
        return

    # Real-time Hardware Health Check: genesis health
    if args and args[0] in ["health", "guard", "sys"]:
        from genesis.core.health_guard import SystemHealthWatchdog
        panel_text = SystemHealthWatchdog.format_status_panel()
        console.print(Panel(panel_text, title="[bold white]Apple Silicon Hardware Watchdog[/bold white]", border_style="cyan"))
        return

    # Local Sovereign Vector Vault commands: genesis vault [index <path> | search <query> | status]
    if args and args[0] == "vault":
        sub_args = args[1:]
        if not sub_args or sub_args[0] in ["status", "stat", "info"]:
            from genesis.tools.vault_rag import vault_status
            console.print(vault_status())
            return
        if sub_args[0] in ["index", "add"] and len(sub_args) > 1:
            target_path = sub_args[1]
            from genesis.tools.vault_rag import vault_index_file
            with console.status(f"[cyan]Indexing '{target_path}' into vector vault...[/cyan]", spinner="dots"):
                res = vault_index_file(target_path)
            console.print(f"[green]{res}[/green]")
            return
        if sub_args[0] in ["search", "query", "find"] and len(sub_args) > 1:
            query = " ".join(sub_args[1:]).strip()
            from genesis.tools.vault_rag import vault_search
            with console.status(f"[cyan]Searching vault for '{query}'...[/cyan]", spinner="dots"):
                res = vault_search(query)
            console.print(Markdown(res))
            return
        console.print("[yellow]Usage: genesis vault [index <path> | search <query> | status][/yellow]")
        return

    # Hierarchical Sub-Agent Pipeline: genesis workflow "<goal>"
    if args and args[0] in ["workflow", "pipeline", "subagents"]:
        goal = " ".join(args[1:]).strip()
        if not goal:
            console.print("[red]Error: Please specify the goal. E.g.: genesis workflow 'Implement health watchdog'[/red]")
            return
        from genesis.core.subagents import HierarchicalWorkflow
        hw = HierarchicalWorkflow()
        output = hw.run_pipeline(goal)
        console.print(Markdown(output))
        return

    # Direct deep research command: genesis research "<topic>"
    if args and args[0] == "research":
        topic = " ".join(args[1:]).strip()
        if not topic:
            console.print("[red]Error: Please specify a topic. E.g.: genesis research 'Apple Silicon M4'[/red]")
            return
        from genesis.tools.web_research import deep_research_report
        with console.status(f"[cyan]Genesis is conducting deep research on '{topic}'...[/cyan]", spinner="dots"):
            report = deep_research_report(topic, max_sources=4)
        console.print(Markdown(report))
        return

    # Direct person due diligence command: genesis person-search "<name>" [--city/--location "<loc>"] [--role/--affiliation "<aff>"] [--id "<id>"]
    if args and args[0] in ["person-search", "person_search", "tutor-search"]:
        sub_args = args[1:]
        if not sub_args or sub_args[0].startswith("-"):
            console.print("[red]Error: Please specify the person's name. E.g.: genesis person-search \"Ramesh Sharma\" --city \"Kolkata\" --role \"Math tutor\"[/red]")
            return
        
        name = sub_args[0]
        location = ""
        affiliation = ""
        identifier = ""

        idx = 1
        while idx < len(sub_args):
            flag = sub_args[idx]
            if flag in ["--city", "--location", "-l"] and idx + 1 < len(sub_args):
                location = sub_args[idx + 1]
                idx += 2
            elif flag in ["--role", "--affiliation", "--subject", "-r", "-a"] and idx + 1 < len(sub_args):
                affiliation = sub_args[idx + 1]
                idx += 2
            elif flag in ["--id", "--identifier", "--phone", "--email"] and idx + 1 < len(sub_args):
                identifier = sub_args[idx + 1]
                idx += 2
            else:
                idx += 1

        from genesis.tools.person_diligence import person_due_diligence
        with console.status(f"[cyan]Genesis is conducting OSINT due diligence on '{name}'...[/cyan]", spinner="dots"):
            dossier = person_due_diligence(name=name, location=location, affiliation=affiliation, identifier=identifier)
        console.print(Markdown(dossier))
        return

    # Direct PDF conversion command: genesis pdf <path/to/doc.pdf> [--output <output.md>] [--analyze "<query>"]
    if args and args[0] in ["pdf", "convert-pdf", "read-pdf"]:
        sub_args = args[1:]
        if not sub_args or sub_args[0].startswith("-"):
            console.print("[red]Error: Please specify the PDF path. E.g.: genesis pdf document.pdf[/red]")
            return

        pdf_path = sub_args[0]
        output_path = ""
        analyze_prompt = ""

        idx = 1
        while idx < len(sub_args):
            flag = sub_args[idx]
            if flag in ["--output", "-o"] and idx + 1 < len(sub_args):
                output_path = sub_args[idx + 1]
                idx += 2
            elif flag in ["--analyze", "-a", "--query", "-q"] and idx + 1 < len(sub_args):
                analyze_prompt = sub_args[idx + 1]
                idx += 2
            else:
                idx += 1

        from genesis.tools.pdf_converter import convert_pdf_to_markdown
        with console.status(f"[cyan]Converting PDF '{pdf_path}' to Markdown...[/cyan]", spinner="dots"):
            conv_status = convert_pdf_to_markdown(pdf_path, output_path=output_path)
        console.print(f"[green]{conv_status}[/green]")

        if analyze_prompt:
            agent = GenesisAgent()
            full_prompt = f"I have converted '{pdf_path}' to Markdown. Please analyze: {analyze_prompt}"
            with console.status(f"[cyan]Genesis is analyzing document...[/cyan]", spinner="dots"):
                analysis = agent.run_turn(full_prompt)
            console.print(Markdown(analysis))
            agent.close(user_feedback=0)
        return

    # Sovereign Skills command: genesis skills
    if args and args[0] in ["skills", "skill", "capabilities"]:
        from genesis.core.skills import format_skills_table
        console.print(format_skills_table())
        return

    # File & Folder Upload command: genesis upload <path>
    if args and args[0] in ["upload", "ingest", "import"]:
        sub_args = args[1:]
        if not sub_args:
            console.print("[red]Error: Please specify the file or folder path to upload. E.g.: genesis upload ./docs[/red]")
            return
        target_path = " ".join(sub_args).strip()
        from genesis.tools.uploader import ingest_upload
        with console.status(f"[cyan]Ingesting '{target_path}' into workspace and vector vault...[/cyan]", spinner="dots"):
            res = ingest_upload(target_path)
        if res.get("status") == "ok":
            console.print(f"[bold green]{res.get('summary')}[/bold green]")
        else:
            console.print(f"[bold red]Upload Error:[/bold red] {res.get('message')}")
        return

    # Models configuration command: genesis models / genesis model <name>
    if args and args[0] in ["models", "model"]:
        from genesis.core.models import ModelManager, PROVIDER_PRESETS
        sub_args = args[1:]
        current_cfg = ModelManager.load_config()

        if not sub_args:
            console.print(Panel(
                f"[bold cyan]Active Model:[/bold cyan] [green]{current_cfg.get('model')}[/green]\n"
                f"[bold cyan]Server URL:[/bold cyan] {current_cfg.get('base_url')} ([dim]{current_cfg.get('provider')}[/dim])",
                title="[bold white]Current Model Configuration[/bold white]",
                border_style="cyan"
            ))
            with console.status("[cyan]Scanning server for available models...[/cyan]", spinner="dots"):
                models_info = ModelManager.fetch_models(current_cfg.get("base_url"), current_cfg.get("api_key"))
            if models_info["status"] == "ok" and models_info["models"]:
                console.print("\n[bold white]Available Models on Server:[/bold white]")
                for m in models_info["models"]:
                    marker = " [bold green]• active[/bold green]" if m == current_cfg.get("model") else ""
                    console.print(f"  • {m}{marker}")
            console.print("\n[bold white]Supported Provider Presets:[/bold white]")
            for p_id, p_info in PROVIDER_PRESETS.items():
                console.print(f"  • [cyan]{p_id:<12}[/cyan] {p_info['name']} ({p_info['base_url']})")
            console.print("\n[dim]Usage:\n  genesis model <name>          Switch model\n  genesis model preset <name>   Switch server provider\n  genesis model server <url>    Set custom server endpoint[/dim]")
            return

        agent = GenesisAgent()
        if sub_args[0] == "preset" and len(sub_args) > 1:
            p_name = sub_args[1].lower()
            if p_name in PROVIDER_PRESETS:
                p_data = PROVIDER_PRESETS[p_name]
                key = p_data.get("default_key", "")
                env_var = p_data.get("env_var")
                import os
                if env_var and os.getenv(env_var):
                    key = os.getenv(env_var)
                res = agent.switch_model(
                    model_name=p_data["default_model"],
                    base_url=p_data["base_url"],
                    api_key=key,
                    provider=p_name,
                )
                console.print(f"[green]✓ Switched to preset '{p_name}':[/green] {res['message']}")
            else:
                console.print(f"[red]Unknown preset '{p_name}'. Available: {', '.join(PROVIDER_PRESETS.keys())}[/red]")
            return

        if sub_args[0] == "server" and len(sub_args) > 1:
            url = sub_args[1]
            key = sub_args[2] if len(sub_args) > 2 else "none"
            res = agent.switch_model(model_name=agent.model_name, base_url=url, api_key=key, provider="custom")
            console.print(f"[green]✓ Server endpoint updated:[/green] {res['message']}")
            return

        target_model = sub_args[0]
        res = agent.switch_model(model_name=target_model)
        console.print(f"[green]✓ Model switched:[/green] {res['message']}")
        return

    agent = GenesisAgent()

    # Status command
    if args and args[0] == "status":
        show_status(agent)
        return

    # Context window command: genesis context [size]
    if args and args[0] in ["context", "token", "tokens"]:
        sub_args = args[1:]
        if sub_args:
            from genesis.core.context import parse_context_size
            new_size = parse_context_size(sub_args[0])
            if new_size:
                old_size = agent.max_context_tokens
                agent.set_max_context(new_size)
                console.print(f"[bold green]✓ Context window scaled:[/bold green] {old_size:,} → [bold cyan]{new_size:,} tokens[/bold cyan]\n")
            else:
                console.print(f"[red]Unknown size '{sub_args[0]}'. E.g.: genesis context 32k[/red]\n")
        usage = agent.get_context_usage()
        console.print(usage.detailed_summary())
        from genesis.core.context import get_recommended_context_size
        rec = get_recommended_context_size()
        console.print(f"\n[dim]Hardware Recommendation: [green]{rec:,} tokens[/green] based on Unified RAM headroom.[/dim]")
        console.print("[dim]To persist across all sessions, set: [cyan]export GENESIS_MAX_CONTEXT=32768[/cyan][/dim]")
        return

    # Research report formats: genesis research-formats
    if args and args[0] in ["research-formats", "research_formats"]:
        from genesis.core.research_swarm import format_report_formats_table
        console.print(format_report_formats_table())
        console.print("\n[dim]Usage: genesis research <topic> [--format comprehensive|executive|technical|market|due_diligence][/dim]")
        return

    # Dedicated Research Swarm command: genesis research <topic> [--format <format>]
    if args and args[0] in ["research", "deep-research"]:
        sub_args = args[1:]
        if not sub_args:
            console.print("[red]Error: Please specify the research topic. E.g.: genesis research 'Solid-state batteries'[/red]")
            from genesis.core.research_swarm import format_report_formats_table
            console.print(format_report_formats_table())
            console.print("\n[dim]Usage: genesis research <topic> [--format FORMAT][/dim]")
            return

        raw_str = " ".join(sub_args).strip()
        import re
        from genesis.core.research_swarm import ResearchSwarmCoordinator
        format_choice = "comprehensive"
        target_urls = 10

        fmt_match = re.search(r'(?:--format|-f)\s+([a-zA-Z_-]+)', raw_str, re.IGNORECASE)
        if fmt_match:
            format_choice = fmt_match.group(1).lower()
            raw_str = re.sub(r'(?:--format|-f)\s+[a-zA-Z_-]+', '', raw_str).strip()

        urls_match = re.search(r'(?:--urls|-u)\s+(\d+)', raw_str, re.IGNORECASE)
        if urls_match:
            target_urls = int(urls_match.group(1))
            raw_str = re.sub(r'(?:--urls|-u)\s+\d+', '', raw_str).strip()

        topic = raw_str.strip()

        coordinator = ResearchSwarmCoordinator(base_agent=agent)
        coordinator.run_research_swarm(topic, report_format=format_choice, target_urls=target_urls)
        agent.close(user_feedback=1)
        return

    # Swarm mode command: genesis swarm "<goal>"
    if args and args[0] == "swarm":
        goal = " ".join(args[1:]).strip()
        if not goal:
            console.print("[red]Usage: genesis swarm \"<goal to achieve>\"[/red]")
            return
        from genesis.core.swarm import SwarmCoordinator
        coordinator = SwarmCoordinator(base_agent=agent)
        coordinator.run_swarm(goal)
        agent.close(user_feedback=1)
        return

    # Single-shot command execution
    if args:
        user_prompt = " ".join(args).strip()
        with console.status(f"[cyan]Genesis is executing: '{user_prompt}'...[/cyan]", spinner="dots"):
            response = agent.run_turn(user_prompt)
        console.print(Markdown(response))
        agent.close(user_feedback=0)
        return

    # Interactive REPL mode (Static Asynchronous User Terminal)
    from genesis.core.terminal import launch_static_terminal
    launch_static_terminal(agent=agent)


if __name__ == "__main__":
    main()
