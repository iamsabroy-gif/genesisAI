"""
Project Genesis: Universal File & Folder Ingestion Engine.
Allows uploading and ingesting single files or entire directory trees into the workspace
with automated PDF-to-Markdown conversion and Vector Vault semantic indexing.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from genesis.config import WORKSPACE_ROOT
from genesis.tools.pdf_converter import convert_pdf_to_markdown
from genesis.tools.vault_rag import vault_index_file

# Directory within workspace dedicated to user uploads
UPLOADS_DIR = WORKSPACE_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# File extensions supported for direct indexing into the Vector Vault
INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv",
    ".sh", ".sql", ".rs", ".go", ".c", ".cpp", ".h", ".swift",
    ".java", ".kt", ".dart", ".rb", ".php",
}


def clean_input_path(raw_path: str) -> Path:
    """Normalize and resolve paths, handling macOS drag-and-drop escapes, quotes, and tildes."""
    cleaned = raw_path.strip().strip("'\"")
    # Handle bash escaped spaces if present (e.g. My\ Documents -> My Documents)
    cleaned = cleaned.replace("\\ ", " ")
    expanded = os.path.expanduser(cleaned)
    p = Path(expanded)
    if not p.is_absolute():
        p = (WORKSPACE_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def ingest_upload(target_path_str: str, copy_to_workspace: bool = True) -> Dict[str, Any]:
    """
    Ingest a single file or an entire folder into Genesis.
    - Recursively processes files
    - Converts PDFs into structured Markdown
    - Indexes text, code, and markdown into the Sovereign Vector Vault
    - Copies files into workspace/uploads/ for active inspection
    """
    target = clean_input_path(target_path_str)

    if not target.exists():
        return {
            "status": "error",
            "message": f"Path '{target_path_str}' does not exist on disk.",
            "target": str(target),
        }

    indexed_files: List[str] = []
    converted_pdfs: List[str] = []
    copied_paths: List[str] = []
    errors: List[str] = []

    if target.is_file():
        # Process single file
        dest_file = target
        if copy_to_workspace and not str(target).startswith(str(WORKSPACE_ROOT)):
            dest_file = UPLOADS_DIR / target.name
            try:
                shutil.copy2(target, dest_file)
                copied_paths.append(str(dest_file))
            except Exception as e:
                errors.append(f"Copy error: {e}")
                dest_file = target

        # Handle PDF conversion
        if dest_file.suffix.lower() == ".pdf":
            try:
                md_path = dest_file.with_suffix(".md")
                conv_res = convert_pdf_to_markdown(str(dest_file), str(md_path))
                converted_pdfs.append(str(md_path))
                # Index the generated markdown into vault
                v_res = vault_index_file(str(md_path))
                indexed_files.append(str(md_path))
            except Exception as e:
                errors.append(f"PDF conversion error ({dest_file.name}): {e}")
        elif dest_file.suffix.lower() in INDEXABLE_EXTENSIONS:
            try:
                v_res = vault_index_file(str(dest_file))
                indexed_files.append(str(dest_file))
            except Exception as e:
                errors.append(f"Vault index error ({dest_file.name}): {e}")

        summary = (
            f"✅ Ingested file: '{target.name}'\n"
            f"• Location: {dest_file}\n"
            f"• Converted PDFs: {len(converted_pdfs)}\n"
            f"• Vault Indexed: {'Yes' if indexed_files else 'No (non-indexable format)'}"
        )
        return {
            "status": "ok",
            "is_folder": False,
            "target_name": target.name,
            "destination": str(dest_file),
            "indexed_count": len(indexed_files),
            "converted_count": len(converted_pdfs),
            "indexed_files": indexed_files,
            "converted_pdfs": converted_pdfs,
            "summary": summary,
            "errors": errors,
        }

    elif target.is_dir():
        # Process entire directory
        folder_dest = UPLOADS_DIR / target.name
        if copy_to_workspace and not str(target).startswith(str(WORKSPACE_ROOT)):
            try:
                if folder_dest.exists():
                    shutil.rmtree(folder_dest)
                shutil.copytree(target, folder_dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "node_modules"))
            except Exception as e:
                errors.append(f"Directory copy error: {e}")
                folder_dest = target
        else:
            folder_dest = target

        total_scanned = 0
        for root, dirs, files in os.walk(folder_dest):
            # Prune noisy directories
            dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"]]
            for f in files:
                total_scanned += 1
                f_path = Path(root) / f

                # Handle PDF
                if f_path.suffix.lower() == ".pdf":
                    try:
                        md_path = f_path.with_suffix(".md")
                        convert_pdf_to_markdown(str(f_path), str(md_path))
                        converted_pdfs.append(str(md_path))
                        vault_index_file(str(md_path))
                        indexed_files.append(str(md_path))
                    except Exception as e:
                        errors.append(f"PDF error ({f}): {e}")
                elif f_path.suffix.lower() in INDEXABLE_EXTENSIONS:
                    try:
                        vault_index_file(str(f_path))
                        indexed_files.append(str(f_path))
                    except Exception as e:
                        errors.append(f"Index error ({f}): {e}")

        summary = (
            f"📁 Ingested folder: '{target.name}'\n"
            f"• Destination: {folder_dest}\n"
            f"• Total files scanned: {total_scanned}\n"
            f"• Files indexed into Vector Vault: {len(indexed_files)}\n"
            f"• PDFs converted to Markdown: {len(converted_pdfs)}"
        )
        return {
            "status": "ok",
            "is_folder": True,
            "target_name": target.name,
            "destination": str(folder_dest),
            "total_scanned": total_scanned,
            "indexed_count": len(indexed_files),
            "converted_count": len(converted_pdfs),
            "indexed_files": indexed_files,
            "converted_pdfs": converted_pdfs,
            "summary": summary,
            "errors": errors,
        }

    return {
        "status": "error",
        "message": f"'{target_path_str}' is neither a regular file nor a directory.",
    }


def upload_files_or_folder(path: str) -> str:
    """Tool wrapper: Ingests files or folders, converts PDFs, and indexes into the Vector Vault."""
    res = ingest_upload(path)
    if res.get("status") == "ok":
        return res.get("summary", "Upload complete.")
    return f"Error uploading '{path}': {res.get('message', 'unknown error')}"
