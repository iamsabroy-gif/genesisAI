"""
Project Genesis: PDF to Markdown Converter & Ingestion Engine.
Converts any PDF document into clean, structured Markdown prior to analysis.
"""

import os
import re
import shlex
from pathlib import Path
from typing import Optional, List, Tuple

import pypdf
from genesis.config import DOCUMENTS_DIR, WORKSPACE_ROOT


def clean_pdf_text(text: str) -> str:
    """Normalize whitespace, remove hyphenated line breaks, and retain structure."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Fix hyphenation at line breaks (e.g. "connec-\ntion" -> "connection")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Normalize multiple newlines (more than 2 into 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing/leading spaces on lines
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def convert_pdf_to_markdown(pdf_path: str, output_path: str = "") -> str:
    """
    Convert a PDF file into a structured Markdown document.

    Args:
        pdf_path: Path to the target PDF file (absolute, relative, or home-relative).
        output_path: Optional destination Markdown file path. Defaults to <pdf_stem>.md.

    Returns:
        Status message with the path to the converted Markdown file and brief summary.
    """
    path = Path(os.path.expanduser(pdf_path.strip().strip("'\"")))
    if not path.is_absolute():
        path = (WORKSPACE_ROOT / path).resolve()

    if not path.exists():
        return f"Error: PDF file not found at '{pdf_path}'."
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return f"Error: Path '{pdf_path}' is not a valid PDF file."

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as e:
        return f"Error: Failed to read PDF file '{pdf_path}': {e}"

    total_pages = len(reader.pages)
    if total_pages == 0:
        return f"Warning: PDF file '{pdf_path}' contains 0 pages."

    # Extract Document Metadata
    meta = reader.metadata or {}
    title = meta.get("/Title") or path.stem.replace("_", " ").title()
    author = meta.get("/Author") or "Unknown"

    markdown_blocks = [
        f"# {title}\n",
        f"**Source PDF**: `{path}`  ",
        f"**Author**: {author} | **Pages**: {total_pages}\n",
        "---\n",
    ]

    total_chars = 0
    for idx, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception as err:
            raw_text = f"[Error extracting text from page {idx}: {err}]"

        cleaned = clean_pdf_text(raw_text)
        total_chars += len(cleaned)

        markdown_blocks.append(f"## Page {idx}\n")
        if cleaned:
            markdown_blocks.append(f"{cleaned}\n")
        else:
            markdown_blocks.append("*[Page contains no extractable text or is image-based]*\n")

    full_markdown = "\n".join(markdown_blocks)

    # Determine output file location
    if output_path and output_path.strip():
        out_file = Path(os.path.expanduser(output_path.strip().strip("'\"")))
        if not out_file.is_absolute():
            out_file = (WORKSPACE_ROOT / out_file).resolve()
    else:
        # Default: try saving adjacent to the PDF
        out_file = path.with_suffix(".md")

    # If adjacent directory is not writable, fallback to ~/.genesis/documents/
    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(full_markdown, encoding="utf-8")
    except (PermissionError, OSError):
        out_file = DOCUMENTS_DIR / f"{path.stem}.md"
        out_file.write_text(full_markdown, encoding="utf-8")

    return (
        f"Successfully converted PDF to Markdown:\n"
        f"- Source: `{path}`\n"
        f"- Markdown File: `{out_file}`\n"
        f"- Pages: {total_pages} | Total Characters: {total_chars}"
    )


def extract_pdf_markdown_content(pdf_path: str, output_path: str = "") -> Tuple[str, Path, int]:
    """
    Convert PDF to Markdown and return (markdown_text, output_file_path, total_pages).
    """
    path = Path(os.path.expanduser(pdf_path.strip().strip("'\"")))
    if not path.is_absolute():
        path = (WORKSPACE_ROOT / path).resolve()

    if not path.exists() or path.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"PDF file not found or invalid: {pdf_path}")

    reader = pypdf.PdfReader(str(path))
    total_pages = len(reader.pages)
    meta = reader.metadata or {}
    title = meta.get("/Title") or path.stem.replace("_", " ").title()
    author = meta.get("/Author") or "Unknown"

    markdown_blocks = [
        f"# {title}\n",
        f"**Source PDF**: `{path}`  ",
        f"**Author**: {author} | **Pages**: {total_pages}\n",
        "---\n",
    ]

    for idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned = clean_pdf_text(raw_text)
        markdown_blocks.append(f"## Page {idx}\n")
        if cleaned:
            markdown_blocks.append(f"{cleaned}\n")
        else:
            markdown_blocks.append("*[Page contains no extractable text or is image-based]*\n")

    full_markdown = "\n".join(markdown_blocks)

    if output_path and output_path.strip():
        out_file = Path(os.path.expanduser(output_path.strip().strip("'\"")))
        if not out_file.is_absolute():
            out_file = (WORKSPACE_ROOT / out_file).resolve()
    else:
        out_file = path.with_suffix(".md")

    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(full_markdown, encoding="utf-8")
    except (PermissionError, OSError):
        out_file = DOCUMENTS_DIR / f"{path.stem}.md"
        out_file.write_text(full_markdown, encoding="utf-8")

    return full_markdown, out_file, total_pages


def detect_pdf_files_in_text(text: str) -> List[Path]:
    """Find any referenced PDF file paths that exist on disk."""
    found_paths = []
    # Regex to capture potential file paths ending in .pdf (including quoted or unquoted)
    candidates = re.findall(r'(?:["\']([^"\']+\.pdf)["\']|([~/\.\w-]+\.pdf))', text, re.IGNORECASE)

    for c1, c2 in candidates:
        raw_candidate = c1 or c2
        if not raw_candidate:
            continue
        try:
            p = Path(os.path.expanduser(raw_candidate.strip()))
            if not p.is_absolute():
                p = (WORKSPACE_ROOT / p).resolve()
            if p.exists() and p.is_file() and p.suffix.lower() == ".pdf":
                if p not in found_paths:
                    found_paths.append(p)
        except Exception:
            continue

    return found_paths


def auto_convert_prompt_pdfs(user_prompt: str) -> Tuple[str, List[Path]]:
    """
    Check if user prompt mentions existing PDF files.
    If so, converts each to Markdown and injects the converted document information into the prompt.
    """
    pdf_paths = detect_pdf_files_in_text(user_prompt)
    if not pdf_paths:
        return user_prompt, []

    converted_files = []
    injected_sections = []

    for pdf_path in pdf_paths:
        try:
            content, md_path, pages = extract_pdf_markdown_content(str(pdf_path))
            converted_files.append(md_path)

            # Cap embedded preview if document is very long, to respect 16 GB Apple Silicon context
            max_preview = 4000
            if len(content) > max_preview:
                preview = content[:max_preview] + f"\n\n... [Truncated {len(content) - max_preview} chars. Complete Markdown file available at '{md_path}']"
            else:
                preview = content

            section = (
                f"[PDF Auto-Converted to Markdown: '{pdf_path.name}']\n"
                f"- Original PDF: `{pdf_path}`\n"
                f"- Converted Markdown: `{md_path}`\n"
                f"- Pages: {pages}\n\n"
                f"```markdown\n{preview}\n```"
            )
            injected_sections.append(section)
        except Exception as e:
            injected_sections.append(f"[Failed to auto-convert '{pdf_path}': {e}]")

    augmented = "\n\n".join(injected_sections) + f"\n\n[User Request]:\n{user_prompt}"
    return augmented, converted_files
