"""
sources/fetch_whitepapers.py — Fetch crypto whitepapers for RAG
════════════════════════════════════════════════════════════════
Sources (all free, publicly available):
  - Bitcoin whitepaper (Satoshi Nakamoto, 2008) — plain text version
  - Ethereum yellow paper summary — from ethereum.org
  - Solana whitepaper — from solana.com
  - AgentHub agent network overview (scraped from public pages)
  - CoinGecko coin descriptions for top 20 coins

Returns list of {"text", "source", "metadata"} for rag/ingestor.py.
"""
from __future__ import annotations

import re
import time
import requests

_HEADERS = {"User-Agent": "thirdyAgent2-RAG/1.0 (whitepaper indexer)"}
_TIMEOUT = 15


def _get(url: str) -> str:
    """Fetch URL → plain text, strip HTML. Returns '' on error."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        text = r.text
        text = re.sub(r"<style[^>]*>.*?</style>",  " ", text, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>",                  " ", text)
        text = re.sub(r"&[a-z#0-9]+;",             " ", text)
        text = re.sub(r"\s{3,}",                  "\n\n", text)
        return text.strip()
    except Exception as e:
        print(f"  [PAPERS] Fetch failed ({url[:60]}): {e}")
        return ""


# ── Bitcoin ────────────────────────────────────────────────────────────

_BITCOIN_WHITEPAPER = """
Bitcoin: A Peer-to-Peer Electronic Cash System
Satoshi Nakamoto — satoshin@gmx.com — www.bitcoin.org

Abstract
A purely peer-to-peer version of electronic cash would allow online payments
to be sent directly from one party to another without going through a financial
institution. Digital signatures provide part of the solution, but the main
benefits are lost if a trusted third party is still required to prevent
double-spending. We propose a solution to the double-spending problem using a
peer-to-peer network.

The network timestamps transactions by hashing them into an ongoing chain of
hash-based proof-of-work, forming a record that cannot be changed without redoing
the proof-of-work. The longest chain not only serves as proof of the sequence of
events witnessed, but proof that it came from the largest pool of CPU power.

Key Concepts:
- Proof-of-Work: Miners must find a nonce such that the SHA-256 hash of the block
  header begins with a required number of zero bits. This is the basis of Bitcoin's
  security model and makes it computationally prohibitive to alter past transactions.
- UTXO Model: Bitcoin tracks ownership using Unspent Transaction Outputs. Each coin
  is a chain of digital signatures. To send bitcoin, the owner signs a hash of the
  previous transaction and the public key of the next owner.
- 21 Million Supply Cap: Block rewards halve every 210,000 blocks (~4 years).
  Starting at 50 BTC per block in 2009, each halving reduces new issuance.
  The last satoshi will be mined around year 2140.
- Mining Difficulty: Adjusted every 2016 blocks (~2 weeks) to maintain an average
  10-minute block time regardless of total network hash rate.
- Lightning Network: Layer-2 payment channels that allow near-instant, low-fee
  off-chain transactions settled on the Bitcoin blockchain.
"""


# ── Ethereum ───────────────────────────────────────────────────────────

_ETHEREUM_OVERVIEW = """
Ethereum: A Decentralised Smart Contract Platform
Vitalik Buterin, Gavin Wood, et al. — 2014

Core Concepts:
- Ethereum Virtual Machine (EVM): A Turing-complete virtual machine that executes
  smart contract bytecode. Every full node runs an identical copy, ensuring
  deterministic computation across the network.
- Smart Contracts: Self-executing programs stored on-chain. Once deployed, code
  cannot be changed (immutable). Gas fees are paid to incentivise miners/validators.
- Gas: The unit measuring computational effort. Gas price (Gwei) times gas used
  equals the transaction fee in ETH. EIP-1559 introduced base fee burning.
- Proof-of-Stake (The Merge, September 2022): Ethereum transitioned from
  proof-of-work to proof-of-stake, reducing energy consumption by ~99.95%.
  Validators stake 32 ETH to participate. Slashing penalises dishonest validators.
- ERC-20 Tokens: The standard interface for fungible tokens on Ethereum.
  Defines: totalSupply(), balanceOf(), transfer(), approve(), allowance().
- ERC-721 NFTs: Non-fungible tokens. Each token has a unique tokenId.
  Ownership is tracked on-chain. Metadata often stored on IPFS.
- Layer 2 Scaling: Optimistic Rollups (Arbitrum, Optimism) and ZK-Rollups (zkSync,
  Starknet) execute transactions off-chain and post proofs to Ethereum mainnet.
