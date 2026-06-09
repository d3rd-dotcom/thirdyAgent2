"""
skills_free_business.py — Business & Economy skill pack for thirdyAgent2
5 skills: global_economy, market_scanner, forex_tracker, startup_intel, business_news
All free, zero API keys needed.
"""
import requests
import datetime
import urllib.parse


def handle_global_economy(params):
    """
    Global economic indicators: GDP, inflation, interest rates
    APIs: World Bank API (no key) + frankfurter.app (no key)
    """
    country     = params.get("country", "PH")
    country_name = params.get("country_name", "Philippines")
    data        = {}

    # World Bank — GDP per capita
    try:
        r = requests.get(
            f"https://api.worldbank.org/v2/country/{country}/indicator/NY.GDP.PCAP.CD",
            params={"format": "json", "mrv": 1},
            timeout=8
        ).json()
        if len(r) > 1 and r[1]:
            entry = r[1][0]
            data["gdp_per_capita"] = entry.get("value")
            data["gdp_year"]       = entry.get("date")
    except: pass

    # World Bank — Inflation
    try:
        r = requests.get(
            f"https://api.worldbank.org/v2/country/{country}/indicator/FP.CPI.TOTL.ZG",
            params={"format": "json", "mrv": 1},
            timeout=8
        ).json()
        if len(r) > 1 and r[1]:
            entry = r[1][0]
            data["inflation"] = entry.get("value")
            data["inflation_year"] = entry.get("date")
    except: pass

    # World Bank — Unemployment
    try:
        r = requests.get(
            f"https://api.worldbank.org/v2/country/{country}/indicator/SL.UEM.TOTL.ZS",
            params={"format": "json", "mrv": 1},
            timeout=8
        ).json()
        if len(r) > 1 and r[1]:
            entry = r[1][0]
            data["unemployment"] = entry.get("value")
    except: pass

    # Major currency rates
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "EUR,GBP,JPY,PHP,SGD,AUD"},
            timeout=5
        ).json()
        data["rates"] = r.get("rates", {})
    except: pass

    gdp    = f"${data['gdp_per_capita']:,.0f}" if isinstance(data.get("gdp_per_capita"), (int,float)) else "N/A"
    inf    = f"{data['inflation']:.1f}%" if isinstance(data.get("inflation"), (int,float)) else "N/A"
    unemp  = f"{data['unemployment']:.1f}%" if isinstance(data.get("unemployment"), (int,float)) else "N/A"
    rates  = data.get("rates", {})
    fx_str = " | ".join([f"{k}={v:.4f}" for k,v in list(rates.items())[:4]]) or "N/A"

    return {
        "result": (
            f"📊 [GLOBAL ECONOMY] — {country_name} ({country})\n"
            f"💰 GDP/Capita   : {gdp} ({data.get('gdp_year','?')})\n"
            f"📈 Inflation    : {inf} ({data.get('inflation_year','?')})\n"
            f"👷 Unemployment : {unemp}\n"
            f"💱 USD Rates    : {fx_str}"
        ),
        "data": data
    }


def handle_market_scanner(params):
    """
    Stock market scanner: top movers + index data using yfinance
    Free, no API key — pulls real Yahoo Finance data
    """
    mode    = params.get("mode", "indices")
    symbol  = params.get("symbol", "AAPL")
    data    = {}

    if mode == "quote":
        # Single stock quote via Yahoo Finance unofficial API
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "5d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8
            ).json()
            meta   = r.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price  = meta.get("regularMarketPrice", "N/A")
            prev   = meta.get("previousClose", price)
            change = ((price - prev) / prev * 100) if isinstance(price, (int,float)) and prev else 0
            arrow  = "📈" if change >= 0 else "📉"
            data["quote"] = {
                "symbol":   meta.get("symbol", symbol),
                "price":    price,
                "change":   change,
                "currency": meta.get("currency", "USD"),
                "exchange": meta.get("exchangeName", "?"),
                "high":     meta.get("regularMarketDayHigh", "N/A"),
                "low":      meta.get("regularMarketDayLow", "N/A"),
                "volume":   meta.get("regularMarketVolume", "N/A"),
            }
            q = data["quote"]
            return {
                "result": (
                    f"📈 [MARKET SCANNER] — {q['symbol']} ({q['exchange']})\n"
                    f"{arrow} Price  : {q['currency']} {q['price']:,.2f} ({change:+.2f}%)\n"
                    f"📊 High   : {q['high']} | Low: {q['low']}\n"
                    f"📦 Volume : {q['volume']:,}" if isinstance(q['volume'], int) else f"📦 Volume: {q['volume']}"
                ),
                "data": data
            }
        except Exception as e:
            return {"result": f"Quote failed for {symbol}: {e}", "data": {}}

    else:  # indices
        symbols = {
            "S&P 500":  "^GSPC",
            "NASDAQ":   "^IXIC",
            "DOW":      "^DJI",
            "VIX":      "^VIX",
            "Gold":     "GC=F",
            "Oil WTI":  "CL=F",
        }
        lines = ["📊 [MARKET SCANNER] — Major Indices"]
        for name, sym in symbols.items():
            try:
                r = requests.get(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                    params={"interval": "1d", "range": "2d"},
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=6
                ).json()
                meta   = r.get("chart", {}).get("result", [{}])[0].get("meta", {})
                price  = meta.get("regularMarketPrice", "?")
                prev   = meta.get("previousClose", price)
                change = ((price - prev) / prev * 100) if isinstance(price, (int,float)) and prev else 0
                arrow  = "📈" if change >= 0 else "📉"
                data[name] = {"price": price, "change": change}
                lines.append(f"{arrow} {name:10}: {price:>10,.2f} ({change:+.2f}%)"
                             if isinstance(price, (int,float)) else f"• {name}: {price}")
            except: pass

        return {
            "result": "\n".join(lines),
            "data": data
        }


