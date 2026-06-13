"""
register_skills.py — Batch register all skills to AgentHub
=========================================================
Registers all 41 skills (25 new free + 3 new premium + fixes existing 2 premium)
using POST /api/agents/:id/skills — the CORRECT endpoint, not `pinai-agenthub init`

Run: python register_skills.py
"""

import requests
import time
import json

# ─────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────

# CRIT-04 FIX: credentials from config.py — never hardcode
from config import (
    AGENTHUB_API_KEY as API_KEY,
    AGENT_ID,
    AGENTHUB_HUB_URL as HUB,
    AGENTHUB_HEADERS as HEADERS,
)

# ─────────────────────────────────────────────────────────────────────
#  ALL SKILLS TO REGISTER
#  Format: (name, description, price_usdc)
#  price_usdc = "0" for free, "0.25" / "0.50" / "1.00" for premium
# ─────────────────────────────────────────────────────────────────────

SKILLS = [

    # ── PACK 1: CRYPTO (skills_free_crypto.py) ──────────────────────
    (
        "crypto_pulse",
        "Multi-source crypto snapshot: live price, 24h change, market cap, Fear and Greed sentiment, trending coins. Sources: CoinGecko plus alternative.me. Free.",
        "0"
    ),
    (
        "btc_network_intel",
        "Bitcoin network intelligence: mempool fees, latest block data, hashrate, difficulty, total BTC mined. Sources: Mempool.space and blockchain.info. Free.",
        "0"
    ),
    (
        "defi_pulse",
        "DeFi ecosystem pulse: top yield pools by APY and TVL filtering, chain TVL rankings. Source: DeFiLlama. Filter by chain and min APY. Free.",
        "0"
    ),
    (
        "dex_scanner",
        "Real-time DEX token scanner using DexScreener API. Covers 2M plus tokens across 80 plus chains and 300 plus DEXs. 300 requests per minute free. Search any token by name. Trending boosted tokens included. Free.",
        "0"
    ),
    (
        "crypto_news_feed",
        "Real-time crypto news feed from cryptocurrency.cv and Hacker News filtered by topic. Topics: bitcoin, ethereum, defi, solana. Free.",
        "0"
    ),

    # ── PACK 2: SCIENCE (skills_free_science.py) ────────────────────
    (
        "space_explorer",
        "Real-time space data: ISS current position, number of people currently in space, crew names, next rocket launch. Sources: open-notify.org and thespacedevs.com. Free.",
        "0"
    ),
    (
        "math_solver",
        "Solve math expressions: simplify, factor, derive, integrate, zeroes, trig functions. Powered by Newton API. Example: operation=derive, expression=x^3+2x. Free.",
        "0"
    ),
    (
        "earth_watch",
        "Real-time earth data: significant earthquakes this week from USGS, plus air quality index and PM2.5 for any city via open-meteo. Free.",
        "0"
    ),
    (
        "astronomy_feed",
        "Astronomy data: sunrise, solar noon, and sunset times for any city or coordinates, plus current moon phase calculation. Sources: sunrise-sunset.org and open-meteo. Free.",
        "0"
    ),
    (
        "science_facts",
        "Random science bundle: number facts from numbersapi, useless interesting facts, cat facts, and life advice. Multiple free APIs combined. Free.",
        "0"
    ),

    # ── PACK 3: ENTERTAINMENT (skills_free_entertainment.py) ─────────
    (
        "anime_universe",
        "Anime data from MyAnimeList via Jikan API: top anime rankings, random anime discovery, or search by title. Mode options: top, random, search. Free.",
        "0"
    ),
    (
        "fun_pack",
        "Fun content bundle: programming jokes, dad jokes, and trivia questions with answers. Multiple free joke APIs combined. Free.",
        "0"
    ),
    (
        "gamer_hub",
        "Gaming data: top free-to-play games from freetogame.com, or search any game via RAWG database. Mode options: free or search. Free.",
        "0"
    ),
    (
        "quotes_wisdom",
        "Quotes and wisdom from multiple sources: Quotable.io, ZenQuotes, and Advice Slip. Filter by author or topic. Free.",
        "0"
    ),
    (
        "daily_briefing",
        "Daily briefing bundle: today date and week number, day of year historical fact, random interesting fact, motivational quote, and activity suggestion. Free.",
        "0"
    ),

    # ── PACK 4: KNOWLEDGE (skills_free_knowledge.py) ─────────────────
    (
        "tech_news_feed",
        "Real-time tech news: Hacker News top stories filtered by topic, plus DEV.to articles. Topics: ai, blockchain, python, webdev. Free.",
        "0"
    ),
    (
        "world_knowledge",
        "World facts: country data including capital, population, area, currencies, languages from REST Countries API. Plus real-time timezone from worldtimeapi.org. Free.",
        "0"
    ),
    (
        "paper_search",
        "Academic paper search across 250 million papers via Semantic Scholar API. No API key required. Filter by query, year, limit. Returns title, authors, citation count, abstract. Free.",
        "0"
    ),
    (
        "dev_toolkit",
        "Developer tools bundle: GitHub repository search by query sorted by stars, IP address geolocation lookup, or UUID generator. Mode options: github, ip, uuid. Free.",
        "0"
    ),
    (
        "web_extractor",
        "Web content extraction: Wikipedia summary for any topic, or Open Graph metadata extraction from any URL. Mode options: wiki or url. Free.",
        "0"
    ),

    # ── PACK 5: BUSINESS (skills_free_business.py) ───────────────────
    (
        "global_economy",
        "Global economic indicators from World Bank API: GDP per capita, inflation rate, unemployment. Plus live ECB forex rates via frankfurter.app. Filter by country code. Free.",
        "0"
    ),
    (
        "market_scanner",
        "Stock market scanner: major index prices including S&P 500, NASDAQ, DOW, VIX, Gold, Oil via Yahoo Finance. Or get a single stock quote by symbol. Free.",
        "0"
    ),
    (
        "forex_tracker",
        "Real-time forex rates from the European Central Bank via Frankfurter.app. Live rates, currency conversion, or historical rates. Covers 170 plus currencies. Free.",
        "0"
    ),
    (
        "startup_intel",
        "Startup and VC intelligence: recent Show HN product launches filtered by topic, plus new GitHub projects from 2026. Topics: ai, fintech, crypto, saas. Free.",
        "0"
    ),
    (
        "business_news",
        "Business and financial news from Hacker News and Reddit r/investing or r/economics. Filter by topic: economy, markets, stocks, crypto, investing. Free.",
        "0"
    ),

    # ── PREMIUM AI SKILLS (skills_ai.py) ─────────────────────────────
    (
        "market_signal",
        "AI-powered BUY/SELL/HOLD trading signal combining 6 data sources: live price, RSI(14), Fear and Greed Index trend, DexScreener DEX liquidity, Reddit sentiment analysis. Cerebras AI synthesis with NVIDIA NIM fallback. Premium skill - 0.50 USDC per call.",
        "0.50"
    ),
    (
        "news_alpha",
        "Real-time crypto news impact analysis. Sources: Hacker News and Reddit r/CryptoCurrency filtered by topic. Mistral AI assesses market impact, magnitude, price effect, and key risks for any asset. Premium skill - 0.25 USDC per call.",
        "0.25"
    ),
    (
        "portfolio_analyzer",
        "Multi-asset crypto portfolio AI analysis using NVIDIA NIM DeepSeek R1. Analyzes allocations, RSI per asset, 24h weighted P&L, risk score, diversification score, and rebalancing suggestions. Bloomberg-grade analysis for 1.00 USDC vs $2000 per month. Premium skill - 1.00 USDC per call.",
        "1.00"
    ),
]

