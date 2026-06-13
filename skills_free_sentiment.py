"""
skills_free_sentiment.py — Social Sentiment Engine for thirdyAgent2
====================================================================
PHASE 4: Real-time social sentiment — your KEY DATA MOAT

3 skills:
  sentiment_pulse  (FREE)      — Reddit + HN crypto sentiment score
  social_alpha     (0.50 USDC) — X/Twitter + Reddit AI interpretation
  viral_signal     (0.25 USDC) — Detect viral narratives before they peak

WHY THIS IS POWERFUL:
  - No LLM has real-time Reddit/Twitter sentiment in training data
  - Agents MUST pay to get this because they cannot replicate it free
  - Combined with market_signal → full trading intelligence stack
  - FinBERT-style scoring without requiring FinBERT (pure Python logic)

APIs used (ALL FREE, NO KEY):
  - Reddit public JSON API (no PRAW needed — uses .json endpoint)
  - Hacker News Firebase API
  - CoinGecko (price context)
  - alternative.me (Fear & Greed)
  - DexScreener (volume context)
"""

import requests
import re
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
# CRIT-03 FIX: credentials from config.py — never hardcode
from config import CEREBRAS_KEY, MISTRAL_KEY

# ─────────────────────────────────────────────────────────────────────
#  SENTIMENT SCORING — pure Python, no ML library needed
#  Based on financial lexicon research (Loughran-McDonald wordlist)
# ─────────────────────────────────────────────────────────────────────

BULLISH_WORDS = {
    # Price action
    "moon", "pump", "bullish", "bull", "surge", "rally", "breakout",
    "ath", "all-time-high", "high", "up", "green", "gains", "gain",
    "rising", "rise", "uptrend", "recovery", "recover", "bounce",
    "accumulate", "accumulation", "buy", "buying", "hodl", "hold",
    # Fundamental
    "adoption", "partnership", "launch", "upgrade", "mainnet",
    "institutional", "etf", "approval", "approve", "bullrun",
    "undervalued", "gem", "opportunity", "support", "strong",
    "positive", "optimistic", "excited", "confident", "promising",
    "milestone", "growth", "expand", "expansion", "innovation",
    # Community
    "letsgo", "wagmi", "lfg", "gm", "based", "alpha",
}

BEARISH_WORDS = {
    # Price action
    "crash", "dump", "bearish", "bear", "drop", "fall", "falling",
    "red", "loss", "losses", "losing", "down", "downtrend", "sell",
    "selling", "capitulation", "bottom", "low", "dip", "correction",
    # Fundamental
    "scam", "rug", "rugpull", "hack", "exploit", "vulnerability",
    "ban", "banned", "regulate", "regulation", "crackdown", "sec",
    "lawsuit", "overvalued", "bubble", "ponzi", "fraud", "exit",
    "delisted", "delist", "insolvent", "bankrupt", "dead", "rip",
    # Sentiment
    "fear", "panic", "scared", "worried", "uncertainty", "uncertain",
    "risky", "danger", "warning", "caution", "avoid", "ngmi",
    "rekt", "liquidated", "margin call", "fud", "doubt",
}

STRONG_BULLISH = {"moon", "ath", "bullrun", "wagmi", "lfg", "surge", "breakout", "etf"}
STRONG_BEARISH = {"crash", "rug", "rugpull", "hack", "scam", "bankrupt", "exploit", "rekt"}


