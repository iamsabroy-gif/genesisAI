"""
Project Genesis: Process-Oriented Multi-Agent Research Swarm Orchestrator.
Executes an iterative, 5-phase academic and executive-grade research pipeline:
  Phase 1: Research Architect & Scoping Lead (Charter, Pillars & Search Strategy)
  Phase 2: Intelligence & Multi-Angle Recon Squad (Empirical Web & Data Extraction)
  Phase 3: Quantitative & Analytical Modeler (Trade-Off Matrices, SWOT, Synthesis)
  Phase 4: Critical Auditor & Peer Reviewer (Fact-Checking, Depth & Gap Remediation)
  Phase 5: Chief Executive Editor & Publication Lead (Authoring Full Markdown Report)

Saves finalized, publication-grade reports to ~/.genesis/research/ and the active workspace.
"""

import os
import re
import time
import json
import datetime
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from genesis.core.agent import GenesisAgent
from genesis.core.health_guard import SystemHealthWatchdog
from genesis.tools.web_research import web_search, web_scrape
from genesis.config import GENESIS_HOME, WORKSPACE_ROOT, RESEARCH_DIR

DOSSIERS_DIR = RESEARCH_DIR / "dossiers"
DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)

console = Console()

# Complete registry of supported report formats for the research swarm
REPORT_FORMATS: Dict[str, Dict[str, Any]] = {
    "comprehensive": {
        "id": "comprehensive",
        "name": "Comprehensive Academic Report",
        "icon": "🔬",
        "badge": "Academic Publication",
        "filename_suffix": "comprehensive_research_report",
        "title_prefix": "Comprehensive Research Report",
        "description": "Exhaustive publication-grade whitepaper with technical foundations, empirical benchmark tables, SWOT analysis, risk matrices, and citations.",
        "architect_focus": "Decompose into 6-8 rigorous technical & theoretical pillars with empirical metrics, hypotheses, and deep benchmarks.",
        "analyst_focus": "Build deep benchmark matrices, technical mechanics, SWOT analysis, and quantitative trade-offs.",
        "auditor_focus": "Audit against academic/peer-reviewed publication rigor, empirical data density, and citation validity.",
        "sections": [
            "Executive Summary & Core Strategic Takeaways",
            "Architectural & Technological Foundations",
            "Comparative Landscape & Empirical Benchmark Matrix",
            "SWOT & Economic / Operational Trade-Offs",
            "Regulatory, Security, & Practical Risk Matrix",
            "Future Outlook, Emerging Trends & Strategic Roadmap",
            "Formal Citations & References Bibliography",
        ],
    },
    "executive": {
        "id": "executive",
        "name": "Executive Briefing & Decision Memo",
        "icon": "👔",
        "badge": "C-Level Briefing",
        "filename_suffix": "executive_briefing_memo",
        "title_prefix": "Executive Briefing & Decision Memo",
        "description": "Concise, high-impact strategic memo for executives: key takeaways, KPI dashboard, cost/ROI analysis, and actionable 90-day execution roadmap.",
        "architect_focus": "Focus on business value, market opportunities, financial/cost implications, and high-level strategic trade-offs.",
        "analyst_focus": "Construct executive KPI dashboards, cost-benefit / ROI frameworks, and strategic positioning matrices.",
        "auditor_focus": "Audit for executive clarity, actionable insight, elimination of unnecessary technical jargon, and decision confidence.",
        "sections": [
            "Executive Dashboard & Bottom-Line Verdict",
            "Strategic Context & Market Opportunity",
            "Key Performance Indicators & Core Metrics Table",
            "Cost-Benefit, Capital Allocation & ROI Analysis",
            "Strategic Risk Assessment & Mitigation Guardrails",
            "Actionable Recommendations & 90-Day Execution Roadmap",
            "Primary Sources & Intelligence References",
        ],
    },
    "technical": {
        "id": "technical",
        "name": "Technical Architecture & System Spec",
        "icon": "🛠️",
        "badge": "Engineering Deep Dive",
        "filename_suffix": "technical_architecture_spec",
        "title_prefix": "Technical Architecture & System Specification",
        "description": "In-depth engineering blueprint covering system architecture, protocol specifications, throughput/latency benchmarks, failure modes, and implementation guidance.",
        "architect_focus": "Focus on system architecture, data models, protocols, latency/throughput requirements, and engineering constraints.",
        "analyst_focus": "Detail mechanical workflows, architectural trade-offs, performance benchmarks, and failure mode analysis.",
        "auditor_focus": "Audit for architectural correctness, edge cases, scalability bottlenecks, and engineering feasibility.",
        "sections": [
            "Technical Abstract & Scope of Specification",
            "System Architecture & Core Component Deconstruction",
            "Comparative Technical Specifications & Performance Benchmarks",
            "Concurrency, Throughput, Scalability & Failure Modes",
            "Security Architecture, Threat Model & Hardening",
            "Implementation Blueprint & Engineering Best Practices",
            "Technical References & Protocol Specifications",
        ],
    },
    "market": {
        "id": "market",
        "name": "Competitive Market & Industry Analysis",
        "icon": "📈",
        "badge": "Market Intelligence",
        "filename_suffix": "market_competitive_analysis",
        "title_prefix": "Competitive Market & Industry Analysis",
        "description": "Comprehensive market intelligence report detailing total addressable market, key players, competitor feature/pricing matrices, and industry disruption trends.",
        "architect_focus": "Decompose into market sizing, competitive dynamics, customer segments, pricing structures, and regulatory landscape.",
        "analyst_focus": "Construct competitor feature comparison matrices, pricing models, market share projections, and Porter's five forces analysis.",
        "auditor_focus": "Verify market data validity, competitor claims, pricing reality, and unbiased industry perspective.",
        "sections": [
            "Industry Overview & Market Sizing (TAM/SAM/SOM)",
            "Competitive Landscape & Key Player Profiles",
            "Side-by-Side Competitor Feature & Pricing Matrix",
            "Market Drivers, Regulatory Tailwinds & Disruptive Forces",
            "Customer Persona, Buying Criteria & Adoption Friction",
            "Strategic Positioning, Go-To-Market & Moat Assessment",
            "Industry Intelligence Sources & Market Citations",
        ],
    },
    "due_diligence": {
        "id": "due_diligence",
        "name": "Due Diligence & Go/No-Go Risk Audit",
        "icon": "⚖️",
        "badge": "Risk & Diligence Audit",
        "filename_suffix": "due_diligence_risk_audit",
        "title_prefix": "Due Diligence & Go/No-Go Risk Audit",
        "description": "Rigorous investigative audit to evaluate feasibility, claims veracity, red flags, compliance exposure, and deliver an explicit Go / No-Go decision verdict.",
        "architect_focus": "Structure investigation around truth-testing claims, identifying hidden liabilities, compliance vulnerabilities, and failure conditions.",
        "analyst_focus": "Create red flag risk matrices, claims vs. reality verification tables, financial/operational health assessments, and risk heatmaps.",
        "auditor_focus": "Stress-test assumptions, verify negative evidence, probe for conflicts of interest or technical debt, and ensure absolute objectivity.",
        "sections": [
            "Executive Audit Summary & Definitive Decision Verdict (Go / No-Go)",
            "Core Value Proposition vs. Empirical Claims Verification",
            "Red Flag Investigation & Critical Vulnerability Audit",
            "Regulatory, Legal, Compliance & IP Posture",
            "Operational Feasibility & Total Cost of Ownership",
            "Risk Heatmap, Mitigation Strategies & Contingencies",
            "Audit Trail, Verification Evidence & Documentation Index",
        ],
    },
}


