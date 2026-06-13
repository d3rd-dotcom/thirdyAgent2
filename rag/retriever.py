"""
rag/retriever.py — Retrieval with MMR reranking for thirdyAgent2 RAG

Fixes over v1:
  - MMR double-embedding eliminated: v1 re-embedded all N candidate
    texts to get vectors for MMR, doubling the Cohere API cost.
    ChromaDB's open-source version doesn't return stored embeddings,
    but the cosine distance it returns IS derived from them. Fix:
    approximate MMR using only distances already returned by ChromaDB.
    "Pseudo-MMR" selects greedily for highest relevance (lowest distance)
    while penalising redundancy approximated by document token overlap.
    This avoids any extra API calls.
  - retrieve() returns {"chunks", "source"} — a named dict —
    so callers know *why* the list is empty ("empty_index" vs
    "no_results" vs "embed_failed").
  - fetch_k multiplier is now a named constant, not a magic 3.
"""
from __future__ import annotations

import math
import re
from typing import Optional

from config import RAG_TOP_K
from rag.embedder import embed_query
from rag.store    import query_collection, collection_stats

_FETCH_MULTIPLIER: int = 3   # fetch_k = top_k * this before MMR filtering


# ── Similarity helpers ─────────────────────────────────────────────────
def _jaccard_sim(a: str, b: str) -> float:
    """
    Token-level Jaccard similarity as a proxy for text redundancy.
    Used by pseudo-MMR to estimate how similar two chunks are to each
    other without re-embedding them.

    O(|a| + |b|) — negligible for RAG chunk sizes.
    """
    tokens_a = set(re.findall(r"\b\w+\b", a.lower()))
    tokens_b = set(re.findall(r"\b\w+\b", b.lower()))
    if not tokens_a and not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union        = tokens_a | tokens_b
    return len(intersection) / len(union)


def _pseudo_mmr(
    candidates:   list[dict],
    top_k:        int,
    lambda_param: float = 0.6,
) -> list[dict]:
    """
    Pseudo-MMR using Jaccard similarity for inter-candidate redundancy
    (avoids re-embedding candidates).

    lambda_param=1.0 → pure relevance
    lambda_param=0.0 → pure diversity
    0.6 is a good balance for RAG prompts.
    """
    if len(candidates) <= top_k:
        return candidates

    selected: list[dict]  = []
    remaining: list[dict] = list(candidates)

    while len(selected) < top_k and remaining:
        best_score: float   = float("-inf")
        best_idx:   int     = 0

        for i, cand in enumerate(remaining):
            # Relevance: ChromaDB returns cosine *distance* (0=identical, 2=opposite)
            # Convert to similarity: 1 - distance/2 keeps values in [0, 1]
            dist      = cand.get("distance", 1.0)
            relevance = 1.0 - dist / 2.0

            # Redundancy: max Jaccard similarity to already-selected chunks
            redundancy = (
                max(_jaccard_sim(cand["text"], s["text"]) for s in selected)
                if selected else 0.0
            )

            score = lambda_param * relevance - (1 - lambda_param) * redundancy
            if score > best_score:
                best_score = score
                best_idx   = i

        selected.append(remaining.pop(best_idx))

    return selected


# ── Public API ─────────────────────────────────────────────────────────
def retrieve(
    query:         str,
    top_k:         int   = RAG_TOP_K,
    source_filter: str   = "",
    use_mmr:       bool  = True,
) -> dict:
    """
    Retrieve the most relevant chunks for a natural-language query.

    FIX (v1): v1 returned a plain list; callers couldn't distinguish
    between "RAG not built", "embed failed", and "genuinely no results".

    Returns:
        {
            "chunks":  list[dict],   # may be empty
            "status":  str,          # "ok" | "empty_index" | "embed_failed" | "no_results"
            "query":   str,
        }

    Each chunk dict: {"doc_id", "text", "source", "distance", "metadata"}
    """
    if not query or not query.strip():
        return {"chunks": [], "status": "empty_query", "query": query}

    stats = collection_stats()
    if stats.get("chunk_count", 0) == 0:
        return {"chunks": [], "status": "empty_index", "query": query}

    # Embed the query
    try:
        q_vec = embed_query(query.strip())
    except Exception as e:
        print(f"  [RAG] Embed query failed: {e}")
        return {"chunks": [], "status": "embed_failed", "query": query}

    # Fetch candidate pool
    fetch_k = top_k * _FETCH_MULTIPLIER
    where   = {"source": source_filter} if source_filter else None
    candidates = query_collection(q_vec, top_k=fetch_k, where=where)

    if not candidates:
        return {"chunks": [], "status": "no_results", "query": query}

    # Rerank with pseudo-MMR (no extra API calls)
    if use_mmr and len(candidates) > top_k:
        chunks = _pseudo_mmr(candidates, top_k)
    else:
        chunks = candidates[:top_k]

    return {"chunks": chunks, "status": "ok", "query": query}


def retrieve_context_string(
    query:         str,
    top_k:         int = RAG_TOP_K,
    source_filter: str = "",
    max_chars:     int = 2000,
) -> str:
    """
    Retrieve relevant chunks and format as a context block for LLM injection.

    Returns empty string when RAG is unavailable (safe for callers to
    concatenate directly into a prompt without checking).
    Logs the reason for an empty result at DEBUG level.
    """
    result = retrieve(query, top_k=top_k, source_filter=source_filter)

    if result["status"] != "ok":
        print(f"  [RAG] Context unavailable: {result['status']}")
        return ""

    chunks = result["chunks"]
    if not chunks:
        return ""

    parts:       list[str] = ["[KNOWLEDGE BASE CONTEXT]"]
    total_chars: int       = 0

    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        text   = chunk.get("text", "")
        dist   = chunk.get("distance", 1.0)

        remaining = max_chars - total_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining] + "..."

        parts.append(f"\n[Source {i}: {source} | relevance: {1 - dist / 2:.0%}]\n{text}")
        total_chars += len(text)

    parts.append("\n[END CONTEXT]")
    return "\n".join(parts)


# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from rag.store import collection_stats as cs

    stats = cs()
    print(f"Collection: {stats}")

    if stats.get("chunk_count", 0) == 0:
        print("No chunks. Run build_rag.py first.")
    else:
        q = "What is proof of work in Bitcoin?"
        print(f"\nQuery: {q}")
        result = retrieve(q, top_k=3)
        print(f"Status: {result['status']}, chunks: {len(result['chunks'])}")
        for i, c in enumerate(result["chunks"], 1):
            print(f"  [{i}] {c['source']} dist={c['distance']:.3f}")
            print(f"       {c['text'][:100]}...")

        ctx = retrieve_context_string(q)
        print(f"\nContext string ({len(ctx)} chars):\n{ctx[:400]}...")