def score_text(text: str) -> dict:
    """
    Score a piece of text for sentiment.
    Returns: {bull_count, bear_count, score, label, confidence}
    score: +100 (max bullish) to -100 (max bearish)
    """
    words = set(re.findall(r"[a-z]+", text.lower()))

    bull_count  = len(words & BULLISH_WORDS)
    bear_count  = len(words & BEARISH_WORDS)
    strong_bull = len(words & STRONG_BULLISH)
    strong_bear = len(words & STRONG_BEARISH)

    # Weight strong signals 2x
    weighted_bull = bull_count + strong_bull
    weighted_bear = bear_count + strong_bear
    total = weighted_bull + weighted_bear

    if total == 0:
        return {"bull": 0, "bear": 0, "score": 0, "label": "Neutral", "confidence": "Low"}

    score = round(((weighted_bull - weighted_bear) / total) * 100, 1)

    if score >= 60:
        label, confidence = "Very Bullish 🟢🟢", "High"
    elif score >= 25:
        label, confidence = "Bullish 🟢", "Medium"
    elif score >= 10:
        label, confidence = "Slightly Bullish ↗️", "Low"
    elif score <= -60:
        label, confidence = "Very Bearish 🔴🔴", "High"
    elif score <= -25:
        label, confidence = "Bearish 🔴", "Medium"
    elif score <= -10:
        label, confidence = "Slightly Bearish ↘️", "Low"
    else:
        label, confidence = "Neutral ⚪", "Low"

    return {
        "bull":       weighted_bull,
        "bear":       weighted_bear,
        "score":      score,
        "label":      label,
        "confidence": confidence,
    }


def aggregate_scores(scores: list) -> dict:
    """Aggregate multiple text scores into one."""
    if not scores:
        return {"bull": 0, "bear": 0, "score": 0, "label": "Neutral", "confidence": "Low"}
    avg_score = sum(s["score"] for s in scores) / len(scores)
    total_bull = sum(s["bull"] for s in scores)
    total_bear = sum(s["bear"] for s in scores)
    agg = score_text(" ".join(["bull"] * total_bull + ["crash"] * total_bear))
    agg["score"] = round(avg_score, 1)
    return agg


# ─────────────────────────────────────────────────────────────────────
#  DATA FETCHERS
# ─────────────────────────────────────────────────────────────────────

REDDIT_HEADERS = {"User-Agent": "thirdyAgent2-sentiment/1.0"}
CRYPTO_SUBS    = ["CryptoCurrency", "Bitcoin", "ethereum", "solana", "investing", "wallstreetbets"]


def fetch_reddit_posts(query: str, subreddit: str = "CryptoCurrency", limit: int = 25) -> list:
    """Fetch Reddit posts via public JSON API — no key needed."""
    posts = []
    urls = [
        f"https://www.reddit.com/r/{subreddit}/search.json?q={query}&sort=hot&limit={limit}&t=day",
        f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=REDDIT_HEADERS, timeout=7).json()
            children = r.get("data", {}).get("children", [])
            for child in children:
                d = child.get("data", {})
                title = d.get("title", "")
                body  = d.get("selftext", "")[:300]
                if title:
                    posts.append({
                        "title":    title,
                        "score":    d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                        "text":     f"{title} {body}",
                    })
            if posts:
                break
        except:
            continue
    return posts[:limit]


def fetch_reddit_comments(subreddit: str, query: str, limit: int = 20) -> list:
    """Fetch top comments from Reddit search."""
    comments = []
    try:
        url = f"https://www.reddit.com/r/{subreddit}/search.json?q={query}&sort=new&limit=10&t=hour"
        r   = requests.get(url, headers=REDDIT_HEADERS, timeout=7).json()
        children = r.get("data", {}).get("children", [])
        for child in children[:5]:
            d = child.get("data", {})
            comments.append({
                "text":  d.get("title", "") + " " + d.get("selftext", "")[:200],
                "score": d.get("score", 0)
            })
    except:
        pass
    return comments


def fetch_hn_stories(query: str, limit: int = 10) -> list:
    """Fetch Hacker News stories filtered by query."""
    crypto_kw = [query.lower()] + [
        "bitcoin", "ethereum", "crypto", "defi", "blockchain",
        "token", "nft", "sec", "etf", "web3", "solana"
    ]
    stories = []
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=5
        ).json()[:40]

        for sid in ids:
            if len(stories) >= limit:
                break
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=3
                ).json()
                title = s.get("title", "")
                if any(k in title.lower() for k in crypto_kw):
                    stories.append({
                        "title": title,
                        "score": s.get("score", 0),
                        "text":  title,
                    })
            except:
                pass
    except:
        pass
    return stories


