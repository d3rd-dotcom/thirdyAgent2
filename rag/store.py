"""
rag/store.py — ChromaDB vector store for thirdyAgent2 RAG

Fixes over v1:
  - Thread safety: v1 had a shared _collection global mutated by
    multiple Flask worker threads without a lock. ChromaDB's Python
    client is not documented as thread-safe for the get_or_create path.
    Fix: a module-level threading.Lock guards client/collection init.
  - Alignment guard: upsert_chunks() now validates len(chunks) ==
    len(embeddings) before sending to ChromaDB — a mismatch silently
    truncates or raises an opaque error in v1.
  - collection_stats() wraps col.count() in its own try/except so a
    ChromaDB internal error returns {"status": "error"} rather than
    propagating an unhandled exception into the skill handler.
  - delete_source() now returns the number of deleted items, not 1/0.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from config import CHROMA_PERSIST_DIR

if TYPE_CHECKING:
    from rag.chunker import Chunk

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False

COLLECTION_NAME = "thirdyagent2_knowledge"

# ── Thread-safe singleton ──────────────────────────────────────────────
_lock:       threading.Lock                  = threading.Lock()
_client:     "chromadb.PersistentClient | None" = None
_collection: "chromadb.Collection | None"   = None


def _ensure_chroma() -> None:
    if not _CHROMA_AVAILABLE:
        raise ImportError(
            "chromadb not installed.\n"
            "Run: pip install chromadb==0.4.24 --break-system-packages"
        )


def get_client() -> "chromadb.PersistentClient":
    """Return the ChromaDB persistent client (created once, thread-safe)."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:         # double-checked locking
                _ensure_chroma()
                persist_dir = str(Path(CHROMA_PERSIST_DIR))
                Path(persist_dir).mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(anonymized_telemetry=False),
                )
    return _client


def get_collection() -> "chromadb.Collection":
    """Return the knowledge collection (created once, thread-safe)."""
    global _collection
    if _collection is None:
        with _lock:
            if _collection is None:     # double-checked locking
                _collection = get_client().get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
    return _collection


def upsert_chunks(chunks: list["Chunk"], embeddings: list[list[float]]) -> int:
    """
    Upsert chunks + pre-computed embeddings into ChromaDB.
    Idempotent: running twice with the same doc_ids is safe.

    FIX: validates alignment before the ChromaDB call.

    Returns:
        Number of chunks upserted.

    Raises:
        ValueError if len(chunks) != len(embeddings).
    """
    if not chunks:
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk/embedding mismatch: {len(chunks)} chunks but "
            f"{len(embeddings)} embeddings. This is a caller bug."
        )

    col = get_collection()
    col.upsert(
        ids        = [c.doc_id   for c in chunks],
        embeddings = embeddings,
        documents  = [c.text     for c in chunks],
        metadatas  = [c.metadata for c in chunks],
    )
    return len(chunks)


def query_collection(
    query_embedding: list[float],
    top_k:           int = 4,
    where:           "dict | None" = None,
) -> list[dict]:
    """
    Query by embedding vector.

    Returns list of dicts ordered by similarity (closest first):
      {"doc_id", "text", "source", "distance", "metadata"}

    Returns empty list (not an exception) on any ChromaDB error.
    """
    col = get_collection()

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results":        top_k,
        "include":          ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    try:
        results = col.query(**kwargs)
    except Exception as e:
        print(f"  [RAG STORE] Query failed: {e}")
        return []

    hits: list[dict] = []
    for doc_id, text, meta, dist in zip(
        results.get("ids",       [[]])[0],
        results.get("documents", [[]])[0],
        results.get("metadatas", [[]])[0],
        results.get("distances", [[]])[0],
    ):
        hits.append({
            "doc_id":   doc_id,
            "text":     text,
            "source":   meta.get("source", "unknown") if meta else "unknown",
            "distance": round(float(dist), 4),
            "metadata": meta or {},
        })

    return hits


def collection_stats() -> dict:
    """
    FIX: v1 let col.count() propagate exceptions into skill handlers.
    Now always returns a dict — callers never need to catch.
    """
    if not _CHROMA_AVAILABLE:
        return {"status": "chromadb_not_installed", "chunk_count": 0}
    try:
        col         = get_collection()
        chunk_count = col.count()
        return {
            "collection":  COLLECTION_NAME,
            "chunk_count": chunk_count,
            "persist_dir": CHROMA_PERSIST_DIR,
            "status":      "ready" if chunk_count > 0 else "empty",
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "chunk_count": 0}


def delete_source(source: str) -> int:
    """
    Delete all chunks for a source document.

    FIX: v1 returned 1 (success) or 0 (failure) regardless of how many
    chunks were deleted. Now returns the pre-delete chunk count for that
    source so callers know what was removed.

    Returns:
        Number of chunks that were present before deletion (may be 0).
    """
    try:
        col = get_collection()
        # Count before deletion
        before = col.get(where={"source": source})
        n      = len(before.get("ids", []))
        if n > 0:
            col.delete(where={"source": source})
        return n
    except Exception as e:
        print(f"  [RAG STORE] delete_source('{source}') failed: {e}")
        return 0


# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--stress" in sys.argv:
        # Thread-safety smoke test: concurrent collection_stats() calls
        import concurrent.futures, time

        print("Stress test: 20 concurrent collection_stats() calls...")
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(collection_stats) for _ in range(20)]
            results_s = [f.result() for f in futs]
        elapsed = time.time() - t0
        errors  = [r for r in results_s if r.get("status") == "error"]
        print(f"  Completed in {elapsed:.2f}s | Errors: {len(errors)}/20")
        if errors:
            print(f"  Error: {errors[0]}")
    else:
        stats = collection_stats()
        print(f"Collection stats: {stats}")
