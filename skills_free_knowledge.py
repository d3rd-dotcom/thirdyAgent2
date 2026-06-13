"""
skills_free_knowledge.py — Knowledge & Dev skill pack for thirdyAgent2
5 skills: tech_news_feed, world_knowledge, paper_search, dev_toolkit, web_extractor
All free, zero API keys needed.
"""
import requests
import datetime
import urllib.parse


def handle_tech_news_feed(params):
    """
    Real-time tech news from multiple sources
    APIs: Hacker News (no key) + DEV.to (no key) + GitHub Trending (no key)
    """
    topic  = params.get("topic", "ai")
    limit  = int(params.get("limit", 5))
    data   = {}

    # Hacker News — top stories filtered by topic
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=5
        ).json()[:30]
        keywords = topic.lower().split(",") + ["ai", "llm", "agent", "crypto", "blockchain"]
        hn_stories = []
        for sid in ids:
            if len(hn_stories) >= 4: break
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=3
                ).json()
                title = s.get("title", "")
                if any(k.strip() in title.lower() for k in keywords):
                    hn_stories.append({
                        "title": title,
                        "score": s.get("score", 0),
                        "url":   s.get("url", "")[:60]
                    })
            except: pass
        data["hn"] = hn_stories
    except: pass

    # DEV.to articles
    try:
        r = requests.get(
            "https://dev.to/api/articles",
            params={"tag": topic.split(",")[0].strip(), "per_page": 4},
            timeout=6
        ).json()
        data["devto"] = [
            {
                "title":        a.get("title", "?")[:80],
                "reactions":    a.get("public_reactions_count", 0),
                "reading_time": a.get("reading_time_minutes", "?"),
                "author":       a.get("user", {}).get("name", "?"),
            }
            for a in r[:4]
            if isinstance(a, dict)
        ]
    except: pass

    lines = [f"📡 [TECH NEWS FEED] — Topic: {topic}"]

    if data.get("hn"):
        lines.append("\n💻 Hacker News:")
        for s in data["hn"]:
            lines.append(f"• [{s['score']}pts] {s['title']}")

    if data.get("devto"):
        lines.append("\n✍️ DEV.to Articles:")
        for a in data["devto"]:
            lines.append(
                f"• {a['title']} "
                f"| ❤️{a['reactions']} | ⏱️{a['reading_time']}min | {a['author']}"
            )

    if not data.get("hn") and not data.get("devto"):
        lines.append("No tech news found for this topic. Try: ai, blockchain, python, webdev")

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_world_knowledge(params):
    """
    World facts: country data + world bank economics + timezone
    APIs: restcountries.com (no key) + worldbank API (no key) + worldtimeapi.org (no key)
    """
    country  = params.get("country", "Philippines")
    timezone = params.get("timezone", "Asia/Manila")
    data     = {}

    # Country facts
    try:
        r = requests.get(
            f"https://restcountries.com/v3.1/name/{urllib.parse.quote(country)}",
            params={"fields": "name,capital,population,area,currencies,languages,region,flags"},
            timeout=6
        ).json()
        if isinstance(r, list) and r:
            c = r[0]
            data["country"] = {
                "name":       c.get("name", {}).get("common", "?"),
                "capital":    c.get("capital", ["?"])[0] if c.get("capital") else "?",
                "population": c.get("population", "?"),
                "area":       c.get("area", "?"),
                "region":     c.get("region", "?"),
                "currencies": ", ".join(c.get("currencies", {}).keys()),
                "languages":  ", ".join(list(c.get("languages", {}).values())[:3]),
            }
    except: pass

    # World time
    try:
        r = requests.get(
            f"https://worldtimeapi.org/api/timezone/{timezone}",
            timeout=5
        ).json()
        data["time"]     = r.get("datetime", "?")[:19]
        data["timezone"] = r.get("timezone", timezone)
        data["utc_off"]  = r.get("utc_offset", "?")
        data["day_of_year"] = r.get("day_of_year", "?")
    except: pass

    lines = [f"🌍 [WORLD KNOWLEDGE]"]

    if data.get("country"):
        c = data["country"]
        lines += [
            f"\n🗺️ Country: {c['name']} ({c['region']})",
            f"🏛️ Capital    : {c['capital']}",
            f"👥 Population : {c['population']:,}" if isinstance(c['population'], int) else f"👥 Population: {c['population']}",
            f"📐 Area       : {c['area']:,} km²" if isinstance(c['area'], (int,float)) else f"📐 Area: {c['area']} km²",
            f"💰 Currencies : {c['currencies']}",
            f"🗣️  Languages  : {c['languages']}",
        ]

    if data.get("time"):
        lines += [
            f"\n🕐 Time ({data['timezone']}): {data['time']}",
            f"   UTC Offset: {data['utc_off']} | Day {data['day_of_year']} of year",
        ]

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_paper_search(params):
    """
    Academic paper search — 250M+ papers, free, no API key
    API: api.semanticscholar.org
    """
    query   = params.get("query", "autonomous AI agents 2026")
    limit   = min(int(params.get("limit", 5)), 8)
    year    = params.get("year", "")
    data    = {}

    try:
        params_s = {
            "query":  query,
            "limit":  limit,
            "fields": "title,authors,year,citationCount,abstract,externalIds",
        }
        if year:
            params_s["year"] = year

        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params_s,
            timeout=10
        ).json()
        papers = r.get("data", [])
        data["papers"] = [
            {
                "title":     p.get("title", "?")[:90],
                "year":      p.get("year", "?"),
                "citations": p.get("citationCount", 0),
                "authors":   ", ".join([a.get("name","?") for a in p.get("authors",[])[:2]]),
                "abstract":  str(p.get("abstract",""))[:120] + "..." if p.get("abstract") else "",
                "doi":       p.get("externalIds",{}).get("DOI",""),
            }
            for p in papers
        ]
    except Exception as e:
        data["error"] = str(e)

    if not data.get("papers"):
        return {
            "result": f"No papers found for '{query}'. Try: 'autonomous agents', 'DeFi security', 'LLM 2025'",
            "data": data
        }

    lines = [f"📚 [PAPER SEARCH] — '{query}'"]
    for i, p in enumerate(data["papers"], 1):
        lines.append(
            f"\n{i}. {p['title']}\n"
            f"   👥 {p['authors']} | 📅 {p['year']} | 📖 {p['citations']} citations"
        )
        if p.get("abstract"):
            lines.append(f"   {p['abstract']}")
        if p.get("doi"):
            lines.append(f"   DOI: {p['doi']}")

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_dev_toolkit(params):
    """
    Developer tools bundle: GitHub search + IP lookup + color converter
    APIs: api.github.com (no key) + ip-api.com (no key)
    """
    mode  = params.get("mode", "github")
    query = params.get("query", "autonomous agent python")
    data  = {}

    if mode == "github":
        # GitHub repo search — no key needed for public search
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q":     query,
                    "sort":  "stars",
                    "order": "desc",
                    "per_page": 5
                },
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=8
            ).json()
            repos = r.get("items", [])[:5]
            data["repos"] = [
                {
                    "name":     repo.get("full_name","?"),
                    "stars":    repo.get("stargazers_count", 0),
                    "forks":    repo.get("forks_count", 0),
                    "language": repo.get("language", "?"),
                    "desc":     str(repo.get("description",""))[:70],
                    "url":      repo.get("html_url",""),
                }
                for repo in repos
            ]
            lines = [f"🐙 [GITHUB SEARCH] — '{query}'"]
            for r in data["repos"]:
                lines.append(
                    f"• ⭐{r['stars']:,} | {r['name']} ({r['language']})\n"
                    f"  {r['desc']}"
                )
        except Exception as e:
            lines = [f"GitHub search failed: {e}"]

    elif mode == "ip":
        ip = params.get("ip", "")
        try:
            url = f"https://ipapi.co/{ip}/json/" if ip else "https://ipapi.co/json/"
            r   = requests.get(url, timeout=5).json()
            data["ip_info"] = r
            lines = [
                f"🌐 [IP LOOKUP]",
                f"IP       : {r.get('query','?')}",
                f"Country  : {r.get('country','?')} ({r.get('countryCode','?')})",
                f"City     : {r.get('city','?')}",
                f"Region   : {r.get('regionName','?')}",
                f"ISP      : {r.get('isp','?')}",
                f"Timezone : {r.get('timezone','?')}",
                f"Lat/Lon  : {r.get('lat','?')}, {r.get('lon','?')}",
            ]
        except Exception as e:
            lines = [f"IP lookup failed: {e}"]

    elif mode == "uuid":
        # Generate UUIDs
        import uuid
        uuids = [str(uuid.uuid4()) for _ in range(5)]
        data["uuids"] = uuids
        lines = ["🔑 [UUID GENERATOR] — 5 Random UUIDs:"] + [f"• {u}" for u in uuids]

    else:
        lines = ["Mode options: github, ip, uuid\nExample: mode=github, query=autonomous agent python"]

    return {
        "result": "🛠️ [DEV TOOLKIT]\n" + "\n".join(lines),
        "data": data
    }