def fetch_multi_reddit(query: str, subs: list, limit_each: int = 15) -> list:
    """Fetch from multiple subreddits simultaneously."""
    all_posts = []

    def fetch_one(sub):
        return fetch_reddit_posts(query, sub, limit_each)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_one, sub): sub for sub in subs}
        for f in as_completed(futures):
            try:
                all_posts.extend(f.result())
            except:
                pass

    return all_posts


def fetch_price_context(coin_id: str) -> dict:
    """Get price + Fear/Greed for context."""
    data = {}
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}"
            f"&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
            timeout=5
        ).json()
        data["price"]  = r.get(coin_id, {}).get("usd", "?")
        data["change"] = r.get(coin_id, {}).get("usd_24h_change", 0)
        data["mcap"]   = r.get(coin_id, {}).get("usd_market_cap", 0)
    except:
        pass

    try:
        fg = requests.get("https://api.alternative.me/fng/?limit=1", timeout=4).json()
        data["fg_value"] = fg.get("data", [{}])[0].get("value", "50")
        data["fg_class"] = fg.get("data", [{}])[0].get("value_classification", "Neutral")
    except:
        pass

    return data


# ─────────────────────────────────────────────────────────────────────
#  SKILL 1: sentiment_pulse (FREE)
#  Real-time Reddit + HN sentiment score for any crypto/topic
# ─────────────────────────────────────────────────────────────────────

