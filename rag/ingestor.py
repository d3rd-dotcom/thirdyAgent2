"""
rag/ingestor.py — Document ingestion pipeline for thirdyAgent2 RAG
════════════════════════════════════════════════════════════════════
Improvements over v1:
  - Dedup guard: v1 would re-embed the exact same text on every call
    to build_rag.py (re-running is common during development).
    Now checks existing doc_ids in ChromaDB before chunking and skips
    sources whose chunks are already present (unless replace=True).
  - Per-source error isolation: v1 used a single try/except around
    the entire batch, so one bad URL aborted all subsequent sources.
    Now each source is isolated — failure appended to errors[] and
    processing continues.
  - Structured summary now includes per-source chunk counts.
  - Type hints throughout; no bare `except: pass`.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

import requests

from rag.chunker  import chunk_documents, Chunk
from rag.embedder import embed_texts
from rag.store    import upsert_chunks, delete_source, get_collection

_HEADERS = {"User-Agent": "thirdyAgent2-RAG/1.0 (knowledge indexer)"}
_TIMEOUT = 15


# ── Source loaders ─────────────────────────────────────────────────────

def _fetch_url(url: str) -> str:
    """
    Fetch URL and return plain text.
    Strips HTML/JS/CSS. Returns empty string on any error.
    """
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        text = r.text
        # Strip style and script blocks first (they contain noise)
        text = re.sub(r"<style[^>]*>.*?</style>",   " ", text, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>",  " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>",                   " ", text)
        text = re.sub(r"&[a-z]+;",                  " ", text)
        text = re.sub(r"\s{3,}",                   "\n\n", text)
        return text.strip()
    except requests.RequestException as e:
        return ""          # caller logs the error with source label
    except Exception:
        return ""


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _read_json_source(path: str, fallback_label: str) -> list[dict]:
    """
    Read a JSON file that contains either:
      - A list of {"text":..., "source":..., "metadata":...} objects
      - A single {"text":..., "source":...} object
    Returns a list of raw doc dicts ready for chunk_documents().
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [
                {
                    "text":     item.get("text", ""),
                    "source":   item.get("source", fallback_label),
                    "metadata": item.get("metadata", {}),
                }
                for item in data
                if item.get("text")
            ]
        if isinstance(data, dict) and data.get("text"):
            return [{"text": data["text"], "source": data.get("source", fallback_label), "metadata": data.get("metadata", {})}]
    except (json.JSONDecodeError, OSError) as e:
        pass
    return []


# ── Dedup helper ───────────────────────────────────────────────────────

def _existing_sources() -> set[str]:
    """
    Return the set of source labels already present in ChromaDB.
    Uses get_collection().get() with limit to avoid loading all vectors.
    Returns empty set if ChromaDB is unavailable.
    """
    try:
        col = get_collection()
        # Fetch just IDs and metadata (no vectors needed)
        result = col.get(include=["metadatas"], limit=100_000)
        metas  = result.get("metadatas") or []
        return {m.get("source", "") for m in metas if m}
    except Exception:
        return set()


# ── Main pipeline ──────────────────────────────────────────────────────