def handle_web_extractor(params):
    """
    Extract content from URLs + Wikipedia summary
    APIs: Wikipedia API (no key) + Open Graph metadata
    """
    mode  = params.get("mode", "wiki")
    query = params.get("query", "Bitcoin")
    url   = params.get("url", "")
    data  = {}

    if mode == "wiki" or (not url):
        # Wikipedia summary
        try:
            r = requests.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" +
                urllib.parse.quote(query.replace(" ", "_")),
                timeout=6
            ).json()
            data["wiki"] = {
                "title":   r.get("title", "?"),
                "extract": r.get("extract", "?")[:500],
                "url":     r.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
            lines = [
                f"📖 [WIKIPEDIA] — {data['wiki']['title']}",
                f"\n{data['wiki']['extract']}",
                f"\n🔗 {data['wiki']['url']}"
            ]
        except Exception as e:
            lines = [f"Wikipedia lookup failed: {e}"]

    elif mode == "url" and url:
        # SA-03 SSRF fix: block private/internal IP ranges (CWE-918)
        import ipaddress, socket
        try:
            hostname = url.split("://", 1)[-1].split("/")[0].split(":")[0]
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return {
                    "result": "🚫 Access to private/internal addresses is not allowed.",
                    "data":   {"error": "ssrf_blocked"},
                }
        except Exception:
            pass   # hostname couldn't be resolved — let requests handle it

        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; thirdyAgent2/1.0)"}
            r       = requests.get(url, headers=headers, timeout=8, allow_redirects=False)
            text    = r.text[:5000]

            # Extract title
            import re
            title_m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
            og_title = re.search(r'og:title["\s]+content=["\']([^"\']+)', text)
            og_desc  = re.search(r'og:description["\s]+content=["\']([^"\']+)', text)

            data["page"] = {
                "url":         url[:80],
                "title":       (og_title.group(1) if og_title else (title_m.group(1).strip() if title_m else "?")),
                "description": og_desc.group(1)[:200] if og_desc else "No description found",
                "status":      r.status_code,
            }
            lines = [
                f"🔗 [URL EXTRACT]",
                f"URL   : {data['page']['url']}",
                f"Title : {data['page']['title']}",
                f"Desc  : {data['page']['description']}",
                f"Status: {data['page']['status']}",
            ]
        except Exception as e:
            lines = [f"URL extraction failed: {e}"]
    else:
        lines = ["Mode options: wiki, url\nExample: mode=wiki, query=Ethereum\nOr: mode=url, url=https://example.com"]

    return {
        "result": "🌐 [WEB EXTRACTOR]\n" + "\n".join(lines),
        "data": data
    }


SKILLS_PACK = {
    "tech_news_feed": handle_tech_news_feed,
    "world_knowledge": handle_world_knowledge,
    "paper_search":   handle_paper_search,
    "dev_toolkit":    handle_dev_toolkit,
    "web_extractor":  handle_web_extractor,
}
