"""
rag/rag_skill.py — knowledge_query and rag_status skills (FREE)
════════════════════════════════════════════════════════════════
Improvements over v1:
  - Lazy import guard: v1 imported rag.store at module load time,
    which raised ImportError if chromadb wasn't installed yet and
    crashed ALL skill loading in agent.py. Now imports only when
    the skill is actually called.
  - Graceful degradation: if chromadb is missing, skills return a
    helpful install message rather than a 500 error.
  - Uses the new structured retrieve() return dict (status field)
    so error messages are specific, not generic "no results".
  - handle_knowledge_query() is split into _do_query() helper so
    the import-guard wrapper stays clean and testable.
"""
from __future__ import annotations


def _rag_available() -> tuple[bool, str]:
    """
    Check whether the RAG stack is importable and the index is built.
    Returns (available: bool, reason: str).
    Imported lazily so agent.py loads even when chromadb is absent.
    """
    try:
        from rag.store import collection_stats
        stats = collection_stats()
        if stats.get("status") == "chromadb_not_installed":
            return False, "chromadb_not_installed"
        if stats.get("chunk_count", 0) == 0:
            return False, "empty_index"
        return True, "ok"
    except ImportError:
        return False, "chromadb_not_installed"
    except Exception as e:
        return False, f"error: {e}"


def _format_not_available(reason: str, skill_name: str) -> str:
    """Human-friendly message when RAG is unavailable."""
    if reason == "chromadb_not_installed":
        return (
            f"📚 [{skill_name.upper()}]\n"
            "⚠️  RAG knowledge base not installed.\n"
            "    Run: pip install chromadb==0.4.24 --break-system-packages\n"
            "    Then: python build_rag.py"
        )
    if reason == "empty_index":
        return (
            f"📚 [{skill_name.upper()}]\n"
            "⚠️  Knowledge base is empty.\n"
            "    Run: python build_rag.py (takes ~5-10 minutes)\n"
            "    Topics: Bitcoin, Ethereum, Solana, Aave, Uniswap, DeFiLlama."
        )
    return (
        f"📚 [{skill_name.upper()}]\n"
        f"⚠️  Knowledge base unavailable: {reason}\n"
        "    Check rag/ module and run python build_rag.py"
    )


# ── knowledge_query ────────────────────────────────────────────────────

def _do_query(query: str, top_k: int, source_filter: str) -> dict:
    """
    Inner query logic — only reached when RAG is confirmed available.
    Separated so the outer function stays a clean guard + dispatch.
    """
    from rag.retriever import retrieve
    from rag.store     import collection_stats

    result = retrieve(query, top_k=top_k, source_filter=source_filter)
    status = result["status"]
    chunks = result["chunks"]

    stats       = collection_stats()
    chunk_count = stats.get("chunk_count", 0)

    if status != "ok" or not chunks:
        status_msg = {
            "no_results":   f"No information found for: '{query}'. Try rephrasing.",
            "embed_failed": "Embedding service unavailable. Check COHERE_KEY in .env.",
        }.get(status, f"Retrieval failed (status={status}).")

        return {
            "result": (
                f"📚 [KNOWLEDGE QUERY]\n"
                f"{status_msg}\n"
                f"Knowledge base has {chunk_count:,} indexed chunks."
            ),
            "data": {"query": query, "results": 0, "status": status},
        }

    lines = [
        f"📚 [KNOWLEDGE QUERY] — {query}",
        "─" * 42,
    ]

    for i, chunk in enumerate(chunks, 1):
        source    = chunk.get("source", "unknown")
        text      = chunk.get("text", "")
        dist      = chunk.get("distance", 1.0)
        relevance = round((1.0 - dist / 2.0) * 100)   # cosine dist → % relevance
        preview   = text[:300].strip() + ("..." if len(text) > 300 else "")

        lines.append(f"\n[{i}] 📄 {source}  (relevance: {relevance}%)\n    {preview}")

    lines.append(
        f"\n{'─'*42}\n"
        f"📊 {len(chunks)} sources | KB: {chunk_count:,} chunks\n"
        "💡 Premium skills (market_signal, portfolio_analyzer)\n"
        "   also use this knowledge base for enriched AI analysis."
    )

    return {
        "result": "\n".join(lines),
        "data": {
            "query":       query,
            "results":     len(chunks),
            "chunk_count": chunk_count,
            "sources": [
                {
                    "doc_id":    c.get("doc_id"),
                    "source":    c.get("source"),
                    "relevance": round((1.0 - c.get("distance", 1.0) / 2.0) * 100),
                    "preview":   c.get("text", "")[:100],
                }
                for c in chunks
            ],
        },
    }


def handle_knowledge_query(params: dict) -> dict:
    """
    FREE: Query the thirdyAgent2 knowledge base (RAG).
    Returns cited answers from indexed DeFi/crypto/blockchain docs.

    Parameters:
        query  (str, required) — the question
        top_k  (int, default 4) — number of source chunks
        source (str, optional) — restrict to a specific document
    """
    query  = params.get("query", "").strip()
    top_k  = min(int(params.get("top_k", 4)), 8)
    source = params.get("source", "").strip()

    if not query:
        return {
            "result": (
                "📚 [KNOWLEDGE QUERY]\n"
                "Please provide a query.\n"
                'Example: {"query": "What is Aave\'s liquidation threshold?"}'
            ),
            "data": {"error": "query_required"},
        }

    available, reason = _rag_available()
    if not available:
        return {
            "result": _format_not_available(reason, "knowledge_query"),
            "data":   {"status": reason},
        }

    return _do_query(query, top_k, source)


# ── rag_status ─────────────────────────────────────────────────────────

def handle_rag_status(params: dict) -> dict:
    """
    FREE: Check RAG knowledge base health and stats.
    """
    available, reason = _rag_available()

    if not available:
        return {
            "result": _format_not_available(reason, "rag_status"),
            "data":   {"status": reason, "available": False},
        }

    # Import only when we know chromadb is present
    from rag.store    import collection_stats
    from rag.embedder import cache_stats

    db_stats    = collection_stats()
    embed_stats = cache_stats()

    return {
        "result": (
            "📚 [RAG STATUS] Knowledge base ready!\n"
            f"   Chunks    : {db_stats.get('chunk_count', 0):,}\n"
            f"   Location  : {db_stats.get('persist_dir', 'chroma_db/')}\n"
            f"   Embed cache: {embed_stats.get('entries', 0):,} vectors cached\n"
            f"   Status    : {db_stats.get('status', 'unknown')}\n"
            '   Query with: skill=knowledge_query, {"query":"..."}'
        ),
        "data": {**db_stats, "embed_cache": embed_stats, "available": True},
    }


# ── Pack registration ──────────────────────────────────────────────────
SKILLS_PACK: dict = {
    "knowledge_query": handle_knowledge_query,
    "rag_status":      handle_rag_status,
}
