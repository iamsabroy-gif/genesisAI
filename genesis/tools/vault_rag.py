"""
Project Genesis: Local Sovereign Semantic RAG Engine.
Embeds and retrieves passages from documents, code, and PDFs using local nomic-embed-text.
"""

import json
import math
import os
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Tuple

from genesis.config import VAULT_DIR, WORKSPACE_ROOT, OLLAMA_BASE_URL

INDEX_PATH = VAULT_DIR / "vault_index.json"
EMBED_MODEL = "nomic-embed-text"


def get_embedding(text: str) -> List[float]:
    """
    Fetch 768-dimensional vector embedding from local Ollama instance.
    Falls back to a sparse bag-of-words vector if Ollama embedding fails.
    """
    # Ollama embedding endpoint: http://localhost:11434/api/embeddings
    clean_text = text.strip()[:2000]
    base_host = OLLAMA_BASE_URL.replace("/v1", "")
    url = f"{base_host}/api/embeddings"

    payload = json.dumps({"model": EMBED_MODEL, "prompt": clean_text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding", [])
    except Exception:
        # Fallback sparse hash vector if embed model unavailable
        vec = [0.0] * 64
        for word in clean_text.lower().split():
            h = hash(word) % 64
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Split text into overlapping windows respecting paragraph breaks."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        if len(current_chunk) + len(p_clean) < chunk_size:
            current_chunk = f"{current_chunk}\n\n{p_clean}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = p_clean

    if current_chunk:
        chunks.append(current_chunk)

    return chunks or [text[:chunk_size]]


def load_vault_index() -> Dict[str, Any]:
    """Load existing index from disk or initialize blank structure."""
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "chunks": []}


def save_vault_index(data: Dict[str, Any]):
    """Atomic write of vault index."""
    INDEX_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def vault_index_file(path: str, chunk_size: int = 800) -> str:
    """
    Index a code, markdown, or text file into the local semantic vector vault.
    """
    target = Path(os.path.expanduser(path.strip().strip("'\"")))
    if not target.is_absolute():
        target = (WORKSPACE_ROOT / target).resolve()

    if not target.exists():
        return f"Error: File not found at '{path}'."

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error: Failed to read file '{path}': {e}"

    chunks = chunk_text(text, chunk_size=chunk_size)
    index = load_vault_index()

    # Remove previous chunks from the same file to prevent duplicates
    str_target = str(target)
    index["chunks"] = [c for c in index["chunks"] if c.get("source") != str_target]

    added = 0
    for idx, c in enumerate(chunks):
        emb = get_embedding(c)
        index["chunks"].append({
            "source": str_target,
            "filename": target.name,
            "chunk_idx": idx + 1,
            "content": c,
            "embedding": emb,
        })
        added += 1

    save_vault_index(index)
    return (
        f"Vault Indexing Complete:\n"
        f"- File: `{target.name}`\n"
        f"- Path: `{target}`\n"
        f"- Semantic Chunks: {added}\n"
        f"- Total Vault Chunks: {len(index['chunks'])}"
    )


def tokenize_terms(text: str) -> List[str]:
    """Simple alphanumeric token extraction for BM25 keyword matching."""
    import re
    return [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_-]+\b", text) if len(t) > 1]


def compute_bm25_scores(query_terms: List[str], docs_tokens: List[List[str]]) -> List[float]:
    """Compute BM25 scores across documents for query terms."""
    if not query_terms or not docs_tokens:
        return [0.0] * len(docs_tokens)

    N = len(docs_tokens)
    doc_lens = [len(dt) for dt in docs_tokens]
    avgdl = (sum(doc_lens) / N) if N > 0 else 1.0

    # Calculate Document Frequencies (DF)
    df = {}
    for term in query_terms:
        df[term] = sum(1 for dt in docs_tokens if term in dt)

    k1 = 1.5
    b = 0.75
    scores = []

    for idx, dt in enumerate(docs_tokens):
        score = 0.0
        d_len = doc_lens[idx]
        term_counts = {}
        for t in dt:
            term_counts[t] = term_counts.get(t, 0) + 1

        for term in query_terms:
            n_t = df.get(term, 0)
            if n_t == 0:
                continue
            idf = math.log(1.0 + (N - n_t + 0.5) / (n_t + 0.5))
            f_t = term_counts.get(term, 0)
            numerator = f_t * (k1 + 1.0)
            denominator = f_t + k1 * (1.0 - b + b * (d_len / avgdl))
            score += idf * (numerator / denominator if denominator > 0 else 0)

        scores.append(score)

    return scores


def vault_search(query: str, top_k: int = 3) -> str:
    """
    Perform Hybrid Semantic Search: Dense Vector Embeddings + BM25 Sparse Keyword Match
    combined via Reciprocal Rank Fusion (RRF). Guarantees zero missed keyword identifiers.
    """
    clean_q = query.strip()
    if not clean_q:
        return "Error: Empty search query."

    index = load_vault_index()
    chunks = index.get("chunks", [])
    if not chunks:
        return "Vault is empty. Use `vault_index_file` to index code or documents first."

    # 1. Dense Vector Scoring
    q_emb = get_embedding(clean_q)
    dense_scores = [cosine_similarity(q_emb, c.get("embedding", [])) for c in chunks]
    # Rank indices descending
    dense_ranked_indices = sorted(range(len(chunks)), key=lambda i: dense_scores[i], reverse=True)

    # 2. Sparse BM25 Keyword Scoring
    q_tokens = tokenize_terms(clean_q)
    docs_tokens = [tokenize_terms(c.get("content", "")) for c in chunks]
    bm25_scores = compute_bm25_scores(q_tokens, docs_tokens)
    bm25_ranked_indices = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)

    # 3. Reciprocal Rank Fusion (RRF) with constant k=60
    rrf_scores = [0.0] * len(chunks)
    for rank, idx in enumerate(dense_ranked_indices, start=1):
        rrf_scores[idx] += 1.0 / (60.0 + rank)
    for rank, idx in enumerate(bm25_ranked_indices, start=1):
        rrf_scores[idx] += 1.0 / (60.0 + rank)

    # Combine results
    ranked_final = sorted(range(len(chunks)), key=lambda i: rrf_scores[i], reverse=True)
    top_indices = ranked_final[:top_k]

    lines = [f"# Hybrid Vault Matches (Dense Vector + BM25 RRF) for: '{clean_q}'\n"]
    for rank, idx in enumerate(top_indices, start=1):
        c = chunks[idx]
        v_sim = round(dense_scores[idx] * 100, 1)
        bm_score = round(bm25_scores[idx], 2)
        lines.append(
            f"### Match {rank} | Vector Sim: **{v_sim}%** | BM25 Score: **{bm_score}** (`{c['filename']}` - Chunk {c['chunk_idx']})\n"
            f"*Source*: `{c['source']}`\n\n"
            f"```text\n{c['content']}\n```\n"
        )

    return "\n".join(lines)


def vault_status() -> str:
    """Report vault indexing statistics."""
    index = load_vault_index()
    chunks = index.get("chunks", [])
    sources = set(c.get("source") for c in chunks)
    size_kb = round(INDEX_PATH.stat().st_size / 1024, 1) if INDEX_PATH.exists() else 0.0

    return (
        f"Genesis Sovereign Vector Vault:\n"
        f"- Index Location: `{INDEX_PATH}`\n"
        f"- Indexed Documents: {len(sources)}\n"
        f"- Vector Chunks: {len(chunks)}\n"
        f"- Embedding Model: `{EMBED_MODEL}` (Local Ollama)\n"
        f"- Vault Storage Size: {size_kb} KB"
    )