# ─────────────────────────────────────────────────────────────────────
#  FIX EXISTING PREMIUM SKILL DESCRIPTIONS
#  crypto_intelligence and defi_yield_finder still say "Groq AI"
# ─────────────────────────────────────────────────────────────────────

EXISTING_SKILL_FIXES = [
    (
        "sk_b576b7f4d77f4ae69f9eaf93",
        "Multi-source crypto intelligence combining live price, Fear and Greed Index, trending coins, and Cerebras AI analysis. Async 3-source fetch via CoinGecko, alternative.me, and trending endpoint. Premium skill - 0.25 USDC per call.",
        "0.25"
    ),
    (
        "sk_a7d76a55972c4127983e851e",
        "Find best DeFi yield opportunities across all chains with AI-powered risk analysis. Sources: DeFiLlama pools and chain TVL. NVIDIA NIM DeepSeek R1 risk assessment per pool. Premium skill - 0.50 USDC per call.",
        "0.50"
    ),
]

# ─────────────────────────────────────────────────────────────────────
#  REGISTRATION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def register_skill(name, description, price_usdc):
    """POST /api/agents/:id/skills — proper skill registration"""
    payload = {
        "name":        name,
        "description": description,
        "parameters":  {},
        "price_usdc":  price_usdc,
    }
    if price_usdc != "0":
        payload["payment_required"] = True

    try:
        r = requests.post(
            f"{HUB}/api/agents/{AGENT_ID}/skills",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}


