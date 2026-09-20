"""
Tests for Project Genesis Sovereign Skills Registry, Slash Autocomplete, and File/Folder Ingestion Engine.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from prompt_toolkit.document import Document

from genesis.config import WORKSPACE_ROOT
from genesis.core.agent import GenesisAgent
from genesis.core.skills import (
    GENESIS_SKILLS,
    get_skills_catalog,
    format_skills_markdown,
    format_skills_table,
)
from genesis.tools.uploader import (
    clean_input_path,
    ingest_upload,
    upload_files_or_folder,
    UPLOADS_DIR,
)
from genesis.core.terminal import SlashCommandCompleter
from genesis.gui.api import GenesisDesktopApi


# =====================================================================
# 1. Skills Registry & Formatter Tests
# =====================================================================

def test_skills_catalog_structure():
    catalog = get_skills_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) >= 15
    for skill in catalog:
        assert "id" in skill
        assert "name" in skill
        assert "command" in skill
        assert "category" in skill
        assert "icon" in skill
        assert "description" in skill
        assert "tools" in skill
        assert "example" in skill


def test_skills_markdown_formatting():
    md = format_skills_markdown()
    assert "# ⚡ Genesis Sovereign Skills" in md
    assert "Deep Research" in md
    assert "Engineering" in md
    assert "Knowledge Base" in md
    assert "Multi-File & Folder Ingestion Engine" in md
    assert "/upload <path>" in md
    assert "/research" in md


def test_skills_table_generation():
    table = format_skills_table()
    assert table.title == "Genesis Sovereign Skills Catalog"
    assert len(table.columns) == 4
    assert len(table.rows) == len(GENESIS_SKILLS)


# =====================================================================
# 2. File & Folder Ingestion Engine Tests
# =====================================================================

def test_clean_input_path(tmp_path):
    # Test path with quotes and spaces
    sample_file = tmp_path / "My Document.txt"
    sample_file.write_text("test")

    cleaned = clean_input_path(f"'{str(sample_file)}'")
    assert cleaned == sample_file.resolve()

    # Test escaped spaces
    escaped_str = str(tmp_path) + "/My\\ Document.txt"
    cleaned_escaped = clean_input_path(escaped_str)
    assert cleaned_escaped == sample_file.resolve()


def test_ingest_single_file(tmp_path, monkeypatch):
    test_file = tmp_path / "notes.txt"
    test_file.write_text("Important notes for testing")

    # Mock vault_index_file to avoid side effects
    mock_vault_index = MagicMock(return_value={"status": "indexed"})
    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", mock_vault_index)

    result = ingest_upload(str(test_file), copy_to_workspace=True)

    assert result["status"] == "ok"
    assert result["is_folder"] is False
    assert result["target_name"] == "notes.txt"
    assert result["indexed_count"] == 1
    assert "✅ Ingested file: 'notes.txt'" in result["summary"]
    mock_vault_index.assert_called_once()

    # Clean up copied file in UPLOADS_DIR
    copied_dest = UPLOADS_DIR / "notes.txt"
    if copied_dest.exists():
        copied_dest.unlink()


def test_ingest_pdf_file(tmp_path, monkeypatch):
    test_pdf = tmp_path / "research.pdf"
    test_pdf.write_text("%PDF-1.4 dummy content")

    mock_convert = MagicMock(return_value="research.md")
    mock_vault_index = MagicMock(return_value={"status": "indexed"})
    monkeypatch.setattr("genesis.tools.uploader.convert_pdf_to_markdown", mock_convert)
    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", mock_vault_index)

    result = ingest_upload(str(test_pdf), copy_to_workspace=True)

    assert result["status"] == "ok"
    assert result["converted_count"] == 1
    mock_convert.assert_called_once()
    mock_vault_index.assert_called_once()

    # Clean up
    for fname in ["research.pdf", "research.md"]:
        f = UPLOADS_DIR / fname
        if f.exists():
            f.unlink()


def test_ingest_directory(tmp_path, monkeypatch):
    source_dir = tmp_path / "project_docs"
    source_dir.mkdir()
    (source_dir / "doc1.md").write_text("# Doc 1")
    (source_dir / "code.py").write_text("print('hello')")
    sub_dir = source_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "sub_doc.txt").write_text("Sub document")

    # Hidden directory should be ignored
    git_dir = source_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")

    mock_vault_index = MagicMock(return_value={"status": "indexed"})
    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", mock_vault_index)

    result = ingest_upload(str(source_dir), copy_to_workspace=True)

    assert result["status"] == "ok"
    assert result["is_folder"] is True
    assert result["target_name"] == "project_docs"
    assert result["total_scanned"] == 3
    assert result["indexed_count"] == 3
    assert "📁 Ingested folder: 'project_docs'" in result["summary"]

    # Clean up
    dest_dir = UPLOADS_DIR / "project_docs"
    if dest_dir.exists():
        import shutil
        shutil.rmtree(dest_dir)


def test_ingest_nonexistent_path():
    result = ingest_upload("/path/that/definitely/does/not/exist_12345")
    assert result["status"] == "error"
    assert "does not exist on disk" in result["message"]


def test_upload_files_or_folder_tool(tmp_path, monkeypatch):
    test_file = tmp_path / "data.csv"
    test_file.write_text("col1,col2\n1,2")

    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", MagicMock())
    summary = upload_files_or_folder(str(test_file))

    assert "✅ Ingested file: 'data.csv'" in summary

    # Clean up
    dest = UPLOADS_DIR / "data.csv"
    if dest.exists():
        dest.unlink()


# =====================================================================
# 3. Slash Command Completer Tests
# =====================================================================

def test_slash_command_completer():
    completer = SlashCommandCompleter()

    # When typing '/' -> should list all slash commands
    doc = Document("/", 1)
    completions = list(completer.get_completions(doc, None))
    names = [c.text for c in completions]
    assert "/skills" in names
    assert "/upload" in names
    assert "/research" in names
    assert "/swarm" in names
    assert "/models" in names
    assert "/status" in names

    # When typing '/up' -> should match '/upload'
    doc_up = Document("/up", 3)
    completions_up = list(completer.get_completions(doc_up, None))
    assert len(completions_up) == 1
    assert completions_up[0].text == "/upload"

    # When typing regular text without slash -> no completions
    doc_regular = Document("hello world", 11)
    completions_regular = list(completer.get_completions(doc_regular, None))
    assert len(completions_regular) == 0


# =====================================================================
# 4. Desktop GUI API Integration Tests
# =====================================================================

def test_gui_api_get_skills():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    skills = api.get_skills()
    assert isinstance(skills, list)
    assert len(skills) >= 15
    assert any(s["id"] == "research_swarm" for s in skills)
    assert any(s["id"] == "file_upload" for s in skills)


def test_gui_api_upload_path(tmp_path, monkeypatch):
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)

    test_file = tmp_path / "test_api_upload.txt"
    test_file.write_text("Sample file for GUI upload")

    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", MagicMock())
    result = api.upload_path(str(test_file))

    assert result["status"] == "ok"
    assert "✅ Ingested file" in result["summary"]

    # Clean up
    dest = UPLOADS_DIR / "test_api_upload.txt"
    if dest.exists():
        dest.unlink()


def test_gui_api_send_prompt_skills_intercept():
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    # Calling send_prompt with "/skills" should intercept immediately
    res = api.send_prompt("/skills")

    assert res["status"] == "completed"
    assert "Genesis Sovereign Skills" in res["response"]

    # Verify event emission occurred
    assert mock_window.evaluate_js.called
    emitted_js = mock_window.evaluate_js.call_args[0][0]
    assert "task_completed" in emitted_js
    assert "Genesis Sovereign Skills" in emitted_js


def test_gui_api_send_prompt_upload_intercept(tmp_path, monkeypatch):
    agent = GenesisAgent()
    api = GenesisDesktopApi(agent=agent)
    mock_window = MagicMock()
    api.set_window(mock_window)

    test_file = tmp_path / "gui_upload_intercept.txt"
    test_file.write_text("Hello intercept")

    monkeypatch.setattr("genesis.tools.uploader.vault_index_file", MagicMock())
    res = api.send_prompt(f"/upload {str(test_file)}")

    assert res["status"] == "completed"
    assert "Ingested file" in res["response"]

    assert mock_window.evaluate_js.called
    emitted_js = mock_window.evaluate_js.call_args[0][0]
    assert "task_completed" in emitted_js
    assert "Ingested file" in emitted_js

    # Clean up
    dest = UPLOADS_DIR / "gui_upload_intercept.txt"
    if dest.exists():
        dest.unlink()
