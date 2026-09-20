"""
Tests for Project Genesis 5-Phase Process-Oriented Research Swarm.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from genesis.core.agent import GenesisAgent
from genesis.core.research_swarm import ResearchSwarmCoordinator
from genesis.core.swarm import SwarmCoordinator


def test_research_swarm_personas_init():
    coordinator = ResearchSwarmCoordinator()
    assert len(coordinator.personas) == 5
    assert "architect" in coordinator.personas
    assert "intelligence" in coordinator.personas
    assert "analyst" in coordinator.personas
    assert "auditor" in coordinator.personas
    assert "editor" in coordinator.personas


def test_research_swarm_execution_flow(tmp_path):
    agent = GenesisAgent()

    # Mock agent.run_turn for each phase
    def _mock_turn(prompt):
        if "Research Architect" in prompt or "Dr. Vance" in prompt:
            return (
                "## Research Charter\n"
                "1. Hypothesis: Solid-state batteries will reach commercial EV parity by 2027.\n"
                "2. Pillars: Electrolytes, Manufacturing Costs, Safety Metrics.\n"
                "SEARCH_QUERY: solid state battery benchmarks 2026\n"
                "SEARCH_QUERY: solid state battery manufacturing costs\n"
            )
        elif "Senior Analyst" in prompt or "Analyst Chen" in prompt:
            return (
                "## Quantitative Analysis\n"
                "| Technology | Energy Density | Cost ($/kWh) |\n"
                "| Lithium-ion | 260 Wh/kg | $110 |\n"
                "| Solid-State | 450 Wh/kg | $160 |\n\n"
                "### SWOT Breakdown\nStrengths: Higher density."
            )
        elif "Red Team" in prompt or "Inspector Sterling" in prompt:
            return (
                "## Audit Findings\n"
                "1. Strong comparative benchmarks.\n"
                "2. Need deeper analysis on manufacturing yield."
            )
        elif "Editor-in-Chief" in prompt or "Evelyn" in prompt:
            return (
                "# Comprehensive Research Report: Solid-State Batteries\n\n"
                "## Executive Summary\nSolid-state batteries represent the defining paradigm shift...\n\n"
                "## Section 1: Architectural Foundations\nDetailed technical analysis of solid electrolytes.\n\n"
                "## Section 2: Comparative Benchmarks\n| Metric | Li-ion | Solid-State |\n| Wh/kg | 260 | 450 |\n\n"
                "## Section 3: References\n- [1] QuantumScape Battery Benchmark Study 2026."
            )
        return "Generic response"

    with patch.object(agent, "run_turn", side_effect=_mock_turn), \
         patch("genesis.core.research_swarm.web_search", return_value="- **URL**: `https://example.com/battery`\n"), \
         patch("genesis.core.research_swarm.web_scrape", return_value="Detailed article text with metrics and specs."):

        coordinator = ResearchSwarmCoordinator(base_agent=agent)
        event_log = []

        def _callback(phase_num, phase_id, label, details):
            event_log.append((phase_num, phase_id))

        dossier = coordinator.run_research_swarm(
            topic="Solid-State Batteries",
            on_event_callback=_callback,
        )

        assert dossier["status"] == "GOAL_ACHIEVED"
        assert dossier["word_count"] > 20
        assert len(event_log) == 5
        assert Path(dossier["report_path"]).exists()

        # Clean up created file
        if Path(dossier["report_path"]).exists():
            Path(dossier["report_path"]).unlink()


def test_swarm_coordinator_delegates_research():
    swarm = SwarmCoordinator()
    with patch.object(ResearchSwarmCoordinator, "run_research_swarm", return_value={"status": "GOAL_ACHIEVED", "summary": "Done"}) as mock_res:
        res = swarm.run_swarm("Deep research and analyze quantum computing post-quantum cryptography")
        mock_res.assert_called_once()
        assert res["status"] == "GOAL_ACHIEVED"


def test_report_formats_registry():
    from genesis.core.research_swarm import (
        REPORT_FORMATS,
        get_report_formats,
        get_format_metadata,
        format_report_formats_table,
        format_report_formats_markdown,
    )
    formats = get_report_formats()
    assert len(formats) == 5
    ids = [f["id"] for f in formats]
    assert "comprehensive" in ids
    assert "executive" in ids
    assert "technical" in ids
    assert "market" in ids
    assert "due_diligence" in ids

    exec_fmt = get_format_metadata("executive")
    assert exec_fmt["id"] == "executive"
    assert exec_fmt["filename_suffix"] == "executive_briefing_memo"

    # Fallback to comprehensive on unknown
    fallback_fmt = get_format_metadata("unknown_format_xyz")
    assert fallback_fmt["id"] == "comprehensive"

    # Test Rich table generation
    table = format_report_formats_table()
    assert len(table.rows) == 5

    # Test Markdown generation
    md = format_report_formats_markdown()
    assert "### 📑 Genesis Research Swarm: Available Report Formats" in md
    assert "executive" in md
    assert "technical" in md


def test_research_swarm_with_executive_format():
    agent = GenesisAgent()

    def _mock_turn(prompt):
        if "Dr. Vance" in prompt:
            return "Charter output with SEARCH_QUERY: quantum computing market size"
        elif "Analyst Chen" in prompt:
            return "KPI dashboard and ROI analysis"
        elif "Inspector Sterling" in prompt:
            return "Audit peer review directives"
        elif "Editor-in-Chief" in prompt:
            return "# Executive Briefing & Decision Memo: Quantum\n\n## Executive Dashboard\nData here."
        return "Generic turn"

    with patch.object(agent, "run_turn", side_effect=_mock_turn), \
         patch("genesis.core.research_swarm.web_search", return_value="- **URL**: `https://example.com/quantum`\n"), \
         patch("genesis.core.research_swarm.web_scrape", return_value="Quantum market data and metrics."):

        coordinator = ResearchSwarmCoordinator(base_agent=agent)
        dossier = coordinator.run_research_swarm(
            topic="Quantum Computing",
            report_format="executive",
        )

        assert dossier["status"] == "GOAL_ACHIEVED"
        assert dossier["report_format"] == "executive"
        assert "executive_briefing_memo" in dossier["report_path"]

        # Clean up
        p = Path(dossier["report_path"])
        if p.exists():
            p.unlink()


def test_swarm_coordinator_parses_format_and_urls_flag():
    swarm = SwarmCoordinator()
    with patch.object(ResearchSwarmCoordinator, "run_research_swarm", return_value={"status": "GOAL_ACHIEVED", "summary": "Done"}) as mock_res:
        res = swarm.run_swarm("Deep research autonomous vehicles --format technical --urls 15")
        mock_res.assert_called_once()
        call_kwargs = mock_res.call_args
        assert call_kwargs.kwargs.get("report_format") == "technical"
        assert call_kwargs.kwargs.get("target_urls") == 15


def test_compress_source_findings_and_build_dossier():
    from genesis.core.research_swarm import compress_source_findings, build_synthesized_intelligence_dossier

    raw_article = (
        "# Quantum Supremacy Benchmarks\n"
        "Researchers achieved a 450 Wh/kg equivalent metric with 99.8% fidelity in 2026.\n"
        "The project secured $120 million in venture funding for scale.\n"
        "This architectural leap enables sub-millisecond execution times across distributed nodes."
    )
    compressed = compress_source_findings(
        source_idx=1,
        url="https://nature.com/articles/quantum-2026",
        title="Quantum Supremacy Benchmarks",
        query="quantum computing benchmarks 2026",
        raw_text=raw_article,
    )

    assert compressed["index"] == 1
    assert compressed["domain"] == "nature.com"
    assert len(compressed["metrics"]) >= 1
    assert any("450 Wh/kg" in m or "99.8%" in m or "$120 million" in m for m in compressed["metrics"])
    assert "sub-millisecond execution" in compressed["distilled_takeaway"]

    dossier_text = build_synthesized_intelligence_dossier([compressed])
    assert "### 🌐 Multi-Source Synthesized Intelligence Dossier" in dossier_text
    assert "**[1]** `nature.com`" in dossier_text
    assert "Quantitative Metrics & Empirical Benchmarks" in dossier_text


def test_research_swarm_extracts_10_urls_and_saves_dossier():
    import json
    agent = GenesisAgent()

    def _mock_turn(prompt):
        if "Dr. Vance" in prompt:
            return (
                "## Charter\nPillars: Tech, Market, Risk.\n"
                "SEARCH_QUERY: ai chip architectures\n"
                "SEARCH_QUERY: ai chip benchmarks\n"
                "SEARCH_QUERY: ai chip memory bandwidth\n"
            )
        elif "Analyst Chen" in prompt:
            return "## Comparative Analysis Table\n| Chip | TOPS | Memory |\n| H100 | 2000 | 80GB |"
        elif "Inspector Sterling" in prompt:
            return "## Audit\nDirectives: Add citations."
        elif "Editor-in-Chief" in prompt:
            return "# Comprehensive Research Report: AI Chips\n\n## Summary\nComprehensive findings."
        return "Generic turn"

    # Generate 12 distinct search results
    mock_search_results = "\n".join([
        f"- **URL**: `https://example.com/source_{i}`\n" for i in range(1, 15)
    ])

    with patch.object(agent, "run_turn", side_effect=_mock_turn), \
         patch("genesis.core.research_swarm.web_search", return_value=mock_search_results), \
         patch("genesis.core.research_swarm.web_scrape", return_value="# Title\nEmpirical metrics showing 400 TOPS at 150W in 2026.\nSubstantive content here."):

        coordinator = ResearchSwarmCoordinator(base_agent=agent)
        dossier = coordinator.run_research_swarm(
            topic="Next-Gen AI Accelerators",
            report_format="comprehensive",
            target_urls=10,
        )

        assert dossier["status"] == "GOAL_ACHIEVED"
        assert dossier["sources_count"] >= 10
        assert dossier["phases"]["phase2_sources_count"] >= 10
        assert Path(dossier["raw_sources_file"]).exists()

        # Verify JSON content of raw sources file
        raw_json = json.loads(Path(dossier["raw_sources_file"]).read_text(encoding="utf-8"))
        assert raw_json["source_count"] >= 10
        assert len(raw_json["sources"]) >= 10
        assert raw_json["sources"][0]["domain"] == "example.com"
        assert raw_json["sources"][0]["raw_content"] != ""

        # Clean up files
        if Path(dossier["report_path"]).exists():
            Path(dossier["report_path"]).unlink()
        if Path(dossier["raw_sources_file"]).exists():
            Path(dossier["raw_sources_file"]).unlink()


