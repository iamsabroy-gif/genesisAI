"""
Tests for Project Genesis Mentorship Memory.
Authored by Test-Harness (Staff QA Lead).
"""

import tempfile
from genesis.memory.mentorship import MentorshipMemory


def test_record_and_retrieve_heuristic():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        mem = MentorshipMemory(db_path=tmp.name)
        
        mem.record_heuristic(
            domain="python",
            preferred="use polars with explicit type annotations",
            forbidden="do not use pandas",
            rationale="polars is faster and memory efficient on Mac",
        )

        results = mem.retrieve_heuristics("write a python data pipeline")
        assert len(results) >= 1
        assert results[0]["domain"] == "python"
        assert "polars" in results[0]["preferred"]

        context_str = mem.format_heuristics_context("python script")
        assert "Mentorship Memory" in context_str
        assert "polars" in context_str
