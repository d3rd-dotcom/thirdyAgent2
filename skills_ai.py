# -*- coding: utf-8 -*-
"""
=====================================================================
  skills_ai.py  --  AI-powered PREMIUM skills for thirdyAgent2
=====================================================================

PHASE 3 SKILLS (existing):
  - market_signal      (0.50 USDC)  BUY/SELL/HOLD, 6 data sources
  - news_alpha         (0.25 USDC)  News impact on price
  - portfolio_analyzer (1.00 USDC)  Multi-asset AI portfolio analysis
  - crypto_intelligence(0.25 USDC)  3-source async + Cerebras AI
  - defi_yield_finder  (0.50 USDC)  DeFiLlama + NVIDIA NIM risk

PHASE 8 ADDITIONS:
  - Gemini 2.0 Flash added to provider chain
  - GitHub Models (Llama 3.3 70B) added to provider chain
  - All keys now loaded from config.py (SA-01 fix)

FALLBACK ORDER (updated):
  Cerebras → NVIDIA → Gemini → GitHub → Cloudflare → Mistral → Cohere
=====================================================================
"""

import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# SA-01 fix: import from config.py instead of hardcoding
from config import (
    CEREBRAS_KEY, NVIDIA_KEY, CF_KEY, CF_ACCOUNT,
    MISTRAL_KEY, COHERE_KEY, GEMINI_KEY, GITHUB_MODELS_KEY,
)

# ─────────────────────────────────────────────────────────────────────
#  PROVIDER CONFIGS — Phase 8 adds Gemini + GitHub
# ─────────────────────────────────────────────────────────────────────

PROVIDERS = {
    "cerebras": {
        "url":     "https://api.cerebras.ai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
        "model":   "llama3.1-8b",
        "style":   "openai",
    },
    "nvidia": {
        "url":     "https://integrate.api.nvidia.com/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"},
        "model":   "meta/llama-3.1-8b-instruct",
        "style":   "openai",
    },
    # ── Phase 8: Gemini 2.0 Flash ──────────────────────────────────
    "gemini": {
        "url":     "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent",
        "headers": {"Content-Type": "application/json"},
        "model":   "gemini-2.0-flash-lite",
        "style":   "gemini",
        "api_key": GEMINI_KEY,   # passed as ?key= query param
    },
    # ── Phase 8: GitHub Models (Llama 3.3 70B via Azure AI Inference)
    "github": {
        "url":     "https://models.inference.ai.azure.com/chat/completions",
        "headers": {"Authorization": f"Bearer {GITHUB_MODELS_KEY}", "Content-Type": "application/json"},
        "model":   "Llama-3.3-70B-Instruct",
        "style":   "openai",
    },
    "cloudflare": {
        "url":     f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.1-8b-instruct",
        "headers": {"Authorization": f"Bearer {CF_KEY}", "Content-Type": "application/json"},
        "model":   None,
        "style":   "cloudflare",
    },
    "mistral": {
        "url":     "https://api.mistral.ai/v1/chat/completions",
        "headers": {"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
        "model":   "mistral-small-latest",
        "style":   "openai",
    },
    "cohere": {
        "url":     "https://api.cohere.ai/v2/chat",
        "headers": {"Authorization": f"Bearer {COHERE_KEY}", "Content-Type": "application/json"},
        "model":   "command-r",
        "style":   "cohere",
    },
}

# Updated fallback order: Cerebras → NVIDIA → Gemini → GitHub → CF → Mistral → Cohere
DEFAULT_ORDER = ["cerebras", "nvidia", "gemini", "github", "cloudflare", "mistral", "cohere"]

# ─────────────────────────────────────────────────────────────────────
#  RATE LIMIT TRACKER
# ─────────────────────────────────────────────────────────────────────

_RATE_LIMITED        : dict = {}
_RATE_LIMIT_COOLDOWN : int  = 60


def is_rate_limited(provider_name: str) -> bool:
    if provider_name in _RATE_LIMITED:
        if time.time() - _RATE_LIMITED[provider_name] < _RATE_LIMIT_COOLDOWN:
            print(f"  [{provider_name.upper()}] Skipping — cooldown active")
            return True
        del _RATE_LIMITED[provider_name]
    return False


