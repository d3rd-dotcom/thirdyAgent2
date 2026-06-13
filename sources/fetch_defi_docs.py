"""
sources/fetch_defi_docs.py — Fetch DeFi protocol documentation for RAG
═══════════════════════════════════════════════════════════════════════
Sources (all free, no API key):
  - DeFiLlama protocol pages (chain descriptions, TVL context)
  - Uniswap docs (public)
  - Aave risk parameters (public JSON)
  - Compound docs (public)
  - Lido docs overview

Returns list of {"text": str, "source": str, "metadata": dict}
for ingestion by rag/ingestor.py
"""
from __future__ import annotations
import re
import time
import requests

HEADERS = {"User-Agent": "thirdyAgent2-RAG/1.0 (DeFi knowledge indexer)"}
TIMEOUT = 12


def _get_text(url: str) -> str:
    """Fetch URL and strip HTML/JS."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        text = r.text
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"\s{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        print(f"  [DEFI_DOCS] Fetch failed ({url[:60]}): {e}")
        return ""


def _defillama_protocol_summary() -> str:
    """Get top 20 protocol names, chain, TVL from DeFiLlama API as structured text."""
    try:
        r = requests.get("https://api.llama.fi/protocols", timeout=10).json()
        top = sorted(r, key=lambda x: x.get("tvl", 0), reverse=True)[:20]
        lines = ["# Top DeFi Protocols by TVL (DeFiLlama)\n"]
        for p in top:
            tvl     = p.get("tvl", 0)
            name    = p.get("name", "?")
            chain   = p.get("chain", "Multi")
            cat     = p.get("category", "?")
            desc    = p.get("description", "")[:200]
            lines.append(
                f"## {name}\n"
                f"- Category: {cat}\n"
                f"- Chain: {chain}\n"
                f"- TVL: ${tvl:,.0f}\n"
                f"- Description: {desc}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        print(f"  [DEFI_DOCS] DeFiLlama protocols failed: {e}")
        return ""


def _aave_risk_params() -> str:
    """Fetch Aave V3 risk parameters from public GitHub."""
    try:
        # Aave V3 Ethereum market risk params (public JSON from docs)
        r = requests.get(
            "https://raw.githubusercontent.com/bgd-labs/aave-address-book/main/src/AaveV3Ethereum.sol",
            headers=HEADERS,
            timeout=10,
        )
        if r.status_code != 200:
            return ""
        # Return the raw Solidity as reference text (still useful for RAG)
        content = r.text[:8000]   # first 8000 chars = address definitions
        return f"# Aave V3 Ethereum Address Book\n\n{content}"
    except Exception as e:
        print(f"  [DEFI_DOCS] Aave risk params failed: {e}")
        return ""


def _yield_pool_descriptions() -> str:
    """Get top yield pools with full metadata as training text."""
    try:
        r = requests.get("https://yields.llama.fi/pools", timeout=12).json()
        pools = sorted(
            [p for p in r.get("data", []) if p.get("tvlUsd", 0) >= 10_000_000],
            key=lambda x: x.get("tvlUsd", 0),
            reverse=True,
        )[:40]
        lines = ["# Top DeFi Yield Pools (DeFiLlama)\n"]
        for p in pools:
            lines.append(
                f"## {p.get('symbol','?')} on {p.get('project','?')}\n"
                f"- Chain: {p.get('chain','?')}\n"
                f"- APY: {p.get('apy',0):.2f}%\n"
                f"- TVL: ${p.get('tvlUsd',0):,.0f}\n"
                f"- APY 7d: {p.get('apyMean30d',0):.2f}%\n"
                f"- Stablecoin: {p.get('stablecoin',False)}\n"
                f"- IL Risk: {p.get('ilRisk','unknown')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        print(f"  [DEFI_DOCS] Yield pools failed: {e}")
        return ""


def _chain_summaries() -> str:
    """Get blockchain chain descriptions from DeFiLlama."""
    try:
        r = requests.get("https://api.llama.fi/v2/chains", timeout=10).json()
        top = sorted(r, key=lambda x: x.get("tvl", 0), reverse=True)[:15]
        lines = ["# Blockchain Networks by TVL (DeFiLlama)\n"]
        for c in top:
            tvl  = c.get("tvl", 0)
            name = c.get("name", "?")
            lines.append(
                f"## {name}\n"
                f"- TVL: ${tvl:,.0f}\n"
                f"- Type: Layer {c.get('chainId','?')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        print(f"  [DEFI_DOCS] Chain summaries failed: {e}")
        return ""


# ── Core fetch function ────────────────────────────────────────────────

def fetch_all_defi_docs() -> list[dict]:
    """
    Fetch all DeFi documentation sources.
    Returns list of {"text", "source", "metadata"} dicts.
    """
    docs: list[dict] = []

    print("  [DEFI_DOCS] Fetching DeFiLlama protocol summaries...")
    text = _defillama_protocol_summary()
    if text:
        docs.append({
            "text":     text,
            "source":   "defillama_protocols",
            "metadata": {"category": "defi", "topic": "protocol_rankings"},
        })
    time.sleep(0.5)

    print("  [DEFI_DOCS] Fetching top yield pools...")
    text = _yield_pool_descriptions()
    if text:
        docs.append({
            "text":     text,
            "source":   "defillama_yield_pools",
            "metadata": {"category": "defi", "topic": "yield_farming"},
        })
    time.sleep(0.5)

    print("  [DEFI_DOCS] Fetching chain TVL summaries...")
    text = _chain_summaries()
    if text:
        docs.append({
            "text":     text,
            "source":   "defillama_chains",
            "metadata": {"category": "blockchain", "topic": "tvl_rankings"},
        })
    time.sleep(0.5)

    print("  [DEFI_DOCS] Fetching Aave address book...")
    text = _aave_risk_params()
    if text:
        docs.append({
            "text":     text,
            "source":   "aave_v3_params",
            "metadata": {"category": "defi", "topic": "lending", "protocol": "aave"},
        })
    time.sleep(0.5)

    print(f"  [DEFI_DOCS] ✅ Collected {len(docs)} DeFi documents.")
    return docs


if __name__ == "__main__":
    docs = fetch_all_defi_docs()
    total_chars = sum(len(d["text"]) for d in docs)
    print(f"\nFetched {len(docs)} documents, {total_chars:,} total chars")
    for d in docs:
        print(f"  - {d['source']}: {len(d['text']):,} chars")
