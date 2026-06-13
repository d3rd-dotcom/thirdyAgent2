"""
rag/embedder.py — Cohere embedding client for thirdyAgent2 RAG

Fixes over v1:
  - Cache explosion: v1 stored ALL embeddings in a single JSON file.
    Each embed-english-v3.0 vector is 1024 floats × 8 bytes = 8 KB.
    1,000 chunks → ~8 MB JSON. 10,000 chunks → ~80 MB JSON, loaded
    entirely into memory on startup. Fix: shard by first 2 hex chars
    of the MD5 hash → 256 shard files, each small and loaded lazily.
  - Atomic cache write: v1 wrote directly to the cache file, so a
    crash mid-write produced a corrupt JSON. Fix: write to a temp
    file then os.replace() (atomic on POSIX and Windows).
  - Assert removed: v1 used `assert all(...)` which is silently
    disabled by `python -O`. Replaced with an explicit RuntimeError.
  - Retry logic: v1 only retried on the same exception type. Now
    distinguishes network errors (retry) from API errors (raise).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

from config import COHERE_KEY, RAG_EMBED_MODEL, BASE_DIR

# ── Cache configuration ────────────────────────────────────────────────
# Shard directory: chroma_db/embed_cache/<2-hex-char-prefix>/<hash>.json
# Each shard file holds ONE embedding vector (list[float]).
# Lazy load: a shard is only read when we encounter a hash with that prefix.
_CACHE_DIR  = Path(BASE_DIR) / "chroma_db" / "embed_cache"
_BATCH_SIZE = 90      # Cohere max texts per call
_RATE_DELAY = 1.2     # seconds between batches (100 calls/min limit)

# In-memory hot cache to avoid re-reading shard files within a session.
# Key: md5 hex string. Value: embedding vector.
_hot_cache: dict[str, list[float]] = {}


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _shard_path(h: str) -> Path:
    """Each hash maps to chroma_db/embed_cache/<first2>/<hash>.json"""
    return _CACHE_DIR / h[:2] / f"{h}.json"


def _read_cached(h: str) -> Optional[list[float]]:
    """Read one embedding from the hot cache or shard file."""
    if h in _hot_cache:
        return _hot_cache[h]
    p = _shard_path(h)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                vec = json.load(f)
            _hot_cache[h] = vec
            return vec
        except (json.JSONDecodeError, OSError):
            # Corrupt shard — delete it so it gets re-embedded
            p.unlink(missing_ok=True)
    return None


def _write_cached(h: str, vec: list[float]) -> None:
    """
    FIX: Atomic shard write.
    Write to a temp file in the same directory, then os.replace().
    os.replace() is atomic on both POSIX and Windows (same filesystem).
    A crash between write and replace leaves a .tmp file, not a corrupt shard.
    """
    p = _shard_path(h)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Write to sibling temp file
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(vec, f)
        os.replace(tmp, p)          # atomic rename
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _hot_cache[h] = vec


# ── API call ───────────────────────────────────────────────────────────
def _embed_batch(texts: list[str], input_type: str) -> list[list[float]]:
    """
    Call Cohere Embed v2 API for one batch.
    Distinguishes retryable network errors from non-retryable API errors.
    """
    if not COHERE_KEY:
        raise RuntimeError(
            "COHERE_KEY not set. Add it to .env.\n"
            "Get a free key at: https://dashboard.cohere.com/"
        )

    headers = {
        "Authorization": f"Bearer {COHERE_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "texts":            texts,
        "model":            RAG_EMBED_MODEL,
        "input_type":       input_type,
        "embedding_types":  ["float"],
    }

    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.cohere.com/v2/embed",
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as exc:
            # Network-level error — always retry
            last_exc = exc
            wait = 2 ** attempt
            print(f"  [EMBED] Network error (attempt {attempt+1}/3): {exc}. Retry in {wait}s...")
            time.sleep(wait)
            continue

        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 60))
            print(f"  [EMBED] Rate limited — waiting {wait}s...")
            time.sleep(wait)
            last_exc = RuntimeError(f"Rate limited (429)")
            continue

        if r.status_code != 200:
            # Non-retryable API error (bad key, bad model name, etc.)
            raise RuntimeError(
                f"Cohere embed error {r.status_code}: {r.text[:200]}"
            )

        data       = r.json()
        embeddings = data.get("embeddings", {}).get("float", [])
        if not embeddings:
            raise RuntimeError(f"No embeddings in response: {list(data.keys())}")

        return embeddings

    raise RuntimeError(f"Embed failed after 3 attempts. Last error: {last_exc}")


# ── Public API ─────────────────────────────────────────────────────────
def embed_texts(
    texts:         list[str],
    input_type:    str  = "search_document",
    show_progress: bool = True,
) -> list[list[float]]:
    """
    Embed a list of texts, using the shard cache where available.

    Returns:
        List of float vectors in the same order as `texts`.

    Raises:
        RuntimeError if COHERE_KEY is unset or all API retries fail.
    """
    if not texts:
        return []

    results: list[Optional[list[float]]] = [None] * len(texts)
    to_embed: list[tuple[int, str]] = []      # (original_index, text)

    for i, text in enumerate(texts):
        vec = _read_cached(_text_hash(text))
        if vec is not None:
            results[i] = vec
        else:
            to_embed.append((i, text))

    cache_hits = len(texts) - len(to_embed)
    if show_progress:
        if cache_hits:
            print(f"  [EMBED] {cache_hits} cached, {len(to_embed)} to embed...")
        else:
            print(f"  [EMBED] Embedding {len(to_embed)} texts...")

    for batch_start in range(0, len(to_embed), _BATCH_SIZE):
        batch       = to_embed[batch_start: batch_start + _BATCH_SIZE]
        batch_texts = [t for _, t in batch]

        if show_progress:
            done = min(batch_start + _BATCH_SIZE, len(to_embed))
            print(f"  [EMBED] Embedding {batch_start+1}–{done}/{len(to_embed)}...", end="\r")

        vectors = _embed_batch(batch_texts, input_type)

        for (orig_idx, text), vec in zip(batch, vectors):
            results[orig_idx] = vec
            _write_cached(_text_hash(text), vec)

        if batch_start + _BATCH_SIZE < len(to_embed):
            time.sleep(_RATE_DELAY)

    if show_progress and to_embed:
        print()   # newline after \r

    # FIX: explicit check instead of assert (assert is disabled by python -O)
    missing = [i for i, v in enumerate(results) if v is None]
    if missing:
        raise RuntimeError(
            f"Embeddings missing for indices {missing}. "
            "This is a bug — please report it."
        )

    return results  # type: ignore[return-value]


def embed_query(query: str) -> list[float]:
    """Embed a single search query (different input_type than documents)."""
    return embed_texts([query], input_type="search_query", show_progress=False)[0]


def cache_stats() -> dict:
    """Return stats about the embedding cache (number of shards, total entries)."""
    if not _CACHE_DIR.exists():
        return {"shards": 0, "entries": 0, "hot_cache": len(_hot_cache)}
    shard_files = list(_CACHE_DIR.rglob("*.json"))
    return {
        "shards":    len(set(p.parent for p in shard_files)),
        "entries":   len(shard_files),
        "hot_cache": len(_hot_cache),
        "cache_dir": str(_CACHE_DIR),
    }


# ── CLI test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_texts = [
        "Bitcoin uses proof-of-work to secure the blockchain.",
        "Ethereum smart contracts allow decentralised applications.",
        "DeFi protocols lock value as TVL — total value locked.",
    ]
    print(f"Embedding {len(test_texts)} texts with {RAG_EMBED_MODEL}...")
    vecs = embed_texts(test_texts)
    print(f"  Vectors: {len(vecs)}, dimension: {len(vecs[0])}")

    print("Second call (all should be cached)...")
    vecs2 = embed_texts(test_texts)
    print(f"  From cache: {len(vecs2)}")

    print(f"Cache stats: {cache_stats()}")

    q = embed_query("How does Bitcoin prevent double-spending?")
    print(f"Query vector dimension: {len(q)}")