def mark_rate_limited(provider_name: str) -> None:
    _RATE_LIMITED[provider_name] = time.time()
    print(f"  [{provider_name.upper()}] Rate limited — cooldown {_RATE_LIMIT_COOLDOWN}s")


# ─────────────────────────────────────────────────────────────────────
#  call_premium_ai() — master function with automatic fallback
#  Phase 8: added "gemini" style handler
# ─────────────────────────────────────────────────────────────────────

def call_premium_ai(
    prompt:     str,
    system:     str = "You are thirdyAgent2, a financial intelligence AI. Be concise, data-driven, and direct.",
    preferred:  str = "cerebras",
    max_tokens: int = 400,
) -> str | None:
    """
    Call an AI provider with automatic fallback.
    Returns the response string, or None if all providers fail.
    Providers are skipped if their key is empty (graceful degradation).
    """
    order = [preferred] + [p for p in DEFAULT_ORDER if p != preferred]

    for provider_name in order:
        if is_rate_limited(provider_name):
            continue

        cfg = PROVIDERS.get(provider_name)
        if not cfg:
            continue

        # Skip providers with no API key configured
        style = cfg["style"]
        if style == "openai":
            # Extract key from Authorization header
            auth = cfg["headers"].get("Authorization", "Bearer ")
            key  = auth.replace("Bearer ", "").strip()
            if not key:
                continue
        elif style == "gemini":
            if not cfg.get("api_key"):
                continue
        elif style == "cloudflare":
            if not CF_KEY or not CF_ACCOUNT:
                continue
        elif style == "cohere":
            if not COHERE_KEY:
                continue

        try:
            if style == "openai":
                # Standard OpenAI-compatible endpoint (Cerebras, NVIDIA, GitHub, Mistral)
                payload = {
                    "model":      cfg["model"],
                    "messages":   [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt}
                    ],
                    "max_tokens":  max_tokens,
                    "temperature": 0.4,
                }
                resp = requests.post(cfg["url"], headers=cfg["headers"], json=payload, timeout=20)
                r    = resp.json()
                if resp.status_code == 429:
                    mark_rate_limited(provider_name)
                    continue
                if "error" in r:
                    print(f"  [{provider_name.upper()}] Error: {str(r['error'])[:80]}")
                    continue
                reply = r.get("choices", [{}])[0].get("message", {}).get("content", "")

            elif style == "gemini":
                # Google Gemini API (key as query param, different body format)
                url = f"{cfg['url']}?key={cfg['api_key']}"
                payload = {
                    "system_instruction": {
                        "parts": [{"text": system}]
                    },
                    "contents": [
                        {"role": "user", "parts": [{"text": prompt}]}
                    ],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature":     0.4,
                    }
                }
                resp = requests.post(url, headers=cfg["headers"], json=payload, timeout=20)
                r    = resp.json()
                if resp.status_code == 429:
                    mark_rate_limited(provider_name)
                    continue
                if resp.status_code != 200:
                    print(f"  [GEMINI] Error {resp.status_code}: {str(r)[:80]}")
                    continue
                # Gemini returns candidates[0].content.parts[0].text
                reply = ""
                for candidate in r.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        reply += part.get("text", "")
                reply = reply.strip()

            elif style == "cloudflare":
                payload = {
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                }
                resp = requests.post(cfg["url"], headers=cfg["headers"], json=payload, timeout=20)
                r    = resp.json()
                if resp.status_code == 429:
                    mark_rate_limited(provider_name)
                    continue
                if not r.get("success"):
                    print(f"  [CLOUDFLARE] Failed: {str(r.get('errors',''))[:60]}")
                    continue
                reply = r.get("result", {}).get("response", "")

            elif style == "cohere":
                payload = {
                    "model":      cfg["model"],
                    "messages":   [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                }
                resp = requests.post(cfg["url"], headers=cfg["headers"], json=payload, timeout=20)
                r    = resp.json()
                if resp.status_code == 429:
                    mark_rate_limited(provider_name)
                    continue
                if resp.status_code != 200:
                    print(f"  [COHERE] Error {resp.status_code}: {str(r)[:60]}")
                    continue
                reply = r.get("message", {}).get("content", [{}])[0].get("text", "")

            else:
                continue

            if reply and reply.strip():
                print(f"  [AI] Reply via {provider_name.upper()} ({cfg.get('model','?')})")
                return reply.strip()

        except Exception as e:
            print(f"  [{provider_name.upper()}] Exception: {e}")
            continue

    print("  [AI] All providers failed — using built-in fallback")
    return None


# ─────────────────────────────────────────────────────────────────────
#  ASYNC HELPER
# ─────────────────────────────────────────────────────────────────────

def fetch_all(url_map: dict, timeout: int = 6) -> dict:
    """Fetch multiple URLs simultaneously. url_map = {"key": (url, params_or_None)}"""
    results: dict = {}

    def fetch_one(key: str, url: str, params):
        try:
            r = (
                requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "thirdyAgent2/1.0"})
                if params
                else requests.get(url, timeout=timeout, headers={"User-Agent": "thirdyAgent2/1.0"})
            )
            return key, r.json()
        except Exception as e:
            print(f"  [ASYNC] {key} failed: {e}")
            return key, None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_one, key, url, params): key
            for key, (url, params) in url_map.items()
        }
        for future in as_completed(futures):
            key, data = future.result()
            results[key] = data

    return results