def handle_forex_tracker(params):
    """
    Real-time forex rates + currency conversion + historical rates
    API: frankfurter.app (no key, ECB official data, 170+ currencies)
    """
    base    = params.get("base", "USD")
    targets = params.get("targets", "EUR,GBP,JPY,PHP,SGD,AUD,CAD,CHF")
    amount  = float(params.get("amount", 1))
    mode    = params.get("mode", "rates")
    data    = {}

    if mode == "convert":
        target = params.get("target", "PHP")
        try:
            r = requests.get(
                "https://api.frankfurter.app/latest",
                params={"from": base, "to": target, "amount": amount},
                timeout=5
            ).json()
            rate   = r.get("rates", {}).get(target, "?")
            result = rate if isinstance(rate, (int,float)) else "?"
            data["conversion"] = {
                "from": base, "to": target,
                "amount": amount, "result": result, "rate": rate
            }
            return {
                "result": (
                    f"💱 [FOREX CONVERTER]\n"
                    f"{amount:,.2f} {base} = {result:,.4f} {target}\n"
                    f"Rate: 1 {base} = {rate} {target}\n"
                    f"Source: European Central Bank (ECB)"
                ),
                "data": data
            }
        except Exception as e:
            return {"result": f"Conversion failed: {e}", "data": {}}

    elif mode == "historical":
        date = params.get("date", (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"))
        try:
            r = requests.get(
                f"https://api.frankfurter.app/{date}",
                params={"from": base, "to": targets},
                timeout=5
            ).json()
            data["historical"] = r.get("rates", {})
            data["date"]       = r.get("date", date)
            lines = [f"📅 [FOREX HISTORICAL] — {data['date']}",
                     f"Base: {base}"]
            for k, v in data["historical"].items():
                lines.append(f"• {k}: {v:.4f}")
            return {"result": "\n".join(lines), "data": data}
        except Exception as e:
            return {"result": f"Historical rates failed: {e}", "data": {}}

    else:  # live rates
        try:
            r = requests.get(
                "https://api.frankfurter.app/latest",
                params={"from": base, "to": targets},
                timeout=5
            ).json()
            data["rates"] = r.get("rates", {})
            data["date"]  = r.get("date", "?")
            lines = [
                f"💱 [FOREX TRACKER] — Live Rates",
                f"Base: {base} | Date: {data['date']}",
                f"Source: European Central Bank (ECB)\n"
            ]
            for currency, rate in data["rates"].items():
                bar_len = min(int(rate / max(data["rates"].values()) * 20), 20) if data["rates"] else 0
                bar     = "█" * bar_len
                lines.append(f"• {currency:4}: {rate:>12,.4f}  {bar}")
            return {"result": "\n".join(lines), "data": data}
        except Exception as e:
            return {"result": f"Forex rates failed: {e}", "data": {}}


def handle_startup_intel(params):
    """
    Startup & VC intelligence from public sources
    APIs: Hacker News (YC launches, no key) + GitHub trending (no key)
    """
    topic  = params.get("topic", "fintech")
    data   = {}

    # Hacker News — Show HN (startup launches)
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/showstories.json",
            timeout=5
        ).json()[:30]
        keywords = topic.lower().split(",") + [
            "launch", "startup", "saas", "api", "agent", "ai", "fintech",
            "crypto", "blockchain", "defi", "trading"
        ]
        launches = []
        for sid in ids:
            if len(launches) >= 5: break
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=3
                ).json()
                title = s.get("title", "")
                if any(k in title.lower() for k in keywords):
                    launches.append({
                        "title":    title,
                        "score":    s.get("score", 0),
                        "comments": s.get("descendants", 0),
                        "url":      s.get("url", "")[:70]
                    })
            except: pass
        data["launches"] = launches
    except: pass

    # GitHub trending repos (new startups open-source)
    try:
        r = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q":        f"{topic} in:description created:>2026-01-01",
                "sort":     "stars",
                "order":    "desc",
                "per_page": 4
            },
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=8
        ).json()
        data["repos"] = [
            {
                "name":  repo.get("full_name","?"),
                "stars": repo.get("stargazers_count", 0),
                "desc":  str(repo.get("description",""))[:70],
                "lang":  repo.get("language","?"),
            }
            for repo in r.get("items", [])[:4]
        ]
    except: pass

    lines = [f"🚀 [STARTUP INTEL] — {topic}"]

    if data.get("launches"):
        lines.append("\n📣 Recent Launches (Show HN):")
        for l in data["launches"]:
            lines.append(f"• [{l['score']}pts, {l['comments']} comments] {l['title']}")

    if data.get("repos"):
        lines.append("\n⭐ New GitHub Projects (2026):")
        for r in data["repos"]:
            lines.append(f"• ⭐{r['stars']:,} | {r['name']} ({r['lang']})\n  {r['desc']}")

    if not data.get("launches") and not data.get("repos"):
        lines.append(f"\nNo recent startup intel found for '{topic}'. Try: ai, fintech, crypto, saas")

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_business_news(params):
    """
    Business & financial news from multiple free sources
    APIs: Hacker News (no key) + DEV.to (no key) + Reddit (no key)
    """
    topic   = params.get("topic", "economy")
    region  = params.get("region", "global")
    data    = {}

    # Hacker News — business/finance stories
    try:
        ids      = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=5
        ).json()[:40]
        keywords = topic.lower().split(",") + [
            "economy", "market", "stock", "bond", "fed", "inflation",
            "gdp", "recession", "earnings", "ipo", "acquisition", "revenue"
        ]
        hn_biz = []
        for sid in ids:
            if len(hn_biz) >= 5: break
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=3
                ).json()
                title = s.get("title", "")
                if any(k in title.lower() for k in keywords):
                    hn_biz.append({
                        "title": title,
                        "score": s.get("score", 0),
                        "url":   s.get("url", "")[:80]
                    })
            except: pass
        data["hn"] = hn_biz
    except: pass

    # Reddit — r/economics or r/investing posts (public JSON)
    sub = "investing" if "invest" in topic.lower() else "economics"
    try:
        r = requests.get(
            f"https://www.reddit.com/r/{sub}/hot.json",
            params={"limit": 5},
            headers={"User-Agent": "thirdyAgent2/1.0"},
            timeout=8
        ).json()
        posts = r.get("data", {}).get("children", [])
        data["reddit"] = [
            {
                "title":  p["data"].get("title","?")[:90],
                "score":  p["data"].get("score", 0),
                "comments": p["data"].get("num_comments", 0),
            }
            for p in posts
            if not p["data"].get("stickied", False)
        ][:5]
    except: pass

    lines = [f"📰 [BUSINESS NEWS] — {topic} ({region})"]

    if data.get("hn"):
        lines.append("\n💻 Hacker News Business:")
        for s in data["hn"]:
            lines.append(f"• [{s['score']}pts] {s['title']}")

    if data.get("reddit"):
        lines.append(f"\n📱 r/{sub}:")
        for p in data["reddit"][:4]:
            lines.append(f"• [{p['score']}pts, {p['comments']} comments] {p['title']}")

    if not data.get("hn") and not data.get("reddit"):
        lines.append("\nNo business news found. Try: economy, markets, stocks, crypto, investing")

    return {
        "result": "\n".join(lines),
        "data": data
    }


SKILLS_PACK = {
    "global_economy": handle_global_economy,
    "market_scanner": handle_market_scanner,
    "forex_tracker":  handle_forex_tracker,
    "startup_intel":  handle_startup_intel,
    "business_news":  handle_business_news,
}
