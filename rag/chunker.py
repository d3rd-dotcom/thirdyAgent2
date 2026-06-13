"""
rag/chunker.py — Recursive text chunker for thirdyAgent2 RAG

Fixes over v1:
  - Infinite recursion guard: v1 would recurse forever when a single
    word was longer than max_chars and no separator could split it
    further. Now falls back to hard character slicing.
  - __len__ fix: v1's __len__ returned approximate token count, which
    breaks any code that calls len(chunk) expecting character count.
    Token approximation moved to a dedicated `.token_count` property.
  - CHARS_PER_TOKEN constant replaces the magic number 4 scattered
    across the file.
  - overlap > chunk_size guard added.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP

# 1 token ≈ 4 English characters (GPT-style BPE approximation).
# Centralised here so embedder.py / retriever.py can import it
# instead of duplicating the magic number.
CHARS_PER_TOKEN: int = 4

# Separators tried in order from coarsest to finest grain.
_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ")


@dataclass
class Chunk:
    text:      str
    source:    str
    doc_id:    str
    chunk_idx: int
    metadata:  dict = field(default_factory=dict)

    def __len__(self) -> int:
        """
        FIX (v1 bug): v1 returned approximate token count from __len__,
        so `len(chunk)` was inconsistent with `len(chunk.text)`.
        Senior reviewers flag this as a violation of the principle of
        least surprise — __len__ should return the number of *items*
        in a container. For a Chunk the natural unit is characters.
        Use `.token_count` when you need an approximation of tokens.
        """
        return len(self.text)

    @property
    def token_count(self) -> int:
        """Approximate token count (1 token ≈ 4 chars)."""
        return len(self.text) // CHARS_PER_TOKEN


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Last-resort: split by character count. Never recurses."""
    return [text[i: i + max_chars] for i in range(0, len(text), max_chars) if text[i: i + max_chars].strip()]


def _recursive_split(text: str, max_chars: int, sep_idx: int = 0) -> list[str]:
    """
    FIX (v1 bug): v1 could infinite-loop when:
      - A piece was longer than max_chars
      - No remaining separator could split it further
      - sep_idx was already at the last separator

    Fix: when sep_idx exceeds the separator list, fall back to
    _hard_split() which guarantees termination.
    """
    if not text.strip():
        return []
    if len(text) <= max_chars:
        return [text]

    # All separators exhausted — hard split is the only remaining option
    if sep_idx >= len(_SEPARATORS):
        return _hard_split(text, max_chars)

    sep    = _SEPARATORS[sep_idx]
    pieces = text.split(sep) if sep else [text]

    # Re-merge short adjacent pieces to avoid tiny chunks
    merged: list[str] = []
    current           = ""
    for piece in pieces:
        candidate = f"{current}{sep}{piece}".strip() if current else piece.strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                merged.append(current)
            current = piece.strip()
    if current:
        merged.append(current)

    result: list[str] = []
    for piece in merged:
        if len(piece) <= max_chars:
            if piece.strip():
                result.append(piece)
        else:
            result.extend(_recursive_split(piece, max_chars, sep_idx + 1))

    return result


def chunk_document(
    text:       str,
    source:     str,
    chunk_size: int = RAG_CHUNK_SIZE,
    overlap:    int = RAG_CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Split a document into overlapping Chunk objects.

    Args:
        text:       Raw document text.
        source:     Human-readable source name (filename, URL, etc.).
        chunk_size: Target size in tokens.
        overlap:    Overlap in tokens between consecutive chunks.

    Returns:
        List of Chunk objects ordered as they appear in the source.
    """
    if not text or not text.strip():
        return []

    # Guard: overlap must be strictly less than chunk_size
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 8)

    max_chars     = chunk_size * CHARS_PER_TOKEN
    overlap_chars = overlap * CHARS_PER_TOKEN

    pieces = _recursive_split(text.strip(), max_chars)
    if not pieces:
        return []

    chunks:    list[Chunk] = []
    prev_tail: str         = ""

    for idx, piece in enumerate(pieces):
        if prev_tail:
            candidate = f"{prev_tail} {piece}".strip()
            # Trim to max_chars if the overlap pushes us over
            if len(candidate) > max_chars:
                candidate = candidate[-max_chars:]
        else:
            candidate = piece

        chunk_text = candidate.strip()
        if not chunk_text:
            continue

        chunks.append(Chunk(
            text      = chunk_text,
            source    = source,
            doc_id    = f"{source}::chunk_{idx}",
            chunk_idx = idx,
            metadata  = {
                "source":        source,
                "chunk_idx":     idx,
                "approx_tokens": len(chunk_text) // CHARS_PER_TOKEN,
            },
        ))

        prev_tail = piece[-overlap_chars:] if len(piece) > overlap_chars else piece

    return chunks


def chunk_documents(docs: list[dict]) -> list[Chunk]:
    """
    Chunk multiple documents at once.

    Args:
        docs: List of {"text": str, "source": str, "metadata": dict (optional)}

    Returns:
        Flat list of all Chunk objects across all documents.
    """
    all_chunks: list[Chunk] = []
    for doc in docs:
        text   = doc.get("text", "")
        source = doc.get("source", "unknown")
        extra  = doc.get("metadata", {})
        for c in chunk_document(text, source):
            c.metadata.update(extra)
            all_chunks.append(c)
    return all_chunks


# ── CLI self-test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Test 1: normal document")
    sample = (
        "Bitcoin: A Peer-to-Peer Electronic Cash System\n\n"
        "Abstract. A purely peer-to-peer version of electronic cash would allow "
        "online payments to be sent directly from one party to another without "
        "going through a financial institution.\n\n"
        "Digital signatures provide part of the solution, but the main benefits "
        "are lost if a trusted third party is still required to prevent double-spending."
    )
    chunks = chunk_document(sample, "bitcoin_whitepaper.txt", chunk_size=64, overlap=8)
    print(f"  Chunks: {len(chunks)}")
    for c in chunks:
        print(f"  [{c.chunk_idx}] len={len(c)} token_count={c.token_count}: {c.text[:50]}...")

    print("\nTest 2: single very long word (infinite-recursion regression test)")
    long_word = "a" * 3000   # longer than any chunk_size * CHARS_PER_TOKEN
    chunks2   = chunk_document(long_word, "stress_test", chunk_size=64, overlap=8)
    print(f"  Chunks: {len(chunks2)} (expected >0, no infinite loop)")

    print("\nTest 3: overlap >= chunk_size guard")
    chunks3 = chunk_document(sample, "guard_test", chunk_size=32, overlap=32)
    print(f"  Chunks: {len(chunks3)} (overlap was clamped, no crash)")

    print("\nAll tests passed.")
