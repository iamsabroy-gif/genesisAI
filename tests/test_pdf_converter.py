"""
Unit tests for Project Genesis PDF to Markdown Converter & Ingestion Engine.
"""

import os
from pathlib import Path
import pytest
import pypdf

from genesis.tools.pdf_converter import (
    clean_pdf_text,
    convert_pdf_to_markdown,
    extract_pdf_markdown_content,
    detect_pdf_files_in_text,
    auto_convert_prompt_pdfs,
)
from genesis.tools.registry import TOOL_MAP, TOOL_SCHEMAS


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a temporary multi-page PDF for testing."""
    pdf_path = tmp_path / "sample_doc.pdf"
    writer = pypdf.PdfWriter()
    # Add page 1 and page 2
    p1 = writer.add_blank_page(width=300, height=300)
    p2 = writer.add_blank_page(width=300, height=300)

    # Note: blank pages have empty text, but test PDF structure
    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path


def test_clean_pdf_text():
    raw = "Multi-\nline word\x00 and   spaces\n\n\n\nNew paragraph."
    cleaned = clean_pdf_text(raw)
    assert "\x00" not in cleaned
    assert "Multiline" in cleaned
    assert "New paragraph." in cleaned


def test_convert_pdf_to_markdown(sample_pdf: Path, tmp_path: Path):
    out_md = tmp_path / "output.md"
    result = convert_pdf_to_markdown(str(sample_pdf), output_path=str(out_md))

    assert "Successfully converted PDF to Markdown" in result
    assert out_md.exists()

    content = out_md.read_text(encoding="utf-8")
    assert "## Page 1" in content
    assert "## Page 2" in content
    assert "Source PDF" in content


def test_convert_pdf_invalid_path():
    result = convert_pdf_to_markdown("non_existent_file.pdf")
    assert "Error: PDF file not found" in result


def test_detect_pdf_files_in_text(sample_pdf: Path):
    text = f"Please analyze {sample_pdf} and check findings."
    found = detect_pdf_files_in_text(text)
    assert len(found) == 1
    assert found[0] == sample_pdf


def test_auto_convert_prompt_pdfs(sample_pdf: Path):
    prompt = f"Here is the report {sample_pdf}. What is the summary?"
    augmented, converted = auto_convert_prompt_pdfs(prompt)

    assert len(converted) == 1
    assert "[PDF Auto-Converted to Markdown:" in augmented
    assert "## Page 1" in augmented
    assert "[User Request]:" in augmented


def test_tool_registry_registration():
    assert "convert_pdf_to_markdown" in TOOL_MAP
    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    assert "convert_pdf_to_markdown" in schema_names