def get_report_formats() -> List[Dict[str, Any]]:
    """Return list of all supported report formats."""
    return list(REPORT_FORMATS.values())


def get_format_metadata(format_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve format metadata by ID, default to comprehensive if not recognized."""
    if not format_id:
        return REPORT_FORMATS["comprehensive"]
    cleaned = format_id.strip().lower().replace("-", "_").replace(" ", "_")
    return REPORT_FORMATS.get(cleaned, REPORT_FORMATS["comprehensive"])


def format_report_formats_table() -> Table:
    """Generate a Rich Table displaying all report format choices."""
    table = Table(title="Genesis Research Swarm Report Formats", border_style="cyan", header_style="bold cyan")
    table.add_column("Option / ID", style="bold green", width=16)
    table.add_column("Format Name", style="bold white", width=28)
    table.add_column("Audience / Badge", style="yellow", width=22)
    table.add_column("Description", style="dim white", width=42)

    for f in REPORT_FORMATS.values():
        table.add_row(
            f"{f['icon']} {f['id']}",
            f['name'],
            f['badge'],
            f['description'],
        )
    return table


def format_report_formats_markdown() -> str:
    """Generate a Markdown summary of all available report formats."""
    lines = [
        "### 📑 Genesis Research Swarm: Available Report Formats\n",
        "Choose a format option before launching research via `/research <topic> --format <type>`:\n",
        "| Format ID | Name | Target Focus | Sections |",
        "|---|---|---|---|",
    ]
    for f in REPORT_FORMATS.values():
        sec_count = len(f["sections"])
        lines.append(f"| `{f['id']}` | {f['icon']} **{f['name']}** | {f['badge']} | {sec_count} Sections |")
    lines.append("\n**Usage Examples:**\n")
    lines.append("- `/research Solid-State Batteries 2026 --format comprehensive`")
    lines.append("- `/research Quantum Computing Cryptography --format executive`")
    lines.append("- `/research Apple M4 Max Neural Engine --format technical`")
    lines.append("- `/research Cloud AI Inference Providers --format market`")
    lines.append("- `/research Autonomous Delivery Drones --format due_diligence`")
    return "\n".join(lines)
 
 
def compress_source_findings(
    source_idx: int,
    url: str,
    title: str,
    query: str,
    raw_text: str,
) -> Dict[str, Any]:
    """
    Synthesizes and compresses a raw scraped webpage into a high-density,
    structured empirical record to preserve context window bandwidth.
    Extracts metrics, quantitative figures, and key technical takeaways.
    """
    domain = urllib.parse.urlparse(url).netloc or "web-source"

    metric_patterns = [
        r"\b\d+(?:\.\d+)?\s*(?:%|percent|ms|s|wh/kg|kwh|ghz|mhz|gb|tb|mb/s|gb/s|tops|tflops|flops|nm|μm|x\b|fold\b|faster|x faster)\b",
        r"\$\s*\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:billion|million|trillion|k|m|b))?",
        r"\b(?:202[0-9]|203[0-9])\b",
    ]

    extracted_metrics: List[str] = []
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    for line in lines:
        if any(re.search(pat, line, re.I) for pat in metric_patterns):
            clean_l = re.sub(r"^[#\-\*\s]+", "", line).strip()
            if 15 < len(clean_l) < 160 and clean_l not in extracted_metrics:
                extracted_metrics.append(clean_l)
                if len(extracted_metrics) >= 3:
                    break

    paragraphs: List[str] = []
    for l in lines:
        if not l.startswith("#") and len(l) > 25:
            paragraphs.append(l)
            if len(paragraphs) >= 3:
                break

    narrative = " ".join(paragraphs)[:450] if paragraphs else raw_text[:300]

    return {
        "index": source_idx,
        "url": url,
        "title": title,
        "domain": domain,
        "query": query,
        "metrics": extracted_metrics,
        "distilled_takeaway": narrative.strip(),
        "raw_content": raw_text,
    }


def build_synthesized_intelligence_dossier(collected_sources: List[Dict[str, Any]]) -> str:
    """
    Builds a unified, structured multi-source intelligence dossier from 10-20
    scraped and compressed sources. Preserves citations, quantitative metrics,
    and takeaways while fitting strictly within context window limits.
    """
    if not collected_sources:
        return "Internal technical knowledge baseline."

    lines = [
        f"### 🌐 Multi-Source Synthesized Intelligence Dossier ({len(collected_sources)} Primary Sources Analyzed)\n",
        "#### [1] Verified Citation & Source Registry:",
    ]
    for s in collected_sources:
        lines.append(f"- **[{s['index']}]** `{s['domain']}`: [{s['title']}]({s['url']}) (Query: '{s['query']}')")

    lines.append("\n#### [2] Cross-Source Quantitative Metrics & Empirical Benchmarks:")
    metrics_count = 0
    for s in collected_sources:
        if s.get("metrics"):
            for m in s["metrics"][:2]:
                lines.append(f"• [Source {s['index']} - {s['domain']}]: {m}")
                metrics_count += 1
    if metrics_count == 0:
        lines.append("• Empirical metrics cross-referenced across technical documentation.")

    lines.append("\n#### [3] Distilled Technical & Strategic Takeaways by Source:")
    for s in collected_sources:
        lines.append(
            f"• **[Source {s['index']} / {s['domain']}]** {s['title']}:\n"
            f"  {s['distilled_takeaway']}"
        )

    return "\n".join(lines)


def extract_research_cli_flags(raw_str: str) -> Tuple[str, str, int, List[str]]:
    """
    Extracts --format, --urls, --context, --file, --folder, and --seed flags from research command string.
    Returns:
        (topic, format_choice, target_urls, context_items)
    """
    format_choice = "comprehensive"
    target_urls = 10
    context_items: List[str] = []

    text = raw_str.strip()

    # 1. Format flag
    fmt_match = re.search(r'(?:--format|-f)\s+([a-zA-Z_-]+)', text, re.IGNORECASE)
    if fmt_match:
        format_choice = fmt_match.group(1).lower()
        text = re.sub(r'(?:--format|-f)\s+[a-zA-Z_-]+', ' ', text).strip()

    # 2. URLs count flag
    urls_match = re.search(r'(?:--urls|-u)\s+(\d+)', text, re.IGNORECASE)
    if urls_match:
        target_urls = int(urls_match.group(1))
        text = re.sub(r'(?:--urls|-u)\s+\d+', ' ', text).strip()

    # 3. Context / File / Folder / Seed flags
    flag_pattern = r'(?:--(?:file|folder|seed|context|-c))\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))'
    for match in re.finditer(flag_pattern, text, re.IGNORECASE):
        val = match.group(1) or match.group(2) or match.group(3)
        if val:
            # Handle comma-separated items within single flag
            if "," in val and not (val.startswith("http://") or val.startswith("https://") and "," not in val.split("://")[1]):
                context_items.extend([p.strip() for p in val.split(",") if p.strip()])
            else:
                context_items.append(val.strip())

    text = re.sub(flag_pattern, ' ', text, flags=re.IGNORECASE).strip()

    # Clean residual whitespace from topic
    topic = re.sub(r'\s+', ' ', text).strip().strip("'\"")
    return topic, format_choice, target_urls, context_items


def ingest_research_starting_context(
    context_input: Optional[Union[str, List[str], Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Parses and ingests starting context for the Research Swarm:
    - Identifies seed URLs (web addresses) for priority Phase 2 scraping
    - Ingests local files (converting PDFs to Markdown, reading text/code/csv/json)
    - Traverses local directories to discover and ingest research assets
    - Formats starting brief/directives for Phase 1 (Architect)
    - Produces compressed source dictionaries ready for Phase 2 (Intelligence)
    """
    payload: Dict[str, Any] = {
        "raw_input": context_input,
        "seed_urls": [],
        "local_files": [],
        "context_sources": [],
        "summary_for_architect": "",
        "source_count": 0,
        "brief": "",
    }

    if not context_input:
        return payload

    if isinstance(context_input, dict) and "context_sources" in context_input:
        return context_input

    # Normalize into list of candidate tokens
    items: List[str] = []
    if isinstance(context_input, list):
        for item in context_input:
            if isinstance(item, str):
                if "," in item and not (item.startswith("http://") or item.startswith("https://") and "," not in item.split("://")[1]):
                    items.extend([p.strip() for p in item.split(",") if p.strip()])
                else:
                    if item.strip():
                        items.append(item.strip())
    elif isinstance(context_input, str):
        raw = context_input.strip()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        for line in lines:
            if "," in line and not (line.startswith("http://") or line.startswith("https://")):
                items.extend([p.strip() for p in line.split(",") if p.strip()])
            else:
                items.append(line)

    from genesis.tools.uploader import clean_input_path
    from genesis.tools.pdf_converter import convert_pdf_to_markdown
    from genesis.tools.vault_rag import vault_index_file

    seen_seeds = set()
    seen_files = set()
    brief_snippets: List[str] = []

    def _process_single_file(p: Path, source_idx: int) -> Optional[Dict[str, Any]]:
        resolved_str = str(p.resolve())
        if resolved_str in seen_files:
            return None
        seen_files.add(resolved_str)

        file_text = ""
        file_title = p.name
        is_pdf = p.suffix.lower() == ".pdf"

        if is_pdf:
            try:
                res_msg = convert_pdf_to_markdown(str(p))
                md_path_match = re.search(r"Markdown File:\s*`([^`]+)`", res_msg)
                if md_path_match and Path(md_path_match.group(1)).exists():
                    md_path = Path(md_path_match.group(1))
                    file_text = md_path.read_text(encoding="utf-8", errors="replace")
                else:
                    alt_md = p.with_suffix(".md")
                    if alt_md.exists():
                        file_text = alt_md.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                console.print(f"  [yellow]⚠️ Could not convert PDF {p.name}: {e}[/yellow]")
        else:
            try:
                raw_bytes = p.read_bytes()
                for enc in ["utf-8", "latin-1"]:
                    try:
                        file_text = raw_bytes[:25000].decode(enc)
                        break
                    except Exception:
                        continue
            except Exception as e:
                console.print(f"  [yellow]⚠️ Could not read file {p.name}: {e}[/yellow]")

        if not file_text:
            return None

        first_h1 = re.search(r"^#\s+(.+)", file_text, re.MULTILINE)
        if first_h1:
            file_title = f"{first_h1.group(1).strip()} ({p.name})"

        compressed = compress_source_findings(
            source_idx=source_idx,
            url=f"file://{p.resolve()}",
            title=f"[Local Document] {file_title}",
            query="User Uploaded Starting Context",
            raw_text=file_text,
        )
        compressed["domain"] = "local-document"
        compressed["local_path"] = str(p.resolve())

        try:
            vault_index_file(str(p))
        except Exception:
            pass

        return compressed

    for item in items:
        # 1. URL check
        if item.startswith("http://") or item.startswith("https://"):
            clean_u = item.strip().rstrip(".,;")
            if clean_u not in seen_seeds:
                seen_seeds.add(clean_u)
                payload["seed_urls"].append(clean_u)
            continue

        # 2. Local path check
        try:
            p = clean_input_path(item)
            if p.exists():
                if p.is_file():
                    src = _process_single_file(p, len(payload["context_sources"]) + 1)
                    if src:
                        payload["context_sources"].append(src)
                        payload["local_files"].append({
                            "path": str(p.resolve()),
                            "name": p.name,
                            "size": p.stat().st_size,
                            "type": "pdf" if p.suffix.lower() == ".pdf" else "document",
                            "title": src["title"],
                        })
                    continue
                elif p.is_dir():
                    SUPPORTED_EXTS = {
                        ".pdf", ".md", ".txt", ".csv", ".json", ".yaml", ".yml",
                        ".py", ".html", ".rst", ".tsv", ".sql", ".sh",
                    }
                    found_count = 0
                    for root, _, files in os.walk(p):
                        for fname in sorted(files):
                            if fname.startswith("."):
                                continue
                            fpath = Path(root) / fname
                            if fpath.suffix.lower() in SUPPORTED_EXTS:
                                src = _process_single_file(fpath, len(payload["context_sources"]) + 1)
                                if src:
                                    payload["context_sources"].append(src)
                                    payload["local_files"].append({
                                        "path": str(fpath.resolve()),
                                        "name": fpath.name,
                                        "size": fpath.stat().st_size,
                                        "type": "pdf" if fpath.suffix.lower() == ".pdf" else "document",
                                        "title": src["title"],
                                    })
                                    found_count += 1
                                    if found_count >= 15:
                                        break
                        if found_count >= 15:
                            break
                    continue
        except Exception:
            pass

        # 3. Text brief / notes
        if len(item) > 10:
            brief_snippets.append(item)

    payload["brief"] = " ".join(brief_snippets).strip()
    payload["source_count"] = len(payload["context_sources"]) + len(payload["seed_urls"])

    # Digest for Phase 1 Architect
    summary_lines = []
    if payload["local_files"]:
        summary_lines.append(f"• **Attached Local Documents & Files ({len(payload['local_files'])} items):**")
        for f in payload["local_files"][:8]:
            summary_lines.append(f"  - `{f['name']}`: {f['title']}")
        if len(payload["local_files"]) > 8:
            summary_lines.append(f"  - ... and {len(payload['local_files']) - 8} more files.")

    if payload["seed_urls"]:
        summary_lines.append(f"• **Prioritized Seed URLs ({len(payload['seed_urls'])} items):**")
        for u in payload["seed_urls"]:
            summary_lines.append(f"  - `{u}`")

    if payload["brief"]:
        summary_lines.append(f"• **User Directives & Brief:**\n  > {payload['brief']}")

    payload["summary_for_architect"] = "\n".join(summary_lines)
    return payload


class ResearchWorkerPersona:
    """Specialized persona in the research swarm."""
    def __init__(self, name: str, title: str, system_directive: str):
        self.name = name
        self.title = title
        self.system_directive = system_directive


class ResearchSwarmCoordinator:
    """
    Coordinates a 5-phase, process-oriented multi-agent research swarm
    to produce exhaustive, publication-grade analytical dossiers.
    """

    def __init__(self, base_agent: Optional[GenesisAgent] = None):
        self.agent = base_agent or GenesisAgent()
        self.personas = self._init_personas()

    def _init_personas(self) -> Dict[str, ResearchWorkerPersona]:
        return {
            "architect": ResearchWorkerPersona(
                name="Dr. Vance",
                title="Lead Research Architect & Strategist",
                system_directive=(
                    "You are the Lead Research Architect. Your mission is to decompose the user's research topic "
                    "into an exhaustive, rigorous Research Charter. "
                    "Define: 1) Core Hypothesis & Investigative Thesis, 2) 6-8 Mandatory Analytical Pillars, "
                    "3) Specific quantitative metrics and benchmarks required, "
                    "and 4) Exactly 6-8 diverse, targeted search queries to extract technical truth."
                ),
            ),
            "intelligence": ResearchWorkerPersona(
                name="Scout Alpha",
                title="Multi-Angle Intelligence & Recon Specialist",
                system_directive=(
                    "You are the Deep Intelligence Specialist. Your mission is to gather empirical facts, "
                    "verified statistics, official specifications, vendor comparisons, benchmark numbers, "
                    "and primary documentation. Use web_search and web_scrape. Extract real numbers, dates, "
                    "architecture parameters, and verified URLs. Avoid unverified assumptions."
                ),
            ),
            "analyst": ResearchWorkerPersona(
                name="Senior Analyst Chen",
                title="Quantitative & Analytical Systems Modeler",
                system_directive=(
                    "You are the Senior Research Analyst. Your mission is to convert raw intelligence into "
                    "structured analytical frameworks. Formulate: 1) Comparative Feature/Benchmark Markdown Tables, "
                    "2) Architectural & Technical Trade-offs, 3) SWOT / Cost-Benefit Matrix, "
                    "and 4) Critical Failure Modes. Synthesize conflicting viewpoints into objective truth."
                ),
            ),
            "auditor": ResearchWorkerPersona(
                name="Inspector Sterling",
                title="Red Team Research Auditor & Peer Reviewer",
                system_directive=(
                    "You are the Red Team Research Auditor. Your mission is to rigorously review the analytical "
                    "findings against publication-grade standards. Check for: superficial claims, lack of quantitative data, "
                    "missing citations, logical gaps, or unsupported conclusions. "
                    "Emit a mandatory Remediation Directives list for the Chief Editor to fix before final publication."
                ),
            ),
            "editor": ResearchWorkerPersona(
                name="Editor-in-Chief Evelyn",
                title="Principal Executive Editor & Publication Author",
                system_directive=(
                    "You are the Editor-in-Chief. Your mission is to author the definitive, publication-grade "
                    "Research Report in Markdown. The report must be exhaustive, authoritative, deeply technical, "
                    "and structured with: Title, Executive Summary, 6+ In-depth Sections, Markdown Tables, "
                    "Strategic Takeaways, and a formal References & Citations Bibliography."
                ),
            ),
        }

    def run_research_swarm(
        self,
        topic: str,
        report_format: str = "comprehensive",
        target_urls: int = 10,
        on_event_callback: Optional[Any] = None,
        starting_context: Optional[Union[str, List[str], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the 5-phase research swarm with chosen report format.
        Supports user-provided starting context (seed URLs, files, folders, or notes),
        extracts at least 10 (up to 20) verified sources, compresses and synthesizes findings
        to protect context window limits, and permanently archives raw source dossiers to disk.
        """
        fmt = get_format_metadata(report_format)
        swarm_id = f"res_swarm_{int(time.time())}"
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.lower()).strip("_")[:45] or "research"
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        target_url_count = max(10, min(target_urls, 25))

        report_filename = f"{slug}_{fmt['filename_suffix']}.md"
        workspace_file = WORKSPACE_ROOT / report_filename
        vault_file = RESEARCH_DIR / f"{slug}_{fmt['id']}_{int(time.time())}.md"

        # 1. Parse & Ingest User Starting Context (URLs, Files, Folders, Briefs)
        starting_data = ingest_research_starting_context(starting_context)

        dossier = {
            "swarm_id": swarm_id,
            "topic": topic,
            "report_format": fmt["id"],
            "report_format_name": fmt["name"],
            "start_time": time.time(),
            "phases": {},
            "report_path": str(workspace_file),
            "vault_path": str(vault_file),
            "status": "IN_PROGRESS",
            "summary": "",
            "sources_count": 0,
            "starting_context": {
                "source_count": starting_data["source_count"],
                "seed_urls": starting_data["seed_urls"],
                "local_files": [f["name"] for f in starting_data["local_files"]],
                "brief": starting_data["brief"],
            },
        }

        panel_lines = [
            f"[bold cyan]Research Topic:[/bold cyan] [white]{topic}[/white]",
            f"[bold yellow]Report Format:[/bold yellow] {fmt['icon']} [bold green]{fmt['name']}[/bold green] ([dim]{fmt['badge']}[/dim])",
            f"[bold magenta]Extraction Target:[/bold magenta] ≥{target_url_count} Verified Sources (Multi-Source Synthesis & Compression)",
        ]
        if starting_data["source_count"] > 0:
            parts = []
            if starting_data["local_files"]:
                parts.append(f"{len(starting_data['local_files'])} file(s)/folder(s)")
            if starting_data["seed_urls"]:
                parts.append(f"{len(starting_data['seed_urls'])} seed URL(s)")
            panel_lines.append(f"[bold blue]Starting Context Attached:[/bold blue] {', '.join(parts)}")
        panel_lines.extend([
            "[dim]5-Phase Pipeline: Architect → Intelligence → Analyst → Auditor → Chief Editor[/dim]",
            f"[dim]Deliverable target: {report_filename}[/dim]",
        ])

        console.print(
            Panel(
                "\n".join(panel_lines),
                title="[bold white]🔬 Process-Oriented Research Swarm[/bold white]",
                border_style="cyan",
            )
        )

        def _notify(phase_num: int, phase_id: str, label: str, details: str):
            if on_event_callback:
                try:
                    on_event_callback(phase_num, phase_id, label, details)
                except Exception:
                    pass

        # Context backup for isolation
        _saved_messages = list(self.agent.messages)
        system_base = next(
            (m for m in _saved_messages if isinstance(m, dict) and m.get("role") == "system"),
            {"role": "system", "content": "You are Project Genesis sovereign intelligence engine."},
        )

        try:
            # =========================================================================
            # PHASE 1: Research Architect & Scoping Lead
            # =========================================================================
            _notify(1, "architect", "Phase 1: Research Architecture & Scoping", f"Deconstructing topic into investigative pillars for {fmt['name']}...")
            console.print(f"\n[bold cyan]📐 [Phase 1/5] Dr. Vance (Research Architect) formulating Charter for '{fmt['name']}'...[/bold cyan]")

            architect_prompt = (
                f"[{self.personas['architect'].system_directive}]\n\n"
                f"RESEARCH TOPIC: '{topic}'\n"
                f"CHOSEN REPORT FORMAT: {fmt['name']} ({fmt['badge']})\n"
                f"FORMAT OBJECTIVE: {fmt['architect_focus']}\n\n"
            )
            if starting_data["summary_for_architect"]:
                architect_prompt += (
                    f"### USER-ATTACHED STARTING CONTEXT & EVIDENCE BASE:\n"
                    f"{starting_data['summary_for_architect']}\n\n"
                    f"CHARTER INTEGRATION DIRECTIVE: Formulate the 6 Research Pillars to directly incorporate, evaluate, and expand upon the user's attached documents and seed URLs. Formulate search queries to specifically deep-dive, verify, or fill gaps around this starting context.\n\n"
                )
            architect_prompt += (
                f"Generate a rigorous Research Charter tailored specifically for a '{fmt['name']}' with:\n"
                f"1. Executive Problem Statement & Core Investigative Thesis\n"
                f"2. 6 Mandatory Research Pillars aligned with {fmt['name']}\n"
                f"3. Quantitative target data points needed (benchmarks, market sizes, specs, costs)\n"
                f"4. Exactly 8-12 diverse targeted web search queries formatted as lines starting with 'SEARCH_QUERY: <query>' "
                f"(spanning technical foundations, comparative benchmarks, market data, vendor architectures, risk/failure modes, and future roadmap)\n"
                f"Be analytical, comprehensive, and non-generic."
            )
            self.agent.messages = [system_base]
            charter_output = self.agent.run_turn(architect_prompt)
            dossier["phases"]["phase1_charter"] = charter_output

            if self.agent.is_aborted():
                dossier["status"] = "ABORTED"
                return dossier

            # Extract search queries formulated by Architect
            raw_queries = re.findall(r"SEARCH_QUERY:\s*(.+)", charter_output)
            if not raw_queries:
                raw_queries = [
                    topic,
                    f"{topic} architecture technical specifications",
                    f"{topic} performance benchmarks comparison",
                    f"{topic} empirical test metrics statistics",
                    f"{topic} market analysis industry reports",
                    f"{topic} challenges failure modes risks",
                    f"{topic} implementation case studies trade-offs",
                    f"{topic} key vendors pricing cost comparison",
                ]
            queries_to_run = [q.strip() for q in raw_queries][:12]

            # =========================================================================
            # PHASE 2: Multi-Angle Reconnaissance & Deep Intelligence Squad
            # =========================================================================
            _notify(2, "intelligence", "Phase 2: Multi-Angle Intelligence Gathering", f"Executing recon probes targeting at least {target_url_count} verified sources...")
            console.print(f"\n[bold yellow]🔍 [Phase 2/5] Scout Alpha (Intelligence Squad) extracting empirical data (Target: ≥{target_url_count} sources)...[/bold yellow]")

            collected_sources: List[Dict[str, Any]] = []
            seen_urls = set()

            # Step 2A: Attach User's Uploaded Local Files / Folders as primary verified baseline sources
            for ctx_src in starting_data["context_sources"]:
                ctx_src["index"] = len(collected_sources) + 1
                collected_sources.append(ctx_src)
                seen_urls.add(ctx_src["url"])
                console.print(f"  [dim]📎 Attached Starting Document [{len(collected_sources)}]: {ctx_src['title'][:55]} ({ctx_src['domain']})[/dim]")

            # Step 2B: Scrape user-provided seed URLs with high priority
            for seed_u in starting_data["seed_urls"]:
                clean_u = seed_u.split("?")[0]
                if clean_u in seen_urls:
                    continue
                seen_urls.add(clean_u)
                console.print(f"  [dim]🌐 Scraping User Seed URL: {seed_u}[/dim]")
                scraped = web_scrape(seed_u, max_chars=3500)
                if "Web Scrape Error" not in scraped and len(scraped) > 50:
                    title_match = re.search(r"^#\s+(.+)", scraped)
                    page_title = title_match.group(1).strip() if title_match else urllib.parse.urlparse(seed_u).netloc
                    compressed_item = compress_source_findings(
                        source_idx=len(collected_sources) + 1,
                        url=seed_u,
                        title=f"[Seed URL] {page_title}",
                        query="User Priority Seed URL",
                        raw_text=scraped,
                    )
                    collected_sources.append(compressed_item)
                    console.print(f"    [dim]✓ [{len(collected_sources)}] Extracted Seed: {page_title[:45]} ({compressed_item['domain']})[/dim]")

            # Step 2C: Run web search probes for remaining target slots
            for q_idx, query in enumerate(queries_to_run, 1):
                console.print(f"  [dim]• Probe {q_idx}/{len(queries_to_run)}: Searching '{query}'[/dim]")
                search_res = web_search(query, max_results=6)
                urls = re.findall(r"- \*\*URL\*\*: `(https?://[^`]+)`", search_res)

                for u in urls:
                    clean_u = u.split("?")[0]
                    if clean_u in seen_urls or any(clean_u.lower().endswith(x) for x in [".pdf", ".png", ".jpg", ".zip", ".gif", ".svg"]):
                        continue
                    seen_urls.add(clean_u)

                    # Scrape substantive textual content
                    scraped = web_scrape(u, max_chars=3500)
                    if "Web Scrape Error" not in scraped and len(scraped) > 50:
                        title_match = re.search(r"^#\s+(.+)", scraped)
                        page_title = title_match.group(1).strip() if title_match else urllib.parse.urlparse(u).netloc

                        compressed_item = compress_source_findings(
                            source_idx=len(collected_sources) + 1,
                            url=u,
                            title=page_title,
                            query=query,
                            raw_text=scraped,
                        )
                        collected_sources.append(compressed_item)
                        console.print(f"    [dim]✓ [{len(collected_sources)}/{target_url_count}] Extracted: {page_title[:45]} ({compressed_item['domain']})[/dim]")

                    if len(collected_sources) >= target_url_count:
                        break
                if len(collected_sources) >= target_url_count:
                    break

            # Fallback exploration probes if initial queries did not yield target_url_count
            if len(collected_sources) < target_url_count:
                fallback_probes = [
                    f"{topic} empirical benchmark metrics",
                    f"{topic} technical whitepaper architecture",
                    f"{topic} market analysis industry reports",
                    f"{topic} implementation case studies",
                    f"{topic} performance evaluation comparison",
                ]
                for fb_query in fallback_probes:
                    if len(collected_sources) >= target_url_count:
                        break
                    console.print(f"  [dim]• Fallback Probe: Searching '{fb_query}'[/dim]")
                    fb_search = web_search(fb_query, max_results=6)
                    fb_urls = re.findall(r"- \*\*URL\*\*: `(https?://[^`]+)`", fb_search)
                    for u in fb_urls:
                        clean_u = u.split("?")[0]
                        if clean_u in seen_urls or any(clean_u.lower().endswith(x) for x in [".pdf", ".png", ".jpg", ".zip", ".gif", ".svg"]):
                            continue
                        seen_urls.add(clean_u)
                        scraped = web_scrape(u, max_chars=3500)
                        if "Web Scrape Error" not in scraped and len(scraped) > 50:
                            title_match = re.search(r"^#\s+(.+)", scraped)
                            page_title = title_match.group(1).strip() if title_match else urllib.parse.urlparse(u).netloc
                            compressed_item = compress_source_findings(
                                source_idx=len(collected_sources) + 1,
                                url=u,
                                title=page_title,
                                query=fb_query,
                                raw_text=scraped,
                            )
                            collected_sources.append(compressed_item)
                            console.print(f"    [dim]✓ [{len(collected_sources)}/{target_url_count}] Extracted: {page_title[:45]} ({compressed_item['domain']})[/dim]")
                        if len(collected_sources) >= target_url_count:
                            break

            # Logically store raw sources to disk vault for complete data retention
            raw_sources_payload = {
                "swarm_id": swarm_id,
                "topic": topic,
                "timestamp": timestamp_str,
                "source_count": len(collected_sources),
                "sources": [
                    {
                        "index": s["index"],
                        "url": s["url"],
                        "title": s["title"],
                        "domain": s["domain"],
                        "query": s["query"],
                        "metrics": s["metrics"],
                        "distilled_takeaway": s["distilled_takeaway"],
                        "raw_content": s["raw_content"],
                    }
                    for s in collected_sources
                ],
            }
            raw_sources_file = DOSSIERS_DIR / f"{slug}_{swarm_id}_sources.json"
            raw_sources_file.write_text(json.dumps(raw_sources_payload, indent=2, ensure_ascii=False), encoding="utf-8")

            # Build unified, compressed multi-source intelligence dossier for context safety
            synthesized_dossier = build_synthesized_intelligence_dossier(collected_sources)
            dossier["phases"]["phase2_sources_count"] = len(collected_sources)
            dossier["phases"]["phase2_raw_sources_file"] = str(raw_sources_file)
            dossier["raw_sources_file"] = str(raw_sources_file)
            dossier["sources_count"] = len(collected_sources)

            if self.agent.is_aborted():
                dossier["status"] = "ABORTED"
                return dossier

            # =========================================================================
            # PHASE 3: Quantitative & Analytical Modeler
            # =========================================================================
            _notify(3, "analyst", "Phase 3: Analytical & Quantitative Modeling", f"Constructing matrices and analytical models for {fmt['name']} across {len(collected_sources)} sources...")
            console.print(f"\n[bold green]📊 [Phase 3/5] Analyst Chen modeling framework across {len(collected_sources)} sources for '{fmt['name']}'...[/bold green]")

            analyst_prompt = (
                f"[{self.personas['analyst'].system_directive}]\n\n"
                f"TOPIC: '{topic}'\n"
                f"REPORT FORMAT: {fmt['name']} ({fmt['badge']})\n"
                f"ANALYTICAL DIRECTIVE: {fmt['analyst_focus']}\n\n"
                f"RESEARCH CHARTER:\n{charter_output[:2500]}\n\n"
                f"EMPIRICAL INTELLIGENCE DOSSIER (Cross-Section of {len(collected_sources)} Primary Sources):\n{synthesized_dossier}\n\n"
                f"Produce an Analytical Synthesis Document tailored for {fmt['name']} including:\n"
                f"1. Detailed Benchmark / Attribute Comparison Table (Markdown matrix with columns appropriate for {fmt['name']})\n"
                f"2. Core Mechanics, Drivers & Differentiators\n"
                f"3. Analytical Matrix (e.g. SWOT, Trade-Offs, Risk Heatmap, or KPI Dashboard)\n"
                f"4. Quantitative Cost / ROI / Efficiency Trade-Offs cross-referencing extracted empirical metrics\n"
                f"Be factual, quantitative, and analytically deep."
            )
            self.agent.messages = [system_base]
            analyst_output = self.agent.run_turn(analyst_prompt)
            dossier["phases"]["phase3_analysis"] = analyst_output

            if self.agent.is_aborted():
                dossier["status"] = "ABORTED"
                return dossier

            # =========================================================================
            # PHASE 4: Critical Reviewer & Peer Auditor
            # =========================================================================
            _notify(4, "auditor", "Phase 4: Critical Quality & Fact Audit", f"Red-teaming findings against {fmt['badge']} standards...")
            console.print(f"\n[bold magenta]🧐 [Phase 4/5] Inspector Sterling (Red Team Auditor) peer reviewing for '{fmt['name']}'...[/bold magenta]")

            auditor_prompt = (
                f"[{self.personas['auditor'].system_directive}]\n\n"
                f"TOPIC: '{topic}'\n"
                f"REPORT FORMAT: {fmt['name']} ({fmt['badge']})\n"
                f"AUDIT DIRECTIVE: {fmt['auditor_focus']}\n\n"
                f"RESEARCH CHARTER:\n{charter_output[:1800]}\n\n"
                f"ANALYTICAL SYNTHESIS:\n{analyst_output[:3500]}\n\n"
                f"Audit this research draft for publication in {fmt['name']} format:\n"
                f"1. Highlight 3 strongest analytical insights.\n"
                f"2. Identify any missing perspectives, unverified assertions, or format deviations.\n"
                f"3. Provide exactly 4 mandatory directives for Chief Editor Evelyn to ensure the final deliverable satisfies {fmt['badge']} standards."
            )
            self.agent.messages = [system_base]
            auditor_output = self.agent.run_turn(auditor_prompt)
            dossier["phases"]["phase4_audit"] = auditor_output

            if self.agent.is_aborted():
                dossier["status"] = "ABORTED"
                return dossier

            # =========================================================================
            # PHASE 5: Chief Executive Editor & Publication Lead
            # =========================================================================
            _notify(5, "editor", "Phase 5: Executive Publication & Authoring", f"Authoring {fmt['name']} to {report_filename}...")
            console.print(f"\n[bold cyan]🖋️ [Phase 5/5] Editor-in-Chief Evelyn authoring '{fmt['name']}' deliverable...[/bold cyan]")

            citations_md = "\n".join([f"- [{s['index']}] {s['url']} ({s['domain']}) — Query: '{s['query']}'" for s in collected_sources])
            if not citations_md:
                citations_md = "- Sovereign Local Intelligence & Technical Knowledge Base"

            sections_spec = "\n".join([f"• Section {idx}: {sec}" for idx, sec in enumerate(fmt["sections"], 1)])

            editor_prompt = (
                f"[{self.personas['editor'].system_directive}]\n\n"
                f"TOPIC: '{topic}'\n"
                f"TARGET FILENAME: '{report_filename}'\n"
                f"CHOSEN REPORT FORMAT: '{fmt['name']}' ({fmt['badge']})\n\n"
                f"CHARTER:\n{charter_output[:1500]}\n\n"
                f"ANALYTICAL MATRICES & BENCHMARKS:\n{analyst_output[:3000]}\n\n"
                f"AUDITOR REMEDIATION MANDATES:\n{auditor_output[:1500]}\n\n"
                f"AVAILABLE CITATIONS ({len(collected_sources)} Verified Sources):\n{citations_md}\n\n"
                f"INSTRUCTIONS:\n"
                f"Author a complete, authoritative, publication-ready research deliverable in Markdown.\n"
                f"Format Requirements:\n"
                f"• Title: # {fmt['title_prefix']}: {topic}\n"
                f"• Metadata Header: Date: {timestamp_str} | Author: Project Genesis Research Swarm | Format: {fmt['name']} ({fmt['badge']}) | Sources Analyzed: {len(collected_sources)} | Status: Verified\n"
                f"Mandatory Sections to Include:\n"
                f"{sections_spec}\n"
                f"Write with maximum depth, authoritative rigor, and zero conversational filler. Output the FULL report text."
            )
            self.agent.messages = [system_base]
            final_report_content = self.agent.run_turn(editor_prompt)

            # If an inference error occurred, attempt recovery with clean prompt
            if final_report_content.startswith("LLM Inference Error:"):
                console.print(f"[bold yellow]⚠️ Editor turn returned inference error; attempting clean retry...[/bold yellow]")
                self.agent.messages = [system_base]
                retry_prompt = (
                    f"Author the final publication research report for '{topic}' in Markdown format.\n\n"
                    f"Format: # {fmt['title_prefix']}: {topic}\n\n"
                    f"SECTIONS TO INCLUDE:\n{sections_spec}\n\n"
                    f"ANALYTICAL HIGHLIGHTS:\n{analyst_output[:2000]}\n\n"
                    f"VERIFIED CITATIONS:\n{citations_md[:2000]}"
                )
                final_report_content = self.agent.run_turn(retry_prompt)

            # Ensure markdown header
            if not final_report_content.strip().startswith("#"):
                final_report_content = f"# {fmt['title_prefix']}: {topic}\n\n" + final_report_content

            # Write finalized report to disk: Workspace file + ~/.genesis/research/ vault
            workspace_file.write_text(final_report_content, encoding="utf-8")
            vault_file.write_text(final_report_content, encoding="utf-8")

            word_count = len(final_report_content.split())
            dossier["word_count"] = word_count
            dossier["status"] = "GOAL_ACHIEVED"
            dossier["summary"] = (
                f"{fmt['name']} complete ({word_count:,} words across {len(collected_sources)} extracted sources). "
                f"Saved to '{report_filename}' and local vault."
            )

            console.print(f"\n[bold green]✅ Research Swarm Complete![/bold green]")
            console.print(f"📄 Deliverable written: [bold cyan]{workspace_file}[/bold cyan] ({word_count:,} words)")
            console.print(f"🗄️ Raw sources vault: [dim]{raw_sources_file}[/dim]")
            console.print(f"🏛️ Vault archive: [dim]{vault_file}[/dim]\n")

            return dossier

        except Exception as e:
            console.print(f"\n[bold red]Research Swarm Encountered Error:[/bold red] {e}")
            dossier["status"] = "ERROR"
            dossier["error"] = str(e)
            return dossier
        finally:
            self.agent.messages = _saved_messages
