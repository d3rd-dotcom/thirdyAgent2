"""
build_rag.py — One-shot RAG knowledge base builder for thirdyAgent2
════════════════════════════════════════════════════════════════════
Run once to build the ChromaDB index from all knowledge sources.
Re-running is safe: already-indexed sources are skipped by default.

Usage:
    python build_rag.py                # incremental (skip existing sources)
    python build_rag.py --rebuild      # delete all and re-index everything
    python build_rag.py --dry-run      # show what would be indexed, no embedding
    python build_rag.py --source defi  # index only defi docs
    python build_rag.py --verify       # check index health and run a test query
    python build_rag.py --stats        # show current index stats only

Sources indexed (total ~1,000-1,500 chunks depending on live API data):
    bitcoin_whitepaper      BTC proof-of-work, UTXO, supply model
    ethereum_overview       EVM, smart contracts, PoS, L2 scaling
    solana_overview         PoH, Sealevel, Turbine, Gulf Stream
    defi_fundamentals       AMMs, lending, yield farming, risk
    agenthub_context        PIN AI AgentHub platform overview
    coingecko_top20         Live top-20 coin market data
    defillama_protocols     Top 20 DeFi protocols by TVL
    defillama_yield_pools   Top yield pools with APY/TVL
    defillama_chains        Blockchain networks by TVL
    aave_v3_params          Aave V3 Ethereum address book
"""
from __future__ import annotations

import sys
import time
import datetime
from pathlib import Path

# ── Pre-flight: confirm RAG dependencies before expensive imports ──────
def _preflight() -> bool:
    try:
        import chromadb   # noqa: F401
    except ImportError:
        print(
            "❌  chromadb not installed.\n"
            "    Run: pip install chromadb==0.4.24 --break-system-packages\n"
            "    Then re-run: python build_rag.py"
        )
        return False

    from config import COHERE_KEY
    if not COHERE_KEY:
        print(
            "❌  COHERE_KEY not set.\n"
            "    Add it to your .env file.\n"
            "    Get a free key at: https://dashboard.cohere.com/"
        )
        return False

    return True


def _parse_args() -> dict:
    args = sys.argv[1:]
    return {
        "rebuild":   "--rebuild"   in args,
        "dry_run":   "--dry-run"   in args,
        "verify":    "--verify"    in args,
        "stats":     "--stats"     in args,
        "source":    next((args[i+1] for i, a in enumerate(args) if a == "--source" and i+1 < len(args)), ""),
    }


def _print_banner(flags: dict) -> None:
    mode = "DRY RUN" if flags["dry_run"] else ("REBUILD ALL" if flags["rebuild"] else "INCREMENTAL")
    print(f"""
{'='*62}
  thirdyAgent2 — RAG Knowledge Base Builder
  Mode: {mode}
{'='*62}
  Sources : Bitcoin · Ethereum · Solana · DeFi · AgentHub
            DeFiLlama protocols · Yield pools · Chains · Aave
  Embedder: Cohere {__import__('config').RAG_EMBED_MODEL}
  Store   : ChromaDB → {__import__('config').CHROMA_PERSIST_DIR}
{'='*62}
""")


def _run_verify() -> None:
    """Run a set of test queries against the built index."""
    from rag.retriever  import retrieve, retrieve_context_string
    from rag.store      import collection_stats

    stats = collection_stats()
    print(f"\n{'─'*50}")
    print(f"  Index stats: {stats}")

    if stats.get("chunk_count", 0) == 0:
        print("  ❌  Index is empty — run build_rag.py without --verify first")
        return

    test_queries = [
        "What is proof of work in Bitcoin?",
        "How does Aave calculate liquidation?",
        "What is Solana's Proof of History?",
        "What is impermanent loss in DeFi?",
    ]

    print(f"\n  Running {len(test_queries)} test queries...\n")
    all_passed = True
    for q in test_queries:
        result = retrieve(q, top_k=2)
        status = result["status"]
        n      = len(result["chunks"])
        if status == "ok" and n > 0:
            top_source = result["chunks"][0]["source"]
            dist       = result["chunks"][0]["distance"]
            print(f"  ✅  '{q[:45]}'\n      → {n} chunks, top: {top_source} (dist={dist:.3f})")
        else:
            print(f"  ❌  '{q[:45]}'\n      → status={status}")
            all_passed = False

    ctx = retrieve_context_string("What is TVL in DeFi?", max_chars=500)
    if ctx:
        print(f"\n  ✅  Context string works ({len(ctx)} chars)")
    else:
        print("\n  ❌  Context string returned empty")
        all_passed = False

    print(f"\n  {'✅ All verify checks passed.' if all_passed else '❌ Some checks failed — review index.'}")