def ingest_documents(
    sources:       list[dict],
    replace:       bool = False,
    show_progress: bool = True,
) -> dict:
    """
    Ingest a list of source definitions into the RAG store.

    Source dict schema:
        {
            "type":     "text" | "file" | "url" | "json",
            "content":  str            (type="text"),
            "path":     str            (type="file" or "json"),
            "url":      str            (type="url"),
            "source":   str,           # stable identifier / display label
            "metadata": dict,          # optional extra fields stored with chunks
        }

    Args:
        sources:       Sources to ingest.
        replace:       Delete existing chunks for each source before ingesting.
                       If False (default), sources already in the DB are skipped.
        show_progress: Print per-source progress.

    Returns:
        {
            "total_docs":     int,
            "total_chunks":   int,
            "total_embedded": int,
            "skipped":        list[str],  # sources already in DB (replace=False)
            "errors":         list[str],
            "per_source":     {source_label: {"chunks": int}},
        }
    """
    summary: dict = {
        "total_docs":     0,
        "total_chunks":   0,
        "total_embedded": 0,
        "skipped":        [],
        "errors":         [],
        "per_source":     {},
    }

    # ── Dedup: find what's already indexed ────────────────────────────
    already_indexed: set[str] = set() if replace else _existing_sources()

    # ── Phase 1: load raw text per source ─────────────────────────────
    docs_to_chunk: list[dict] = []

    for i, src in enumerate(sources):
        src_type  = src.get("type",   "text")
        src_label = src.get("source", f"doc_{i}")
        metadata  = src.get("metadata", {})

        # Dedup check
        if src_label in already_indexed:
            summary["skipped"].append(src_label)
            if show_progress:
                print(f"  [INGEST] ({i+1}/{len(sources)}) '{src_label}' already indexed — skipping")
            continue

        if show_progress:
            print(f"  [INGEST] ({i+1}/{len(sources)}) Loading '{src_label}' ({src_type})...")

        # Delete old version if replace=True
        if replace and src_label in _existing_sources():
            deleted = delete_source(src_label)
            if show_progress and deleted:
                print(f"  [INGEST]   → Deleted {deleted} old chunks for '{src_label}'")

        # Load text — each branch is independently try/except isolated
        raw_text = ""
        extra_docs: list[dict] = []

        try:
            if src_type == "text":
                raw_text = src.get("content", "")
            elif src_type == "file":
                raw_text = _read_file(src.get("path", ""))
                if not raw_text:
                    raise ValueError(f"File empty or unreadable: {src.get('path')}")
            elif src_type == "url":
                raw_text = _fetch_url(src.get("url", ""))
                if not raw_text:
                    raise ValueError(f"URL returned empty content: {src.get('url','')[:80]}")
                time.sleep(0.5)   # polite crawl delay
            elif src_type == "json":
                extra_docs = _read_json_source(src.get("path", ""), src_label)
                if not extra_docs:
                    raise ValueError(f"JSON file empty or unreadable: {src.get('path')}")
            else:
                raise ValueError(f"Unknown source type: {src_type!r}")
        except Exception as exc:
            err_msg = f"{src_label}: {exc}"
            summary["errors"].append(err_msg)
            if show_progress:
                print(f"  [INGEST]   ❌ {err_msg}")
            continue  # FIX: continue to next source, don't abort all

        # Normalise: either raw_text or extra_docs (from JSON)
        if extra_docs:
            for d in extra_docs:
                d.setdefault("metadata", {}).update(metadata)
            docs_to_chunk.extend(extra_docs)
            summary["total_docs"] += len(extra_docs)
        elif raw_text and raw_text.strip():
            docs_to_chunk.append({
                "text":     raw_text,
                "source":   src_label,
                "metadata": metadata,
            })
            summary["total_docs"] += 1
        else:
            summary["errors"].append(f"{src_label}: empty after loading")
            if show_progress:
                print(f"  [INGEST]   ⚠️  '{src_label}' produced empty text — skipping")

    if not docs_to_chunk:
        if show_progress:
            print("  [INGEST] Nothing to process after dedup/error filtering.")
        return summary

    # ── Phase 2: chunk ────────────────────────────────────────────────
    if show_progress:
        print(f"\n  [INGEST] Chunking {len(docs_to_chunk)} documents...")

    all_chunks: list[Chunk] = chunk_documents(docs_to_chunk)
    summary["total_chunks"] = len(all_chunks)

    if show_progress:
        print(f"  [INGEST] Created {len(all_chunks)} chunks")

    if not all_chunks:
        return summary

    # ── Phase 3: embed ────────────────────────────────────────────────
    if show_progress:
        print(f"\n  [INGEST] Embedding {len(all_chunks)} chunks...")

    texts:      list[str]           = [c.text for c in all_chunks]
    embeddings: list[list[float]]   = embed_texts(texts, input_type="search_document", show_progress=show_progress)
    summary["total_embedded"] = len(embeddings)

    # ── Phase 4: upsert ───────────────────────────────────────────────
    if show_progress:
        print(f"\n  [INGEST] Storing {len(all_chunks)} chunks in ChromaDB...")

    upserted = upsert_chunks(all_chunks, embeddings)

    # Per-source counts for the summary
    for chunk in all_chunks:
        src = chunk.source
        summary["per_source"].setdefault(src, {"chunks": 0})
        summary["per_source"][src]["chunks"] += 1

    if show_progress:
        print(f"  [INGEST] ✅ Stored {upserted} chunks\n")

    return summary


# ── CLI quick test ────────────────────────────────────────────────────
if __name__ == "__main__":
    test_sources = [
        {
            "type":    "text",
            "source":  "test_bitcoin",
            "content": (
                "Bitcoin uses proof-of-work to secure the blockchain. "
                "Miners compete to solve a cryptographic puzzle. "
                "The first miner to solve it adds the next block and earns a reward. "
                "This mechanism makes altering past blocks computationally expensive, "
                "providing immutability and security against double-spending attacks."
            ),
        },
    ]
    result = ingest_documents(test_sources)
    print(f"Result: {result}")