# ─────────────────────────────────────────────────────────────────────
#  RSI CALCULATOR
# ─────────────────────────────────────────────────────────────────────

def calculate_rsi(prices: list, period: int = 14) -> float | None:
    """Calculate RSI from list of prices. Returns RSI 0-100 or None."""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def get_rsi_for_coin(coin_id: str) -> tuple:
    """Fetch 14-day OHLC and compute RSI. Returns (rsi_value, signal_str)."""
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": "14"},
            timeout=8
        ).json()
        closes = [candle[4] for candle in r if len(candle) >= 5]
        rsi    = calculate_rsi(closes)
        if rsi is None:
            return None, "N/A"
        if rsi >= 70:
            signal = f"Overbought 🔴 ({rsi:.1f})"
        elif rsi <= 30:
            signal = f"Oversold 🟢 ({rsi:.1f})"
        else:
            signal = f"Neutral ⚪ ({rsi:.1f})"
        return rsi, signal
    except Exception:
        return None, "N/A"


# ─────────────────────────────────────────────────────────────────────
#  SKILL 1: crypto_intelligence (0.25 USDC)
# ─────────────────────────────────────────────────────────────────────

def handle_crypto_intelligence(params: dict) -> dict:
    """Multi-source crypto intelligence — 3 async sources + Cerebras AI"""
    coin = params.get("coin", "bitcoin").lower()

    url_map = {
        "price":     (
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin}"
            f"&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
            None
        ),
        "feargreed": ("https://api.alternative.me/fng/?limit=1", None),
        "trending":  ("https://api.coingecko.com/api/v3/search/trending", None),
    }
    print(f"  [CRYPTO_INTEL] Async fetching 3 sources for {coin}...")
    raw = fetch_all(url_map, timeout=6)

    price_data = (raw.get("price") or {}).get(coin, {})
    fear_greed = ((raw.get("feargreed") or {}).get("data", [{}]))[0]
    trending   = [c["item"]["name"] for c in ((raw.get("trending") or {}).get("coins", []))[:3]]

    price    = price_data.get("usd", "N/A")
    change   = price_data.get("usd_24h_change", 0)
    mcap     = price_data.get("usd_market_cap", 0)
    fg_value = fear_greed.get("value", "N/A")
    fg_class = fear_greed.get("value_classification", "N/A")
    trend_str = ", ".join(trending) if trending else "N/A"

    prompt = (
        f"Analyze: {coin.upper()} ${price:,} | 24h: {change:.2f}% | "
        f"MCap: ${mcap:,.0f} | Fear/Greed: {fg_value}/100 ({fg_class}) | "
        f"Trending with: {trend_str}. "
        f"Give 3-4 sentence intelligence report. No disclaimers."
    )

    analysis = call_premium_ai(prompt, preferred="cerebras")
    if not analysis:
        analysis = f"{coin.upper()} at ${price} ({change:+.2f}% 24h). Sentiment: {fg_class}."

    return {
        "result": (
            f"📊 [CRYPTO INTELLIGENCE] {coin.upper()}\n"
            f"- Price      : ${price:,} USD\n"
            f"- 24h Change : {change:+.2f}%\n"
            f"- Sentiment  : {fg_class} ({fg_value}/100)\n"
            f"- Trending   : {trend_str}\n"
            f"\n🤖 [AI ANALYSIS]\n{analysis}"
        ),
        "data": {
            "coin": coin, "price_usd": price, "change_24h": change,
            "fear_greed": fg_value, "sentiment": fg_class,
            "trending": trending, "ai_analysis": analysis,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 2: defi_yield_finder (0.50 USDC)
# ─────────────────────────────────────────────────────────────────────

def handle_defi_yield_finder(params: dict) -> dict:
    """Find best DeFi yields with NVIDIA NIM AI risk analysis"""
    min_apy = float(params.get("min_apy", 3.0))
    chain   = params.get("chain", "all").lower()

    pools: list = []
    try:
        r = requests.get("https://yields.llama.fi/pools", timeout=10).json()
        filtered = [
            p for p in r.get("data", [])
            if p.get("apy", 0) >= min_apy
            and p.get("tvlUsd", 0) >= 1_000_000
            and (chain == "all" or p.get("chain", "").lower() == chain)
        ]
        filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
        pools = filtered[:5]
    except Exception as e:
        print(f"  [DEFI] DeFiLlama failed: {e}")

    if not pools:
        return {
            "result": f"No DeFi pools found (APY ≥ {min_apy}%, TVL ≥ $1M). Try lowering min_apy.",
            "data":   {"pools": [], "min_apy": min_apy}
        }

    pool_lines = [
        f"{i}. {p.get('symbol','?')} on {p.get('project','?')} ({p.get('chain','?')}) "
        f"— APY: {p.get('apy',0):.1f}% — TVL: ${p.get('tvlUsd',0):,.0f}"
        for i, p in enumerate(pools, 1)
    ]
    prompt = (
        f"Analyze these DeFi yield opportunities (risk level + 1 sentence each):\n"
        f"{chr(10).join(pool_lines)}\n"
        f"Focus: smart contract risk, protocol age, TVL stability. Concise."
    )
    analysis = call_premium_ai(prompt, preferred="nvidia")
    if not analysis:
        analysis = "Risk analysis unavailable. Always DYOR before investing in DeFi."

    result_lines = ["💎 [DEFI YIELD FINDER] Top Opportunities\n"]
    for p in pools:
        result_lines.append(
            f"- {p.get('symbol','?')} | {p.get('project','?')} | {p.get('chain','?')}\n"
            f"  APY: {p.get('apy',0):.1f}% | TVL: ${p.get('tvlUsd',0):,.0f}\n"
        )
    result_lines.append(f"\n🤖 [AI RISK ANALYSIS]\n{analysis}")
    result_lines.append(f"\nData: DeFiLlama | Min APY: {min_apy}%")

    return {
        "result": "\n".join(result_lines),
        "data":   {
            "pools": [
                {"symbol": p.get("symbol"), "project": p.get("project"),
                 "chain": p.get("chain"), "apy": p.get("apy"), "tvl_usd": p.get("tvlUsd")}
                for p in pools
            ],
            "min_apy": min_apy, "ai_analysis": analysis,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 3: market_signal (0.50 USDC)
# ─────────────────────────────────────────────────────────────────────

def handle_market_signal(params: dict) -> dict:
    """AI-powered BUY/SELL/HOLD signal from 6 data sources"""
    asset     = params.get("asset", "bitcoin").lower()
    timeframe = params.get("timeframe", "24h")

    aliases = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "doge": "dogecoin", "ada": "cardano", "xrp": "ripple",
        "bnb": "binancecoin", "avax": "avalanche-2",
    }
    coin_id = aliases.get(asset, asset)

    print(f"  [MARKET_SIGNAL] Async fetching 4 sources for {asset}...")

    url_map = {
        "price":     (
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            f"&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true",
            None
        ),
        "feargreed": ("https://api.alternative.me/fng/?limit=3", None),
        "dex":       (f"https://api.dexscreener.com/latest/dex/search?q={asset}", None),
        "reddit":    (
            "https://www.reddit.com/r/CryptoCurrency/search.json",
            {"q": asset, "sort": "hot", "limit": 5, "t": "day"}
        ),
    }
    raw = fetch_all(url_map, timeout=7)

    price_data = (raw.get("price") or {}).get(coin_id, {})
    price      = price_data.get("usd", 0)
    change_24h = price_data.get("usd_24h_change", 0)
    volume_24h = price_data.get("usd_24h_vol", 0)
    mcap       = price_data.get("usd_market_cap", 0)

    fg_data  = (raw.get("feargreed") or {}).get("data", [{}])
    fg_today = fg_data[0].get("value", "50") if fg_data else "50"
    fg_class = fg_data[0].get("value_classification", "Neutral") if fg_data else "Neutral"
    fg_trend = (
        "improving" if len(fg_data) > 1
        and int(fg_data[0].get("value", "50")) > int(fg_data[1].get("value", "50"))
        else "declining"
    )

    dex_pairs     = (raw.get("dex") or {}).get("pairs", [])[:3]
    total_dex_vol = sum(float(p.get("volume", {}).get("h24", 0) or 0) for p in dex_pairs)
    total_dex_liq = sum(float(p.get("liquidity", {}).get("usd", 0) or 0) for p in dex_pairs)

    reddit_posts = []
    reddit_sentiment = "Neutral"
    bull_count = bear_count = 0
    try:
        posts = (raw.get("reddit") or {}).get("data", {}).get("children", [])
        reddit_posts = [p["data"].get("title", "") for p in posts[:5] if p.get("data")]
        bull_kw = ["bull", "moon", "pump", "buy", "green", "up", "rally", "surge"]
        bear_kw = ["bear", "dump", "sell", "crash", "down", "red", "drop", "fear"]
        bull_count = sum(1 for t in reddit_posts for w in bull_kw if w in t.lower())
        bear_count = sum(1 for t in reddit_posts for w in bear_kw if w in t.lower())
        reddit_sentiment = "Bullish" if bull_count > bear_count else "Bearish" if bear_count > bull_count else "Neutral"
    except Exception:
        pass

    rsi_value, rsi_signal = get_rsi_for_coin(coin_id)

    prompt = (
        f"Asset: {asset.upper()} | Timeframe: {timeframe}\n"
        f"Price: ${price:,.2f} ({change_24h:+.2f}% 24h) | Vol: ${volume_24h:,.0f}\n"
        f"MCap: ${mcap:,.0f}\n"
        f"Fear/Greed: {fg_today}/100 ({fg_class}, {fg_trend})\n"
        f"RSI 14: {rsi_value or 'N/A'} — {rsi_signal}\n"
        f"DEX Liquidity: ${total_dex_liq:,.0f} | DEX Vol: ${total_dex_vol:,.0f}\n"
        f"Reddit: {reddit_sentiment} ({bull_count}↑ {bear_count}↓)\n\n"
        f"Provide: 1.SIGNAL:[BUY/SELL/HOLD] 2.CONFIDENCE:[Low/Med/High] "
        f"3.REASONING(2 sentences) 4.RISK(1 sentence) 5.TARGET for {timeframe}"
    )

    analysis = call_premium_ai(
        prompt,
        system="You are thirdyAgent2's signal engine. Give clear, data-backed trading signals.",
        preferred="cerebras",
        max_tokens=350,
    )

    signal_label = "HOLD 🟡"
    if analysis:
        upper = analysis.upper()
        if "SIGNAL: BUY" in upper or "1. BUY" in upper or "SIGNAL:BUY" in upper:
            signal_label = "BUY 🟢"
        elif "SIGNAL: SELL" in upper or "1. SELL" in upper or "SIGNAL:SELL" in upper:
            signal_label = "SELL 🔴"

    if not analysis:
        score = 0
        if change_24h > 2:  score += 1
        if change_24h < -2: score -= 1
        if int(fg_today) < 30: score += 1
        if int(fg_today) > 70: score -= 1
        if rsi_value and rsi_value < 35: score += 1
        if rsi_value and rsi_value > 65: score -= 1
        if reddit_sentiment == "Bullish": score += 1
        if reddit_sentiment == "Bearish": score -= 1
        if score >= 2:
            signal_label = "BUY 🟢"
            analysis = f"Math signal: {score} bullish indicators across 6 sources."
        elif score <= -2:
            signal_label = "SELL 🔴"
            analysis = f"Math signal: {abs(score)} bearish indicators across 6 sources."
        else:
            signal_label = "HOLD 🟡"
            analysis = f"Mixed signals (score {score}). No clear directional bias."

    return {
        "result": (
            f"📡 [MARKET SIGNAL] {asset.upper()} — {timeframe}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 SIGNAL     : {signal_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Price      : ${price:,.2f} ({change_24h:+.2f}% 24h)\n"
            f"😱 Fear/Greed : {fg_today}/100 ({fg_class}, {fg_trend})\n"
            f"📊 RSI 14     : {rsi_signal}\n"
            f"💬 Reddit     : {reddit_sentiment} ({bull_count}↑ {bear_count}↓)\n"
            f"💧 DEX Liq    : ${total_dex_liq:,.0f}\n"
            f"\n🤖 [AI ANALYSIS]\n{analysis}\n"
            f"\n⚠️  DYOR — Not financial advice."
        ),
        "data": {
            "asset": asset, "signal": signal_label, "price": price,
            "change_24h": change_24h, "fear_greed": fg_today,
            "rsi": rsi_value, "reddit_sentiment": reddit_sentiment,
            "ai_analysis": analysis, "timeframe": timeframe, "sources": 6,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 4: news_alpha (0.25 USDC)
# ─────────────────────────────────────────────────────────────────────

def handle_news_alpha(params: dict) -> dict:
    """Real-time news impact analysis using Mistral AI"""
    topic  = params.get("topic", "bitcoin").lower()
    asset  = params.get("asset", topic)

    url_map = {
        "hn_top":    ("https://hacker-news.firebaseio.com/v0/topstories.json", None),
        "hn_new":    ("https://hacker-news.firebaseio.com/v0/newstories.json", None),
        "reddit_hot":(
            "https://www.reddit.com/r/CryptoCurrency/search.json",
            {"q": topic, "sort": "hot", "limit": 8, "t": "day"}
        ),
        "price":     (
            f"https://api.coingecko.com/api/v3/simple/price?ids={asset}&vs_currencies=usd&include_24hr_change=true",
            None
        ),
    }
    raw = fetch_all(url_map, timeout=7)

    crypto_kw = [topic, "bitcoin", "ethereum", "crypto", "defi", "blockchain",
                 "token", "nft", "sec", "etf", "fed", "inflation", "regulation", "hack"]
    hn_stories: list = []
    for list_key in ["hn_top", "hn_new"]:
        if len(hn_stories) >= 5:
            break
        ids = (raw.get(list_key) or [])[:25]
        for sid in ids:
            if len(hn_stories) >= 5:
                break
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=3
                ).json()
                title = s.get("title", "")
                if any(k in title.lower() for k in crypto_kw):
                    hn_stories.append({"title": title, "score": s.get("score", 0)})
            except Exception:
                pass

    reddit_titles: list = []
    posts = (raw.get("reddit_hot") or {}).get("data", {}).get("children", [])
    for p in posts:
        title = p.get("data", {}).get("title", "")
        score = p.get("data", {}).get("score", 0)
        if title:
            reddit_titles.append({"title": title[:100], "score": score})
    reddit_titles = reddit_titles[:6]

    price_info = (raw.get("price") or {}).get(asset, {})
    price  = price_info.get("usd", "N/A")
    change = price_info.get("usd_24h_change", 0)

    all_headlines = (
        [f"[HN/{s['score']}pts] {s['title']}" for s in hn_stories[:4]] +
        [f"[Reddit/{r['score']}pts] {r['title']}" for r in reddit_titles[:4]]
    )
    if not all_headlines:
        all_headlines = [f"No major news for {topic} in last 24h"]

    prompt = (
        f"News impact analysis for {topic.upper()}. Price: ${price} ({change:+.2f}% 24h).\n\n"
        f"Headlines:\n" + "\n".join(all_headlines) +
        f"\n\nProvide: 1.IMPACT:[Bullish/Bearish/Neutral] 2.MAGNITUDE:[Low/Med/High] "
        f"3.SUMMARY(2 sentences) 4.PRICE_EFFECT(1 sentence) 5.KEY_RISK(1 sentence)"
    )

    analysis = call_premium_ai(prompt, preferred="mistral", max_tokens=350)
    if not analysis:
        analysis = (
            f"Found {len(all_headlines)} news items about {topic}. "
            f"Price is {change:+.2f}% in 24h. Review headlines for context."
        )

    result_lines = [
        f"📰 [NEWS ALPHA] {topic.upper()}",
        f"💰 Price: ${price} ({change:+.2f}% 24h)\n",
        f"📡 Latest Headlines:"
    ]
    for h in all_headlines[:6]:
        result_lines.append(f"  • {h}")
    result_lines += [
        f"\n🤖 [AI IMPACT ANALYSIS]\n{analysis}",
        f"\nSources: Hacker News + Reddit r/CryptoCurrency | Real-time",
    ]

    return {
        "result": "\n".join(result_lines),
        "data":   {
            "topic": topic, "price": price, "change_24h": change,
            "headlines": all_headlines, "ai_analysis": analysis,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 5: portfolio_analyzer (1.00 USDC)
# ─────────────────────────────────────────────────────────────────────

def handle_portfolio_analyzer(params: dict) -> dict:
    """Multi-asset portfolio AI analysis using NVIDIA NIM"""
    portfolio: dict = {}

    if params.get("assets"):
        raw_assets = params.get("assets")
        if isinstance(raw_assets, dict):
            portfolio = {k.lower(): float(v) for k, v in raw_assets.items()}
        elif isinstance(raw_assets, str):
            try:
                for pair in raw_assets.split(","):
                    if ":" in pair:
                        k, v = pair.strip().split(":")
                        portfolio[k.strip().lower()] = float(v.strip())
            except Exception:
                pass
    else:
        i = 1
        while params.get(f"asset{i}"):
            asset = params.get(f"asset{i}", "").lower()
            pct   = float(params.get(f"pct{i}", 0))
            if asset and pct > 0:
                portfolio[asset] = pct
            i += 1

    if not portfolio:
        portfolio = {"bitcoin": 50, "ethereum": 30, "solana": 20}

    total_pct = sum(portfolio.values())
    if total_pct == 0:
        return {"result": "Portfolio is empty.", "data": {}}
    portfolio = {k: round(v / total_pct * 100, 1) for k, v in portfolio.items()}

    print(f"  [PORTFOLIO] Analyzing: {portfolio}")

    aliases = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "doge": "dogecoin", "ada": "cardano", "xrp": "ripple",
        "bnb": "binancecoin", "avax": "avalanche-2",
    }
    coin_ids = [aliases.get(a, a) for a in portfolio.keys()]
    ids_str  = ",".join(coin_ids)

    url_map = {
        "prices":    (
            f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}"
            f"&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
            None
        ),
        "feargreed": ("https://api.alternative.me/fng/?limit=1", None),
    }
    raw = fetch_all(url_map, timeout=8)

    prices_data = raw.get("prices") or {}
    fg_data     = ((raw.get("feargreed") or {}).get("data", [{}]))[0]
    fg_value    = fg_data.get("value", "50")
    fg_class    = fg_data.get("value_classification", "Neutral")

    asset_rows: list  = []
    asset_lines: list = []
    total_weighted_change = 0.0

    for orig_name, pct in portfolio.items():
        coin_id    = aliases.get(orig_name, orig_name)
        asset_data = prices_data.get(coin_id, {})
        price      = asset_data.get("usd", 0)
        change_24h = asset_data.get("usd_24h_change", 0)
        mcap       = asset_data.get("usd_market_cap", 0)
        rsi_val, rsi_sig = get_rsi_for_coin(coin_id)

        total_weighted_change += (pct / 100) * change_24h
        asset_rows.append({
            "name": orig_name, "pct": pct, "price": price,
            "change24": change_24h, "mcap": mcap,
            "rsi": rsi_val, "rsi_sig": rsi_sig,
        })
        mcap_str = f"${mcap:,.0f}" if isinstance(mcap, (int, float)) and mcap > 0 else "N/A"
        asset_lines.append(
            f"• {orig_name.upper()} ({pct:.1f}%): ${price:,.4f} | "
            f"24h: {change_24h:+.2f}% | MCap: {mcap_str} | RSI: {rsi_sig}"
        )

    risk_score = 0
    for row in asset_rows:
        if abs(row.get("change24", 0)) > 5: risk_score += 1
        if row.get("rsi") and row["rsi"] > 70: risk_score += 1
        if row.get("rsi") and row["rsi"] < 30: risk_score -= 1

    risk_label = (
        "HIGH 🔴" if risk_score >= 3 else
        "MEDIUM 🟡" if risk_score >= 1 else
        "LOW 🟢"
    )
    num_assets  = len(portfolio)
    max_pct     = max(portfolio.values())
    div_score   = (
        "Well Diversified ✅"       if num_assets >= 5 and max_pct <= 40 else
        "Moderately Diversified 🟡" if num_assets >= 3 and max_pct <= 60 else
        "Concentrated ⚠️"
    )

    prompt = (
        f"Portfolio:\n" + "\n".join(asset_lines) +
        f"\n\n24h P&L: {total_weighted_change:+.2f}% (weighted) | "
        f"Risk: {risk_label} | Diversification: {div_score} | "
        f"F&G: {fg_value}/100 ({fg_class}) | Assets: {num_assets} | Largest: {max_pct:.1f}%\n\n"
        f"Provide: 1.HEALTH_SCORE(1-10+reason) 2.STRENGTHS 3.WEAKNESSES "
        f"4.REBALANCING(specific) 5.OUTLOOK(7d)"
    )

    analysis = call_premium_ai(
        prompt,
        system="You are thirdyAgent2's portfolio intelligence engine. Institutional-grade analysis.",
        preferred="nvidia",
        max_tokens=500,
    )
    if not analysis:
        analysis = (
            f"Portfolio 24h: {total_weighted_change:+.2f}%. "
            f"Risk: {risk_label}. {div_score}. Sentiment: {fg_class}."
        )

    result = [
        "💼 [PORTFOLIO ANALYZER]",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 Assets: {num_assets} | 24h P&L: {total_weighted_change:+.2f}%",
        f"🛡️  Risk: {risk_label} | {div_score}",
        f"😱 Market: {fg_class} ({fg_value}/100)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "\n📈 ASSET BREAKDOWN:",
    ]
    result.extend(asset_lines)
    result += [
        f"\n🤖 [AI ANALYSIS]\n{analysis}",
        "\n⚠️  DYOR — Not financial advice. | Sources: CoinGecko + DeFiLlama + RSI",
    ]

    return {
        "result": "\n".join(result),
        "data":   {
            "portfolio": portfolio, "assets": asset_rows,
            "portfolio_24h": total_weighted_change,
            "risk_level": risk_label, "diversification": div_score,
            "fear_greed": fg_value, "ai_analysis": analysis,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  REGISTRY
# ─────────────────────────────────────────────────────────────────────

AI_SKILLS = {
    "crypto_intelligence": handle_crypto_intelligence,
    "defi_yield_finder":   handle_defi_yield_finder,
    "market_signal":       handle_market_signal,
    "news_alpha":          handle_news_alpha,
    "portfolio_analyzer":  handle_portfolio_analyzer,
}

AI_PAID_SKILLS = {
    "crypto_intelligence": 0.25,
    "defi_yield_finder":   0.50,
    "market_signal":       0.50,
    "news_alpha":          0.25,
    "portfolio_analyzer":  1.00,
}