def main() -> None:
    flags = _parse_args()

    # Stats-only mode — no preflight needed
    if flags["stats"]:
        try:
            from rag.store import collection_stats
            from rag.embedder import cache_stats
            print(f"\nDB stats:    {collection_stats()}")
            print(f"Cache stats: {cache_stats()}\n")
        except Exception as e:
            print(f"Stats failed: {e}")
        return

    # Verify-only mode
    if flags["verify"]:
        if not _preflight():
            sys.exit(1)
        _run_verify()
        return

    if not _preflight():
        sys.exit(1)

    _print_banner(flags)

    # ── Import sources ─────────────────────────────────────────────────
    from sources.fetch_whitepapers import fetch_all_whitepapers
    from sources.fetch_defi_docs   import fetch_all_defi_docs
    from rag.ingestor              import ingest_documents
    from rag.store                 import collection_stats

    # ── Optionally wipe existing index ────────────────────────────────
    if flags["rebuild"]:
        print("⚠️   --rebuild: deleting existing ChromaDB collection...")
        try:
            import chromadb
            from chromadb.config import Settings
            from config import CHROMA_PERSIST_DIR
            client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
            client.delete_collection("thirdyagent2_knowledge")
            print("    Deleted. Re-creating on first upsert.\n")
        except Exception as e:
            print(f"    Warning: delete failed ({e}) — continuing anyway\n")

    # ── Gather all source documents ────────────────────────────────────
    t_start = time.time()
    all_sources: list[dict] = []

    src_filter = flags["source"].lower()

    if not src_filter or "paper" in src_filter or "whitepaper" in src_filter or "btc" in src_filter or "eth" in src_filter or "sol" in src_filter or "defi_fund" in src_filter or "agent" in src_filter or "coin" in src_filter:
        print("📄  Fetching whitepapers and reference docs...")
        all_sources.extend(fetch_all_whitepapers())

    if not src_filter or "defi" in src_filter or "llama" in src_filter or "yield" in src_filter or "aave" in src_filter:
        print("\n📊  Fetching DeFi protocol data from DeFiLlama...")
        all_sources.extend(fetch_all_defi_docs())

    if not all_sources:
        print(f"⚠️   No sources matched filter '{src_filter}'")
        sys.exit(0)

    # ── Dry run: report without embedding ─────────────────────────────
    if flags["dry_run"]:
        total_chars = sum(len(s["text"]) for s in all_sources)
        total_toks  = total_chars // 4
        print(f"\n{'─'*50}")
        print(f"  DRY RUN — would index {len(all_sources)} documents")
        print(f"  Total chars: {total_chars:,}  (~{total_toks:,} tokens)")
        for s in all_sources:
            print(f"  - {s['source']}: {len(s['text']):,} chars")
        print(f"\n  Estimated chunks (512-token target): ~{total_toks // 512 + len(all_sources):,}")
        print(f"  Estimated Cohere embed calls: ~{total_toks // (512*90) + 1}")
        print("\n  Run without --dry-run to actually build the index.")
        return

    # ── Ingest ────────────────────────────────────────────────────────
    print(f"\n🚀  Starting ingestion of {len(all_sources)} source documents...\n")
    summary = ingest_documents(
        all_sources,
        replace=flags["rebuild"],
        show_progress=True,
    )

    elapsed = time.time() - t_start
    stats   = collection_stats()

    # ── Summary report ────────────────────────────────────────────────
    print(f"\n{'='*62}")
    print(f"  ✅  BUILD COMPLETE  ({elapsed:.1f}s)")
    print(f"{'='*62}")
    print(f"  Documents processed : {summary['total_docs']}")
    print(f"  Chunks created      : {summary['total_chunks']}")
    print(f"  Vectors embedded    : {summary['total_embedded']}")
    print(f"  Sources skipped     : {len(summary['skipped'])} (already indexed)")
    print(f"  Errors              : {len(summary['errors'])}")
    print(f"  Total index chunks  : {stats.get('chunk_count', '?'):,}")
    print(f"  Index location      : {stats.get('persist_dir', '?')}")

    if summary["skipped"]:
        print(f"\n  ⏭   Skipped (already indexed): {', '.join(summary['skipped'])}")
        print(f"      To re-index: python build_rag.py --rebuild")

    if summary["errors"]:
        print(f"\n  ⚠️   Errors:")
        for err in summary["errors"]:
            print(f"       {err}")

    if summary["per_source"]:
        print(f"\n  Per-source chunk counts:")
        for src, info in sorted(summary["per_source"].items()):
            print(f"    {src:<35} {info['chunks']:>5} chunks")

    print(f"\n  Next step: python agent.py")
    print(f"  Verify  : python build_rag.py --verify\n")

    # Auto-verify after successful build
    if summary["total_chunks"] > 0 and not flags["dry_run"]:
        print("Running quick verification...")
        _run_verify()


if __name__ == "__main__":
    main()
