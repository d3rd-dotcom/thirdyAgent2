"""
skills_free_crypto.py — Crypto & Web3 skill pack for thirdyAgent2
UPGRADED v2 (May 2026):
  - dex_scanner: DexScreener API (no key, 300 req/min, 2M+ tokens, 80+ chains)
  - crypto_news_feed: cryptocurrency.cv free news API (no key) + HN filter
  - btc_network_intel: Mempool.space blocks + fees + blockchain.info
  - defi_pulse: DeFiLlama pools + chain TVL rankings
  - crypto_pulse: CoinGecko + Fear/Greed + Trending (upgraded output)
"""
import requests
import datetime


def handle_crypto_pulse(params):
    """Multi-source crypto snapshot: CoinGecko + Fear/Greed + Trending"""
    coin = params.get("coin", "bitcoin").lower()
    results = {}

    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin}&vs_currencies=usd&include_24hr_change=true"
            f"&include_market_cap=true&include_24hr_vol=true",
            timeout=5
        ).json()
        results["coingecko"] = r.get(coin, {})
    except: pass

    try:
        fg = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json()
        results["fear_greed"] = fg.get("data", [{}])[0]
    except: pass

    try:
        tr = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=5).json()
        results["trending"] = [c["item"]["name"] for c in tr.get("coins", [])[:3]]
    except: pass

    price    = results.get("coingecko", {}).get("usd", "N/A")
    change   = results.get("coingecko", {}).get("usd_24h_change", 0)
    vol      = results.get("coingecko", {}).get("usd_24h_vol", 0)
    mcap     = results.get("coingecko", {}).get("usd_market_cap", 0)
    fg_class = results.get("fear_greed", {}).get("value_classification", "N/A")
    fg_score = results.get("fear_greed", {}).get("value", "?")
    trending = ", ".join(results.get("trending", [])) or "N/A"
    arrow    = "📈" if change >= 0 else "📉"
    sign     = "+" if change >= 0 else ""
    mood     = "bullish 🚀" if change >= 3 else "bearish 🔻" if change <= -3 else "neutral ➡️"

    return {
        "result": (
            f"📊 [CRYPTO PULSE] {coin.upper()}\n"
            f"{arrow} Price     : ${price:,} USD ({sign}{change:.2f}% 24h)\n"
            f"📦 Market Cap: ${mcap:,.0f}\n"
            f"💹 24h Vol   : ${vol:,.0f}\n"
            f"😱 Sentiment : {fg_class} ({fg_score}/100)\n"
            f"🔥 Trending  : {trending}\n"
            f"📌 Outlook   : {mood}"
        ),
        "data": results
    }


def handle_btc_network_intel(params):
    """BTC network: Mempool.space fees + blocks + blockchain.info stats"""
    data = {}

    try:
        fees = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=5).json()
        data["fees"] = fees
    except: pass

    try:
        blocks = requests.get("https://mempool.space/api/v1/blocks", timeout=5).json()
        if blocks:
            b = blocks[0]
            data["latest_block"] = {
                "height":   b.get("height", "?"),
                "tx_count": b.get("tx_count", "?"),
                "size":     round(b.get("size", 0) / 1024, 1),
            }
    except: pass

    try:
        stats = requests.get("https://blockchain.info/stats?format=json", timeout=5).json()
        data["hashrate"]   = stats.get("hash_rate", "N/A")
        data["difficulty"] = stats.get("difficulty", "N/A")
        data["tx_per_day"] = stats.get("n_tx", "N/A")
        data["total_btc"]  = round(stats.get("totalbc", 0) / 100_000_000, 2)
    except: pass

    low  = data.get("fees", {}).get("economyFee", "N/A")
    med  = data.get("fees", {}).get("halfHourFee", "N/A")
    fast = data.get("fees", {}).get("fastestFee", "N/A")
    blk  = data.get("latest_block", {})

    return {
        "result": (
            f"⛓️ [BTC NETWORK INTEL]\n"
            f"🔧 Fees        : Low={low} | Med={med} | Fast={fast} sat/vB\n"
            f"📦 Latest Block: #{blk.get('height','?')} | "
            f"{blk.get('tx_count','?')} txs | {blk.get('size','?')} KB\n"
            f"⛏️  Hashrate    : {data.get('hashrate','N/A')}\n"
            f"📊 Difficulty  : {data.get('difficulty','N/A')}\n"
            f"💰 Total Mined : {data.get('total_btc','?')} BTC\n"
            f"📈 Tx/Day      : {data.get('tx_per_day','N/A')}"
        ),
        "data": data
    }


def handle_defi_pulse(params):
    """DeFi pulse: DeFiLlama top pools + chain TVL rankings"""
    chain   = params.get("chain", "all").lower()
    min_apy = float(params.get("min_apy", 5.0))
    data    = {}

    try:
        r = requests.get("https://yields.llama.fi/pools", timeout=10).json()
        pools = [
            p for p in r.get("data", [])
            if p.get("apy", 0) >= min_apy and p.get("tvlUsd", 0) >= 500_000
        ]
        if chain != "all":
            pools = [p for p in pools if p.get("chain", "").lower() == chain]
        pools.sort(key=lambda x: x.get("apy", 0), reverse=True)
        data["pools"] = pools[:5]
    except: pass

    try:
        chains_r = requests.get("https://api.llama.fi/v2/chains", timeout=6).json()
        top_chains = sorted(chains_r, key=lambda x: x.get("tvl", 0), reverse=True)[:3]
        data["top_chains"] = [f"{c.get('name','?')}: ${c.get('tvl',0):,.0f}" for c in top_chains]
    except: pass

    if not data.get("pools"):
        return {
            "result": f"No pools found (APY ≥ {min_apy}%, TVL ≥ $500K). Try lowering min_apy.",
            "data": {}
        }

    lines = [
        f"• {p.get('symbol','?')} | {p.get('project','?')} ({p.get('chain','?')}) "
        f"| APY: {p.get('apy',0):.1f}% | TVL: ${p.get('tvlUsd',0):,.0f}"
        for p in data["pools"]
    ]
    chains_str = " | ".join(data.get("top_chains", []))

    return {
        "result": (
            f"💎 [DEFI PULSE] Top Pools (APY ≥ {min_apy}%):\n"
            + "\n".join(lines)
            + f"\n\n🏆 Top Chains by TVL: {chains_str}"
        ),
        "data": data
    }