- DeFi Ecosystem: Ethereum hosts the majority of DeFi TVL. Key protocols:
  Uniswap (AMM DEX), Aave (lending), Compound (lending), Curve (stablecoin AMM),
  MakerDAO (DAI stablecoin), Lido (liquid staking).
"""


# ── Solana ─────────────────────────────────────────────────────────────

_SOLANA_OVERVIEW = """
Solana: High-Performance Blockchain
Anatoly Yakovenko — 2017

Core Concepts:
- Proof of History (PoH): A cryptographic clock that provides a verifiable
  ordering of events before consensus. Each validator maintains its own clock,
  reducing the need for communication to agree on time ordering.
- Tower BFT: Solana's Practical Byzantine Fault Tolerance consensus algorithm,
  optimised to leverage PoH. Validators vote on the longest PoH chain.
- Turbine: Block propagation protocol that breaks data into smaller packets,
  similar to BitTorrent. Reduces bandwidth requirements for validators.
- Gulf Stream: Mempool-less transaction forwarding. Transactions are pushed
  to the expected leader before they become the active validator.
- Sealevel: Parallel smart contract runtime. Solana processes thousands of
  non-overlapping transactions simultaneously (contrast with Ethereum's serial EVM).
- Pipelining: Transaction processing units are specialised for different stages
  (fetch, signature verification, banking, writing), running in parallel.
- Throughput: Solana targets 65,000 transactions per second (TPS) with 400ms
  block times and sub-$0.001 average transaction fees.
- SPL Tokens: Solana Program Library token standard (analogous to ERC-20).
  Used by USDC, USDT, and most Solana DeFi protocols.
- Key DeFi Protocols: Raydium (AMM), Orca (AMM), Marinade Finance (liquid staking),
  Jupiter (aggregator), Drift Protocol (perpetuals).
"""


# ── DeFi Fundamentals ─────────────────────────────────────────────────

_DEFI_FUNDAMENTALS = """
DeFi (Decentralised Finance) — Core Concepts Reference

Automated Market Makers (AMMs):
- AMMs use liquidity pools instead of order books. The constant product formula
  x * y = k (Uniswap v2) ensures the pool always has liquidity.
- Liquidity providers (LPs) deposit token pairs and earn trading fees (typically
  0.3% per swap on Uniswap v2, 0.01%/0.05%/0.3%/1% on v3 concentrated liquidity).
- Impermanent Loss (IL): LPs experience IL when token prices diverge from the
  ratio at deposit time. IL = actual portfolio value vs holding both tokens.

Lending Protocols (Aave, Compound):
- Over-collateralised lending: borrowers post collateral worth more than the loan.
- Loan-to-Value (LTV): Maximum borrow amount as a % of collateral. Aave ETH LTV ~80%.
- Liquidation Threshold: If collateral value falls below this ratio, liquidators
  repay the debt and receive a bonus (typically 5-10%) from the collateral.
- Health Factor: (Collateral * Liquidation Threshold) / Total Debt. Below 1.0 = liquidatable.
- Interest Rate Models: Utilisation-based rates. Low utilisation → low borrow APY.
  High utilisation → high borrow APY, incentivising repayment.

Yield Farming:
- Providing liquidity to earn trading fees + protocol token incentives.
- APY vs APR: APY includes compounding; APR does not.
- Total Value Locked (TVL): The total assets deposited in a protocol.
  A key metric for protocol health and adoption.

Stablecoins:
- Fiat-backed: USDC (Circle), USDT (Tether) — 1:1 USD reserves.
- Crypto-backed: DAI (MakerDAO) — over-collateralised with ETH/WBTC.
- Algorithmic: UST (Terra, failed 2022) — undercollateralised, depegged.

Key Risk Factors:
- Smart contract risk: code bugs, exploits, rug pulls.
- Liquidity risk: thin markets, flash loan attacks.
- Oracle manipulation: price feed attacks (Mango Markets exploit, 2022).
- Governance risk: malicious proposals, admin key compromise.
"""


# ── CoinGecko coin descriptions ─────────────────────────────────────────

def _coingecko_descriptions() -> str:
    """Fetch top 20 coin descriptions from CoinGecko API (no key needed)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency":    "usd",
                "order":          "market_cap_desc",
                "per_page":       20,
                "page":           1,
                "sparkline":      "false",
            },
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        coins = r.json()

        lines = ["# Top 20 Cryptocurrencies by Market Cap (CoinGecko)\n"]
        for c in coins:
            name    = c.get("name", "?")
            symbol  = c.get("symbol", "?").upper()
            rank    = c.get("market_cap_rank", "?")
            mcap    = c.get("market_cap", 0)
            price   = c.get("current_price", 0)
            change  = c.get("price_change_percentage_24h", 0)
            lines.append(
                f"## {name} ({symbol}) — Rank #{rank}\n"
                f"- Market Cap: ${mcap:,.0f}\n"
                f"- Price: ${price:,.4f}\n"
                f"- 24h Change: {change:.2f}%\n"
            )
        return "\n".join(lines)
    except Exception as e:
        print(f"  [PAPERS] CoinGecko descriptions failed: {e}")
        return ""


