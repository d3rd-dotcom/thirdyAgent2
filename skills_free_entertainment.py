"""
skills_free_entertainment.py — Entertainment skill pack for thirdyAgent2
5 skills: anime_universe, fun_pack, gamer_hub, quotes_wisdom, daily_briefing
All free, zero API keys needed.
"""
import requests
import random
import datetime


def handle_anime_universe(params):
    """
    Anime data: top anime, random anime, search
    API: api.jikan.moe (no key, MyAnimeList data)
    """
    mode  = params.get("mode", "top")
    query = params.get("query", "")
    data  = {}

    if mode == "search" and query:
        try:
            r = requests.get(
                f"https://api.jikan.moe/v4/anime",
                params={"q": query, "limit": 5},
                timeout=8
            ).json()
            data["results"] = [
                {
                    "title":  a.get("title", "?"),
                    "score":  a.get("score", "?"),
                    "eps":    a.get("episodes", "?"),
                    "status": a.get("status", "?"),
                }
                for a in r.get("data", [])[:5]
            ]
            lines = [f"🔍 Anime Search: '{query}'"]
            for a in data["results"]:
                lines.append(f"• {a['title']} | Score: {a['score']} | {a['eps']} eps | {a['status']}")
        except Exception as e:
            lines = [f"Anime search failed: {e}"]

    elif mode == "random":
        try:
            r = requests.get("https://api.jikan.moe/v4/random/anime", timeout=8).json()
            a = r.get("data", {})
            data["anime"] = a
            lines = [
                f"🎲 [RANDOM ANIME]",
                f"Title   : {a.get('title','?')}",
                f"Score   : {a.get('score','?')} ⭐",
                f"Episodes: {a.get('episodes','?')}",
                f"Status  : {a.get('status','?')}",
                f"Genre   : {', '.join([g['name'] for g in a.get('genres',[])[:3]])}",
                f"Synopsis: {str(a.get('synopsis','?'))[:150]}...",
            ]
        except Exception as e:
            lines = [f"Random anime failed: {e}"]

    else:  # top
        try:
            r = requests.get(
                "https://api.jikan.moe/v4/top/anime",
                params={"limit": 5},
                timeout=8
            ).json()
            data["top"] = r.get("data", [])[:5]
            lines = ["🏆 [TOP ANIME RIGHT NOW]"]
            for i, a in enumerate(data["top"], 1):
                lines.append(f"{i}. {a.get('title','?')} | Score: {a.get('score','?')} | {a.get('episodes','?')} eps")
        except Exception as e:
            lines = [f"Top anime failed: {e}"]

    return {
        "result": "🌸 [ANIME UNIVERSE]\n" + "\n".join(lines),
        "data": data
    }


def handle_fun_pack(params):
    """
    Fun content bundle: jokes + dad jokes + dark jokes + trivia
    APIs: v2.jokeapi.dev (no key) + official-joke-api (no key) + opentdb (no key)
    """
    mode = params.get("mode", "mixed")
    data = {}

    # Programming/general joke
    try:
        r = requests.get(
            "https://v2.jokeapi.dev/joke/Programming,Misc",
            params={"blacklistFlags": "nsfw,racist,sexist,explicit", "format": "json"},
            timeout=5
        ).json()
        if r.get("type") == "single":
            data["joke"] = r.get("joke", "?")
        else:
            data["joke"] = f"{r.get('setup','?')} ... {r.get('delivery','?')}"
    except: pass

    # Dad joke
    try:
        r = requests.get(
            "https://official-joke-api.appspot.com/random_joke",
            timeout=5
        ).json()
        data["dad_joke"] = f"{r.get('setup','?')} — {r.get('punchline','?')}"
    except: pass

    # Trivia question
    try:
        r = requests.get(
            "https://opentdb.com/api.php?amount=1&type=multiple&difficulty=medium",
            timeout=5
        ).json()
        q = r.get("results", [{}])[0]
        data["trivia_q"] = q.get("question", "?").replace("&quot;",'"').replace("&#039;","'")
        data["trivia_a"] = q.get("correct_answer", "?").replace("&quot;",'"')
    except: pass

    lines = ["🎉 [FUN PACK]"]
    if data.get("joke"):
        lines.append(f"\n😂 Joke:\n{data['joke']}")
    if data.get("dad_joke"):
        lines.append(f"\n👨 Dad Joke:\n{data['dad_joke']}")
    if data.get("trivia_q"):
        lines.append(f"\n🧠 Trivia:\n{data['trivia_q']}\n(Answer: {data['trivia_a']})")

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_gamer_hub(params):
    """
    Gaming data: top games, game search, game details
    API: api.rawg.io (no key for basic, or free key with 100K/month)
    Fallback: freetogame.com (no key at all)
    """
    mode  = params.get("mode", "free")
    query = params.get("query", "")
    data  = {}

    if mode == "search" and query:
        # RAWG search (works without key for basic)
        try:
            r = requests.get(
                "https://api.rawg.io/api/games",
                params={"search": query, "page_size": 5},
                timeout=8
            ).json()
            games = r.get("results", [])[:5]
            data["games"] = games
            lines = [f"🔍 Game Search: '{query}'"]
            for g in games:
                rating = g.get("rating", "?")
                platforms = ", ".join([p["platform"]["name"] for p in g.get("platforms", [])[:2]])
                lines.append(f"• {g.get('name','?')} | Rating: {rating}/5 | {platforms}")
        except Exception as e:
            lines = [f"Game search failed: {e}"]

    else:  # free games
        try:
            r = requests.get(
                "https://www.freetogame.com/api/games",
                params={"sort-by": "popularity"},
                timeout=8
            ).json()
            games = r[:6] if isinstance(r, list) else []
            data["free_games"] = games
            lines = ["🆓 [TOP FREE-TO-PLAY GAMES]"]
            for g in games:
                lines.append(
                    f"• {g.get('title','?')} | {g.get('genre','?')} | "
                    f"{g.get('platform','?')} | {g.get('developer','?')}"
                )
        except Exception as e:
            lines = [f"Free games failed: {e}"]

    return {
        "result": "🎮 [GAMER HUB]\n" + "\n".join(lines),
        "data": data
    }