def handle_dex_scanner(params):
    """
    NEW v2: Real-time DEX scanner — DexScreener API (NO KEY NEEDED)
    Covers 2M+ tokens, 80+ chains, 300+ DEXs — 300 req/min free
    """
    query = params.get("query", "bitcoin")
    chain = params.get("chain", "").lower()
    data  = {}

    try:
        r     = requests.get(
            f"https://api.dexscreener.com/latest/dex/search?q={query}",
            timeout=8
        ).json()
        pairs = r.get("pairs", [])
        if chain:
            pairs = [p for p in pairs if p.get("chainId", "").lower() == chain]
        pairs.sort(
            key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0),
            reverse=True
        )
        data["pairs"] = pairs[:5]
    except Exception as e:
        data["error"] = str(e)

    try:
        boosted = requests.get(
            "https://api.dexscreener.com/token-boosts/top/v1",
            timeout=6
        ).json()
        if isinstance(boosted, list):
            data["boosted"] = [
                t.get("description", t.get("tokenAddress", "?"))[:50]
                for t in boosted[:3]
            ]
    except: pass

    if not data.get("pairs"):
        return {
            "result": f"No DEX pairs found for '{query}'. Try: bitcoin, pepe, bonk, wif",
            "data": data
        }

    lines = []
    for p in data["pairs"]:
        sym     = p.get("baseToken", {}).get("symbol", "?")
        chain_id = p.get("chainId", "?")
        dex     = p.get("dexId", "?")
        price   = p.get("priceUsd", "?")
        change  = p.get("priceChange", {}).get("h24", "?")
        vol     = float(p.get("volume", {}).get("h24", 0) or 0)
        liq     = float(p.get("liquidity", {}).get("usd", 0) or 0)
        lines.append(
            f"• {sym} [{chain_id}/{dex}]\n"
            f"  ${price} | 24h: {change}% | Vol: ${vol:,.0f} | Liq: ${liq:,.0f}"
        )

    boosted_str = ", ".join(data.get("boosted", [])) or "N/A"

    return {
        "result": (
            f"🔍 [DEX SCANNER] '{query}' across all chains:\n"
            + "\n".join(lines)
            + f"\n\n🚀 Currently Boosted: {boosted_str}"
        ),
        "data": data
    }


def handle_crypto_news_feed(params):
    """
    NEW v2: Real-time crypto news
    Sources: cryptocurrency.cv (no key) + Hacker News crypto filter
    """
    topic = params.get("topic", "bitcoin").lower()
    data  = {}

    # cryptocurrency.cv — free, no key, covers BTC/ETH/DeFi/SOL/altcoins
    try:
        r = requests.get(
            f"https://cryptocurrency.cv/api/v1/news/recent",
            params={"query": topic, "limit": 5},
            timeout=7
        ).json()
        articles = r if isinstance(r, list) else r.get("articles", r.get("data", []))
        data["news"] = [
            {
                "title":  str(a.get("title", "?"))[:90],
                "source": str(a.get("source", {}).get("name", a.get("source", "?")))[:30]
                         if isinstance(a.get("source"), dict)
                         else str(a.get("source", "?"))[:30],
            }
            for a in articles[:5]
            if a.get("title")
        ]
    except: pass

    # Hacker News crypto filter fallback
    try:
        crypto_kw = ["bitcoin","ethereum","crypto","defi","solana","blockchain","web3","nft","btc","eth","token"]
        ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=5).json()[:30]
        hn  = []
        for sid in ids:
            if len(hn) >= 3: break
            try:
                s = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=3).json()
                title = s.get("title", "")
                if any(k in title.lower() for k in crypto_kw):
                    hn.append({"title": title, "score": s.get("score", 0)})
            except: pass
        data["hn"] = hn
    except: pass

    lines = []
    if data.get("news"):
        lines.append(f"📰 Crypto News — {topic.upper()}:")
        for a in data["news"]:
            lines.append(f"• [{a['source']}] {a['title']}")
    if data.get("hn"):
        lines.append("\n💻 Hacker News:")
        for s in data["hn"]:
            lines.append(f"• [{s['score']}pts] {s['title']}")
    if not lines:
        lines.append("No crypto news available right now.")

    return {
        "result": f"📡 [CRYPTO NEWS FEED]\n" + "\n".join(lines),
        "data": data
    }


SKILLS_PACK = {
    "crypto_pulse":      handle_crypto_pulse,
    "btc_network_intel": handle_btc_network_intel,
    "defi_pulse":        handle_defi_pulse,
    "dex_scanner":       handle_dex_scanner,      # NEW — DexScreener no key
    "crypto_news_feed":  handle_crypto_news_feed, # NEW — cryptocurrency.cv no key
}