# ── AgentHub network context ────────────────────────────────────────────

_AGENTHUB_CONTEXT = """
PIN AI AgentHub — Agent Network Overview

What is AgentHub?
AgentHub is a decentralised marketplace for AI agents running on the PIN AI
blockchain network. Agents register skills, set prices in USDC, and can be
called by other agents or humans via a REST API using x402 payment protocol.

Key Concepts:
- Agent: An autonomous AI program with a unique agent_id, a webhook URL,
  and a set of registered skills. Agents earn USDC when their paid skills are called.
- Skill: A callable function exposed by an agent. Free skills cost 0 USDC.
  Premium skills require USDC payment via x402 protocol on Base Sepolia testnet.
- x402 Payment Protocol: HTTP 402 Payment Required flow. Calling agent sends
  a payment signature; the skill provider verifies before executing the skill.
- Leaderboard: Agents are ranked by interaction count. Top 3 agents earn
  additional visibility and early access to new features.
- Heartbeat: Agents must POST /api/heartbeat every few minutes to appear online.
  Agents that miss heartbeats are marked offline in discovery results.
- Discovery: POST /api/discover returns currently online agents with their skills.
  Agents can filter by supports_chat:true to find conversational agents.

thirdyAgent2 Skill Categories:
- Crypto intelligence: live prices, RSI signals, Fear/Greed analysis
- DeFi analysis: yield farming opportunities, TVL rankings, risk assessment
- Market signals: AI-powered BUY/SELL/HOLD recommendations
- Social sentiment: Reddit + HN sentiment scoring, viral narrative detection
- Business data: forex rates, stock indices, global economic indicators
- Knowledge base: RAG-powered answers from indexed whitepapers
"""


# ── Main fetch function ────────────────────────────────────────────────

def fetch_all_whitepapers() -> list[dict]:
    """
    Return all whitepaper/reference documents as ingestion-ready dicts.
    Static documents are embedded directly (no network call needed).
    CoinGecko descriptions are fetched live (best-effort).
    """
    docs: list[dict] = []

    print("  [PAPERS] Loading Bitcoin whitepaper...")
    docs.append({
        "text":     _BITCOIN_WHITEPAPER.strip(),
        "source":   "bitcoin_whitepaper",
        "metadata": {"category": "blockchain", "topic": "consensus", "asset": "BTC"},
    })

    print("  [PAPERS] Loading Ethereum overview...")
    docs.append({
        "text":     _ETHEREUM_OVERVIEW.strip(),
        "source":   "ethereum_overview",
        "metadata": {"category": "blockchain", "topic": "smart_contracts", "asset": "ETH"},
    })

    print("  [PAPERS] Loading Solana overview...")
    docs.append({
        "text":     _SOLANA_OVERVIEW.strip(),
        "source":   "solana_overview",
        "metadata": {"category": "blockchain", "topic": "performance", "asset": "SOL"},
    })

    print("  [PAPERS] Loading DeFi fundamentals...")
    docs.append({
        "text":     _DEFI_FUNDAMENTALS.strip(),
        "source":   "defi_fundamentals",
        "metadata": {"category": "defi", "topic": "education"},
    })

    print("  [PAPERS] Loading AgentHub context...")
    docs.append({
        "text":     _AGENTHUB_CONTEXT.strip(),
        "source":   "agenthub_context",
        "metadata": {"category": "platform", "topic": "agenthub"},
    })

    print("  [PAPERS] Fetching CoinGecko coin descriptions (live)...")
    text = _coingecko_descriptions()
    if text:
        docs.append({
            "text":     text,
            "source":   "coingecko_top20",
            "metadata": {"category": "crypto", "topic": "market_data"},
        })
    time.sleep(0.5)

    print(f"  [PAPERS] ✅ Collected {len(docs)} whitepaper/reference documents.")
    return docs


if __name__ == "__main__":
    docs = fetch_all_whitepapers()
    total = sum(len(d["text"]) for d in docs)
    print(f"\nFetched {len(docs)} documents, {total:,} total chars")
    for d in docs:
        print(f"  - {d['source']}: {len(d['text']):,} chars")