def handle_quotes_wisdom(params):
    """
    Quotes and wisdom from multiple sources
    APIs: api.quotable.io (no key) + zenquotes.io (no key) + adviceslip (no key)
    """
    author  = params.get("author", "")
    topic   = params.get("topic", "")
    data    = {}

    # Quotable — author or random
    try:
        params_q = {"limit": 3}
        if author:
            params_q["author"] = author.lower().replace(" ", "-")
        if topic:
            params_q["tags"] = topic
        r = requests.get("https://api.quotable.io/quotes/random", params=params_q, timeout=6).json()
        if isinstance(r, list):
            data["quotes"] = [{"text": q.get("content","?"), "author": q.get("author","?")} for q in r[:3]]
        elif isinstance(r, dict):
            data["quotes"] = [{"text": r.get("content","?"), "author": r.get("author","?")}]
    except: pass

    # Zen quotes — always uplifting
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=5).json()
        if r:
            data["zen"] = {"text": r[0].get("q","?"), "author": r[0].get("a","?")}
    except: pass

    # Advice slip
    try:
        r = requests.get("https://api.adviceslip.com/advice", timeout=5).json()
        data["advice"] = r.get("slip", {}).get("advice", "?")
    except: pass

    lines = [f"📜 [QUOTES & WISDOM]"]
    if author:
        lines.append(f"— Quotes by {author} —")
    elif topic:
        lines.append(f"— Topic: {topic} —")

    for q in data.get("quotes", []):
        lines.append(f'\n"{q["text"]}"\n  — {q["author"]}')

    if data.get("zen"):
        lines.append(f'\n✨ Zen: "{data["zen"]["text"]}"\n  — {data["zen"]["author"]}')

    if data.get("advice"):
        lines.append(f'\n💡 Advice: {data["advice"]}')

    return {
        "result": "\n".join(lines),
        "data": data
    }


def handle_daily_briefing(params):
    """
    Daily briefing bundle: date info + fun fact + quote + random activity
    All no-key APIs combined into one morning briefing
    """
    data = {}
    now  = datetime.datetime.now(datetime.timezone.utc)

    data["date"]    = now.strftime("%A, %B %d, %Y")
    data["time"]    = now.strftime("%H:%M UTC")
    data["day_num"] = now.timetuple().tm_yday
    data["week"]    = now.isocalendar()[1]

    # Fun fact
    try:
        r = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=5).json()
        data["fact"] = r.get("text", "?")
    except: pass

    # Quote
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=5).json()
        if r:
            data["quote"]        = r[0].get("q","?")
            data["quote_author"] = r[0].get("a","?")
    except: pass

    # Bored? Activity suggestion
    try:
        r = requests.get("https://bored-api.appbrewery.com/random", timeout=5).json()
        data["activity"]       = r.get("activity", "?")
        data["activity_type"]  = r.get("type", "?")
        data["participants"]   = r.get("participants", "?")
    except: pass

    # Number fact for day of year
    try:
        day_num = data["day_num"]
        fact = requests.get(f"http://numbersapi.com/{day_num}/date", timeout=5).text
        data["day_fact"] = fact
    except: pass

    lines = [
        f"☀️ [DAILY BRIEFING]",
        f"📅 {data['date']} — Week {data['week']}, Day {data['day_num']} of the year",
        f"🕐 {data['time']}",
    ]
    if data.get("day_fact"):
        lines.append(f"\n🗓️  On This Day: {data['day_fact']}")
    if data.get("fact"):
        lines.append(f"\n💡 Today's Fact:\n{data['fact']}")
    if data.get("quote"):
        lines.append(f"\n📜 Quote:\n\"{data['quote']}\"\n  — {data.get('quote_author','?')}")
    if data.get("activity"):
        lines.append(
            f"\n🎯 Activity Idea: {data['activity']}\n"
            f"   Type: {data['activity_type']} | Participants: {data['participants']}"
        )

    return {
        "result": "\n".join(lines),
        "data": data
    }


SKILLS_PACK = {
    "anime_universe":  handle_anime_universe,
    "fun_pack":        handle_fun_pack,
    "gamer_hub":       handle_gamer_hub,
    "quotes_wisdom":   handle_quotes_wisdom,
    "daily_briefing":  handle_daily_briefing,
}
