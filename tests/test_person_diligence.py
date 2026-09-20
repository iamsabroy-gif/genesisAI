"""
Unit tests for Project Genesis Person Due Diligence & Educator Verification Engine.
"""

import pytest
from genesis.tools.person_diligence import person_due_diligence
from genesis.tools.registry import TOOL_MAP, TOOL_SCHEMAS
from genesis.connectors.hub import ConnectorHub
from genesis.config import RESEARCH_DIR


def test_person_due_diligence_empty_name():
    res = person_due_diligence("")
    assert "Error: Please specify the person's name" in res


def test_tool_registration():
    # Verify TOOL_MAP
    assert "person_due_diligence" in TOOL_MAP
    # Verify TOOL_SCHEMAS
    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert "person_due_diligence" in schema_names


def test_connector_hub_exposure():
    hub = ConnectorHub()
    tool_map = hub.get_active_tool_map()
    assert "person_due_diligence" in tool_map
    tool_schemas = hub.get_active_tool_schemas()
    schema_names = [s["function"]["name"] for s in tool_schemas]
    assert "person_due_diligence" in schema_names


def test_person_due_diligence_structure_and_bounds():
    # Execute due diligence with simulated input
    result = person_due_diligence(
        name="Test Educator",
        location="Kolkata",
        affiliation="Physics tutor",
        save_to_vault=True,
    )
    
    # Assert primary structure
    assert "# Educator & Due Diligence Briefing: Test Educator" in result
    assert "## 1. Triangulation & Verification Score:" in result
    assert "## 2. Professional & Academic Findings" in result
    assert "## 3. Tutoring Profiles & Reviews" in result
    assert "## 4. Public Web Mentions & Footprint" in result
    assert "## 5. Parent Safety & In-Person Verification Checklist" in result
    assert "Photo ID Verification" in result
    assert "Certificate Check" in result
    assert "Parent Reference Check" in result
    assert "First 2 Sessions Protocol" in result

    # Check vault storage
    vault_file = RESEARCH_DIR / "person_test_educator.md"
    assert vault_file.exists()