def fix_existing_skill(skill_id, description, price_usdc):
    """PATCH /api/agents/:id/skills/:skill_id — fix existing skill description"""
    payload = {
        "description": description,
        "price_usdc":  price_usdc,
    }
    try:
        # Try PATCH first
        r = requests.patch(
            f"{HUB}/api/agents/{AGENT_ID}/skills/{skill_id}",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        if r.status_code in (200, 201):
            return r.status_code, r.json()
        # Fallback: PUT
        r2 = requests.put(
            f"{HUB}/api/agents/{AGENT_ID}/skills/{skill_id}",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        return r2.status_code, r2.json()
    except Exception as e:
        return 0, {"error": str(e)}


def update_agent_description():
    """Update the agent's main description"""
    payload = {
        "description": (
            "Autonomous financial intelligence agent on PIN AI AgentHub. "
            "41 skills: crypto intelligence, DeFi analysis, BUY/SELL/HOLD market signals, "
            "news impact analysis, portfolio assessment, DEX scanning across 80+ chains, "
            "forex rates, stock market indices, academic research, anime, gaming, world "
            "knowledge and more. Multi-LLM AI chain: Cerebras, NVIDIA NIM, Cloudflare, "
            "Mistral, Cohere. Bloomberg Terminal-grade financial analysis at cents per call. "
            "Open source: github.com/d3rd-dotcom/thirdyAgent2"
        )
    }
    try:
        r = requests.put(
            f"{HUB}/api/agents/{AGENT_ID}",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  thirdyAgent2 — SKILL REGISTRATION SCRIPT")
    print(f"  Agent: {AGENT_ID}")
    print(f"  Hub:   {HUB}")
    print("=" * 60)

    results = {
        "registered": [],
        "already_exists": [],
        "failed": [],
        "fixed": [],
        "fix_failed": [],
    }

    # ── STEP 1: Register 25 new free + 3 new premium skills ──────────
    print(f"\n📦 Registering {len(SKILLS)} skills...\n")

    for i, (name, description, price) in enumerate(SKILLS, 1):
        label = f"PREMIUM ({price} USDC)" if price != "0" else "FREE"
        print(f"  [{i:02d}/{len(SKILLS)}] {name} [{label}]")

        status, resp = register_skill(name, description, price)

        if status in (200, 201):
            skill_id = resp.get("skill_id") or resp.get("id") or "?"
            print(f"         ✅ Registered! skill_id: {skill_id}")
            results["registered"].append(name)

        elif status == 409 or "already" in str(resp).lower() or "exists" in str(resp).lower():
            print(f"         ⚠️  Already exists — skipping")
            results["already_exists"].append(name)

        elif status == 504 or status == 0:
            print(f"         ⏱️  Timeout (504) — retrying once...")
            time.sleep(3)
            status2, resp2 = register_skill(name, description, price)
            if status2 in (200, 201):
                print(f"         ✅ Registered on retry!")
                results["registered"].append(name)
            else:
                print(f"         ❌ Failed ({status2}): {str(resp2)[:80]}")
                results["failed"].append(name)

        else:
            print(f"         ❌ Failed ({status}): {str(resp)[:80]}")
            results["failed"].append(name)

        time.sleep(0.8)  # be nice to the server

    # ── STEP 2: Fix existing premium skill descriptions ───────────────
    print(f"\n🔧 Fixing {len(EXISTING_SKILL_FIXES)} existing skill descriptions...\n")

    for skill_id, description, price in EXISTING_SKILL_FIXES:
        print(f"  Updating: {skill_id[:30]}...")
        status, resp = fix_existing_skill(skill_id, description, price)
        if status in (200, 201):
            print(f"         ✅ Updated!")
            results["fixed"].append(skill_id)
        else:
            print(f"         ❌ Failed ({status}): {str(resp)[:80]}")
            results["fix_failed"].append(skill_id)
        time.sleep(0.8)

    # ── STEP 3: Update agent description ─────────────────────────────
    print(f"\n📝 Updating agent description...")
    status, resp = update_agent_description()
    if status in (200, 201):
        print(f"  ✅ Agent description updated!")
    else:
        print(f"  ❌ Description update failed ({status}): {str(resp)[:100]}")
        print(f"  ➡️  Retry manually with the curl command below")

    # ── SUMMARY ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  REGISTRATION SUMMARY")
    print("=" * 60)
    print(f"  ✅ Newly registered : {len(results['registered'])}")
    print(f"  ⚠️  Already existed : {len(results['already_exists'])}")
    print(f"  ❌ Failed           : {len(results['failed'])}")
    print(f"  🔧 Descriptions fixed: {len(results['fixed'])}")
    print(f"  ❌ Fix failed        : {len(results['fix_failed'])}")
    print("=" * 60)

    if results["failed"]:
        print("\n❌ FAILED SKILLS (run these manually):")
        for name in results["failed"]:
            # Find the skill data
            skill_data = next((s for s in SKILLS if s[0] == name), None)
            if skill_data:
                _, desc, price = skill_data
                print(f"""
  curl -X POST {HUB}/api/agents/{AGENT_ID}/skills ^
    -H "Authorization: Bearer {API_KEY}" ^
    -H "Content-Type: application/json" ^
    -d "{{\\"name\\": \\"{name}\\", \\"description\\": \\"{desc[:60]}...\\", \\"price_usdc\\": \\"{price}\\"}}"
""")

    total_expected = len(SKILLS) + 2  # +2 for existing premium
    total_on_hub   = 14 + len(results["registered"]) + len(results["already_exists"])
    print(f"\n  Expected total on AgentHub: ~{total_on_hub} skills")
    print(f"  (14 legacy + {len(results['registered'])} new + {len(results['already_exists'])} already existed)")

    if results["failed"]:
        print(f"\n⚠️  {len(results['failed'])} skills failed. Wait 1-2 min and run again.")
        print("   The 504 errors are server-side timeouts — retry usually works.")
    else:
        print("\n🎉 All skills registered! Run: pinai-agenthub skills list")
        print("   Then run: python message_all.py to broadcast your new lineup!")


if __name__ == "__main__":
    main()