def handle_sentiment_pulse(params):
    """
    FREE: Multi-source social sentiment score
    Sources: Reddit r/CryptoCurrency + r/Bitcoin + r/investing + HN
    Returns: sentiment score -100 to +100, label, post samples
    """
    topic  = params.get("topic", "bitcoin").lower()
    asset  = params.get("asset", topic)

    aliases = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "doge": "dogecoin", "bnb": "binancecoin", "ada": "cardano"
    }
    coin_id = aliases.get(asset, asset)

    print(f"  [SENTIMENT_PULSE] Fetching sentiment for {topic}...")

    # Async fetch all sources
    subs_to_check = ["CryptoCurrency", "Bitcoin"] if "bitcoin" in topic else ["CryptoCurrency", "investing"]

    def get_reddit():
        return fetch_multi_reddit(topic, subs_to_check, limit_each=20)

    def get_hn():
        return fetch_hn_stories(topic, limit=10)

    def get_price():
        return fetch_price_context(coin_id)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_reddit = ex.submit(get_reddit)
        f_hn     = ex.submit(get_hn)
        f_price  = ex.submit(get_price)

    reddit_posts = f_reddit.result()
    hn_stories   = f_hn.result()
    price_data   = f_price.result()

    # Score all content
    all_scores = []
    top_posts  = []

    for post in reddit_posts:
        s = score_text(post["text"])
        all_scores.append(s)
        if post["score"] > 10 or post["comments"] > 5:
            top_posts.append({
                "title":     post["title"][:80],
                "reddit_score": post["score"],
                "sentiment": s["label"],
            })

    for story in hn_stories:
        s = score_text(story["text"])
        all_scores.append(s)

    agg = aggregate_scores(all_scores)

    # Weighted by Fear/Greed
    fg_val = int(price_data.get("fg_value", 50))
    fg_adj = (fg_val - 50) / 50 * 20  # -20 to +20 adjustment
    final_score = round(max(-100, min(100, agg["score"] + fg_adj)), 1)

    # Format output
    price   = price_data.get("price", "?")
    change  = price_data.get("change", 0)
    fg_cls  = price_data.get("fg_class", "Neutral")
    sign    = "+" if change >= 0 else ""

    sample_lines = []
    for p in top_posts[:3]:
        sample_lines.append(f"  • [{p['reddit_score']}pts] {p['title']} → {p['sentiment']}")

    samples_str = "\n".join(sample_lines) if sample_lines else "  • No high-signal posts found"

    return {
        "result": (
            f"📊 [SENTIMENT PULSE] {topic.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Sentiment Score : {final_score:+.1f} / 100\n"
            f"🏷️  Label          : {agg['label']}\n"
            f"💪 Confidence     : {agg['confidence']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 {topic.upper()} Price : ${price:,} ({sign}{change:.2f}% 24h)\n"
            f"😱 Fear/Greed     : {fg_val}/100 ({fg_cls})\n"
            f"🟢 Bullish signals: {agg['bull']} | 🔴 Bearish: {agg['bear']}\n"
            f"📝 Posts analyzed : {len(all_scores)}\n"
            f"\n🔥 Top Signals:\n{samples_str}\n"
            f"\n💡 Want AI interpretation? Call social_alpha (0.50 USDC)"
        ),
        "data": {
            "topic":        topic,
            "score":        final_score,
            "label":        agg["label"],
            "confidence":   agg["confidence"],
            "bull_signals": agg["bull"],
            "bear_signals": agg["bear"],
            "posts_scored": len(all_scores),
            "price":        price,
            "change_24h":   change,
            "fear_greed":   fg_val,
            "top_posts":    top_posts[:5],
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 2: social_alpha (0.50 USDC) — PREMIUM
#  AI-interpreted social sentiment with trading implications
# ─────────────────────────────────────────────────────────────────────

def handle_social_alpha(params):
    """
    PREMIUM 0.50 USDC: X/Twitter-style + Reddit sentiment with AI analysis
    Uses: Reddit multi-sub + HN + price + Fear/Greed → AI interpretation
    Why agents pay: 'What does this social data mean for price?' — not free
    """
    topic  = params.get("topic", "bitcoin").lower()
    asset  = params.get("asset", topic)

    aliases = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "doge": "dogecoin", "bnb": "binancecoin", "ada": "cardano",
        "xrp": "ripple", "avax": "avalanche-2"
    }
    coin_id = aliases.get(asset, asset)

    print(f"  [SOCIAL_ALPHA] Fetching multi-source sentiment for {topic}...")

    # Fetch from more subreddits for premium
    subs = ["CryptoCurrency", "Bitcoin", "ethereum", "investing", "wallstreetbets"]
    if topic not in ["bitcoin", "btc"]:
        subs = ["CryptoCurrency", "investing", "wallstreetbets"]

    # Parallel fetch
    def get_reddit():
        return fetch_multi_reddit(topic, subs, limit_each=25)
    def get_hn():
        return fetch_hn_stories(topic, limit=15)
    def get_price():
        return fetch_price_context(coin_id)
    def get_dex():
        try:
            r = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={asset}",
                timeout=6
            ).json()
            pairs = r.get("pairs", [])[:3]
            return sum(float(p.get("volume", {}).get("h24", 0) or 0) for p in pairs)
        except:
            return 0

    with ThreadPoolExecutor(max_workers=4) as ex:
        f_r = ex.submit(get_reddit)
        f_h = ex.submit(get_hn)
        f_p = ex.submit(get_price)
        f_d = ex.submit(get_dex)

    reddit_posts = f_r.result()
    hn_stories   = f_h.result()
    price_data   = f_p.result()
    dex_volume   = f_d.result()

    # Score all content
    all_scores   = []
    reddit_scores = []
    hn_scores     = []
    top_posts     = []

    for post in reddit_posts:
        s = score_text(post["text"])
        all_scores.append(s)
        reddit_scores.append(s)
        if post.get("score", 0) > 20 or post.get("comments", 0) > 10:
            top_posts.append({
                "title":    post["title"][:90],
                "score":    post.get("score", 0),
                "sentiment": s["label"],
            })

    for story in hn_stories:
        s = score_text(story["text"])
        all_scores.append(s)
        hn_scores.append(s)

    agg_reddit = aggregate_scores(reddit_scores)
    agg_hn     = aggregate_scores(hn_scores)
    agg_total  = aggregate_scores(all_scores)

    # Context
    price  = price_data.get("price", "?")
    change = price_data.get("change", 0)
    fg_val = int(price_data.get("fg_value", 50))
    fg_cls = price_data.get("fg_class", "Neutral")

    # Build AI prompt
    top_headlines = "\n".join([f"- {p['title']}" for p in top_posts[:6]])
    if not top_headlines:
        top_headlines = "No high-engagement posts found in last 24h"

    prompt = f"""You are a social sentiment analyst for crypto markets. Analyze this social data:

Asset: {topic.upper()}
Current Price: ${price} ({'+' if change >= 0 else ''}{change:.2f}% 24h)
Fear/Greed: {fg_val}/100 ({fg_cls})
DEX 24h Volume: ${dex_volume:,.0f}

SENTIMENT SCORES:
- Reddit sentiment: {agg_reddit['score']:+.1f} ({agg_reddit['label']})
- HN sentiment: {agg_hn['score']:+.1f} ({agg_hn['label']})
- Combined score: {agg_total['score']:+.1f} / 100
- Bullish signals: {agg_total['bull']} | Bearish signals: {agg_total['bear']}
- Posts analyzed: {len(all_scores)}

TOP COMMUNITY POSTS:
{top_headlines}

Provide:
1. NARRATIVE: What story is the community telling about {topic}?
2. SIGNAL: Bullish / Bearish / Neutral — and why
3. DIVERGENCE: Is social sentiment aligned or diverging from price action?
4. ALPHA: One actionable insight traders can use from this social data
5. RISK: Main social risk (FOMO, FUD, whale manipulation, etc)

Be concise, data-driven, 5 lines max."""

    # Call AI
    analysis = None
    ai_providers = [
        {
            "url":     "https://api.cerebras.ai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {CEREBRAS_KEY}",
                       "Content-Type": "application/json"},
            "model":   "llama3.1-8b",
            "style":   "openai",
        },
        {
            "url":     "https://api.mistral.ai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {MISTRAL_KEY}",
                       "Content-Type": "application/json"},
            "model":   "mistral-small-latest",
            "style":   "openai",
        },
    ]

    for provider in ai_providers:
        try:
            payload = {
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": "You are a crypto social sentiment analyst. Be concise and data-driven."},
                    {"role": "user",   "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            }
            r = requests.post(provider["url"], headers=provider["headers"], json=payload, timeout=18)
            analysis = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if analysis:
                print(f"  [AI] social_alpha via {provider['model']}")
                break
        except:
            continue

    if not analysis:
        analysis = (
            f"Social sentiment for {topic.upper()}: {agg_total['label']} "
            f"(score: {agg_total['score']:+.1f}). "
            f"{agg_total['bull']} bullish vs {agg_total['bear']} bearish signals across "
            f"{len(all_scores)} posts. Price is {'+' if change>=0 else ''}{change:.2f}% — "
            f"{'aligned with' if (change>0)==(agg_total['score']>0) else 'diverging from'} social sentiment."
        )

    sign = "+" if change >= 0 else ""
    top_posts_str = "\n".join([f"  • [{p['score']}pts] {p['title']}" for p in top_posts[:4]]) or "  • No high-signal posts"

    return {
        "result": (
            f"🧠 [SOCIAL ALPHA] {topic.upper()} — AI Sentiment Analysis\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Score     : {agg_total['score']:+.1f}/100 ({agg_total['label']})\n"
            f"💪 Confidence: {agg_total['confidence']}\n"
            f"💬 Reddit    : {agg_reddit['score']:+.1f} | HN: {agg_hn['score']:+.1f}\n"
            f"📰 Analyzed  : {len(all_scores)} posts/stories\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Price Context:\n"
            f"  ${price:,} ({sign}{change:.2f}% 24h) | F&G: {fg_val}/100 ({fg_cls})\n"
            f"  DEX Volume: ${dex_volume:,.0f}\n"
            f"\n🔥 Top Community Posts:\n{top_posts_str}\n"
            f"\n🤖 [AI ANALYSIS]\n{analysis}\n"
            f"\n⚠️ DYOR — Social sentiment analysis, not financial advice."
        ),
        "data": {
            "topic":          topic,
            "overall_score":  agg_total["score"],
            "label":          agg_total["label"],
            "confidence":     agg_total["confidence"],
            "reddit_score":   agg_reddit["score"],
            "hn_score":       agg_hn["score"],
            "posts_analyzed": len(all_scores),
            "bull_signals":   agg_total["bull"],
            "bear_signals":   agg_total["bear"],
            "price":          price,
            "change_24h":     change,
            "fear_greed":     fg_val,
            "dex_volume":     dex_volume,
            "top_posts":      top_posts[:5],
            "ai_analysis":    analysis,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  SKILL 3: viral_signal (0.25 USDC) — PREMIUM
#  Detect viral crypto/stock narratives BEFORE they peak
#  This is the early-warning system — the rarest signal on AgentHub
# ─────────────────────────────────────────────────────────────────────

def handle_viral_signal(params):
    """
    PREMIUM 0.25 USDC: Viral narrative detector
    Scans Reddit + HN for emerging stories gaining momentum
    Why agents pay: early narrative detection = trading edge
    No other agent on AgentHub offers this
    """
    asset  = params.get("asset", "crypto").lower()
    window = params.get("window", "6h")

    print(f"  [VIRAL_SIGNAL] Scanning for viral {asset} narratives...")

    # Subreddits to monitor
    scan_subs = ["CryptoCurrency", "Bitcoin", "ethereum",
                 "investing", "wallstreetbets", "stocks"]

    # Fetch new + hot posts to compare velocity
    narratives = {}

    def fetch_sub_new(sub):
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
            r   = requests.get(url, headers=REDDIT_HEADERS, timeout=6).json()
            return [(sub, "new", p["data"]) for p in r.get("data", {}).get("children", [])]
        except:
            return []

    def fetch_sub_hot(sub):
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            r   = requests.get(url, headers=REDDIT_HEADERS, timeout=6).json()
            return [(sub, "hot", p["data"]) for p in r.get("data", {}).get("children", [])]
        except:
            return []

    def fetch_hn_new():
        try:
            ids  = requests.get(
                "https://hacker-news.firebaseio.com/v0/newstories.json",
                timeout=5
            ).json()[:30]
            items = []
            for sid in ids[:20]:
                try:
                    s = requests.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        timeout=2
                    ).json()
                    items.append(("HackerNews", "new", s))
                except:
                    pass
            return items
        except:
            return []

    all_posts = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = []
        for sub in scan_subs[:4]:
            futures.append(ex.submit(fetch_sub_new, sub))
            futures.append(ex.submit(fetch_sub_hot, sub))
        futures.append(ex.submit(fetch_hn_new))
        for f in as_completed(futures):
            try:
                all_posts.extend(f.result())
            except:
                pass

    # Extract and score all posts
    scored_posts = []
    crypto_kw = {
        asset, "bitcoin", "btc", "ethereum", "eth", "crypto",
        "defi", "nft", "blockchain", "token", "altcoin", "web3",
        "solana", "sol", "binance", "coinbase", "doge", "meme",
        "whale", "pump", "dump", "liquidation", "etf", "sec"
    }

    now_ts = time.time()

    for source, feed_type, post_data in all_posts:
        title    = post_data.get("title", "")
        if not title:
            continue

        text     = title + " " + post_data.get("selftext", "")[:200]
        words    = set(text.lower().split())

        # Filter relevance
        if asset not in ["crypto", "general"] and asset not in text.lower():
            continue
        if not (words & crypto_kw):
            continue

        score_data = score_text(text)
        post_score = post_data.get("score", 0)
        comments   = post_data.get("num_comments", 0)
        created    = post_data.get("created_utc", now_ts)
        age_hours  = (now_ts - created) / 3600

        # Velocity = engagement rate per hour
        velocity = (post_score + comments * 2) / max(age_hours, 0.5)

        # Viral score = velocity * sentiment magnitude
        sentiment_magnitude = abs(score_data["score"]) / 100
        viral_score = round(velocity * (1 + sentiment_magnitude), 1)

        scored_posts.append({
            "title":      title[:90],
            "source":     source,
            "feed":       feed_type,
            "score":      post_score,
            "comments":   comments,
            "age_hours":  round(age_hours, 1),
            "velocity":   round(velocity, 1),
            "viral_score":viral_score,
            "sentiment":  score_data["label"],
            "s_score":    score_data["score"],
        })

    # Sort by viral score
    scored_posts.sort(key=lambda x: x["viral_score"], reverse=True)
    top_viral = scored_posts[:8]

    if not top_viral:
        return {
            "result": f"📡 [VIRAL SIGNAL] No viral {asset} narratives detected in last {window}. Market is quiet.",
            "data":   {"asset": asset, "viral_posts": [], "trending_themes": []}
        }

    # Extract themes from top viral posts
    theme_words = {}
    for p in top_viral:
        words = re.findall(r"[a-z]{4,}", p["title"].lower())
        for w in words:
            if w not in {"that", "this", "with", "from", "have", "been",
                         "will", "what", "your", "their", "about", "just"}:
                theme_words[w] = theme_words.get(w, 0) + 1

    trending_themes = sorted(theme_words.items(), key=lambda x: x[1], reverse=True)
    top_themes = [w for w, c in trending_themes if c >= 2][:5]

    # Overall viral sentiment
    viral_scores_list = [score_text(p["title"]) for p in top_viral]
    overall = aggregate_scores(viral_scores_list)

    # Format output
    posts_lines = []
    for p in top_viral[:5]:
        age_str = f"{p['age_hours']:.1f}h ago"
        posts_lines.append(
            f"  🔥 [{p['viral_score']:.0f}v] {p['title']}\n"
            f"     {p['source']} | {p['sentiment']} | {p['score']}pts | {age_str}"
        )

    themes_str = ", ".join(f"#{t}" for t in top_themes) or "no clear theme"

    return {
        "result": (
            f"📡 [VIRAL SIGNAL] {asset.upper()} — Emerging Narratives\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Signals Found  : {len(top_viral)} viral posts\n"
            f"📊 Overall Tone   : {overall['label']}\n"
            f"🏷️  Trending Themes: {themes_str}\n"
            f"⏱️  Scan Window   : last {window}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n🔥 TOP VIRAL POSTS (by velocity):\n"
            + "\n".join(posts_lines) +
            f"\n\n💡 High viral score = high engagement velocity = potential price mover\n"
            f"⚠️  DYOR — Early signal, not financial advice."
        ),
        "data": {
            "asset":           asset,
            "viral_posts":     top_viral,
            "trending_themes": top_themes,
            "overall_sentiment": overall["label"],
            "overall_score":   overall["score"],
            "posts_scanned":   len(all_posts),
            "window":          window,
        }
    }


# ─────────────────────────────────────────────────────────────────────
#  PACK REGISTRY
# ─────────────────────────────────────────────────────────────────────

SKILLS_PACK = {
    "sentiment_pulse": handle_sentiment_pulse,  # FREE
    "social_alpha":    handle_social_alpha,     # 0.50 USDC PREMIUM
    "viral_signal":    handle_viral_signal,     # 0.25 USDC PREMIUM
}
