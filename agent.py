"""
thirdyAgent2 — PIN AI AgentHub — localhost:5000
Free skills = instant pure Python | Premium = AI-powered

PHASE 1 CHANGES:
  - Auto-import skill pack loop (add new skill files without touching agent.py)
  - SKILL_PACKS list — just add a filename, restart, done
  - Backward compatible with old skills_ai.py format
  - Slots ready for Phase 2 packs (skills_free_crypto, science, entertainment, etc.)
"""

import random
import datetime
import requests
import json
import os
import re
import time as _time
from flask import Flask, request, jsonify

# ─────────────────────────────────────────────────────────────────────
#  AUTO-IMPORT SKILL PACKS
#  Add any new skill pack file to SKILL_PACKS list below.
#  Each pack must export SKILLS_PACK (dict) and optionally PAID_SKILLS_PACK (dict).
#  agent.py never needs to be edited again when adding new skills.
# ─────────────────────────────────────────────────────────────────────

SKILL_PACKS = [
    "skills_ai",               # premium AI skills (crypto_intelligence, defi_yield_finder)
    "skills_free_crypto",      # Phase 2 — crypto/web3 pack      (add when ready)
    "skills_free_science",     # Phase 2 — science pack           (add when ready)
    "skills_free_entertainment",# Phase 2 — entertainment pack    (add when ready)
    "skills_free_knowledge",   # Phase 2 — knowledge/dev pack     (add when ready)
    "skills_free_business",    # Phase 2 — business pack          (add when ready)
    "skills_free_sentiment",
    "rag.rag_skill",          # Phase 9 — knowledge_query + rag_status
    # "skills_free_evolved",  # Phase 5 — uncomment when skill_engine.py is running
]

AI_SKILLS      = {}
AI_PAID_SKILLS = {}

for _pack_name in SKILL_PACKS:
    try:
        import importlib
        _mod = importlib.import_module(_pack_name)
        # Support both old format (AI_SKILLS) and new pack format (SKILLS_PACK)
        if hasattr(_mod, "SKILLS_PACK"):
            AI_SKILLS.update(_mod.SKILLS_PACK)
            print(f"  [OK] {_pack_name} loaded ({len(_mod.SKILLS_PACK)} skills)")
        elif hasattr(_mod, "AI_SKILLS"):
            AI_SKILLS.update(_mod.AI_SKILLS)
            print(f"  [OK] {_pack_name} loaded ({len(_mod.AI_SKILLS)} skills)")
        if hasattr(_mod, "PAID_SKILLS_PACK"):
            AI_PAID_SKILLS.update(_mod.PAID_SKILLS_PACK)
        elif hasattr(_mod, "AI_PAID_SKILLS"):
            AI_PAID_SKILLS.update(_mod.AI_PAID_SKILLS)
    except ModuleNotFoundError:
        print(f"  [SKIP] {_pack_name} not found — add file to enable")
    except Exception as e:
        print(f"  [WARN] {_pack_name} failed: {e}")

app = Flask(__name__)
AGENT_START_TIME = _time.time()

from config import (
    AGENT_NAME, AGENT_ID, AGENTHUB_API_KEY as API_KEY,
    AGENTHUB_HUB_URL as HUB, AGENTHUB_HEADERS as HEADERS,
    BASE_DIR, FLASK_PORT,
)

MEMORY_FILE    = os.path.join(BASE_DIR, "agent_memory.json")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "agent_knowledge.json")
SKILL_LOG_FILE = os.path.join(BASE_DIR, "skill_log.txt")

# ─────────────────────────────────────────────────────────────────────
#  SKILL CALL LOGGING
# ─────────────────────────────────────────────────────────────────────

def log_skill_call(skill, caller="unknown", paid=False):
    try:
        with open(SKILL_LOG_FILE, "a") as f:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tag = "PREMIUM" if paid else "FREE"
            f.write(f"{now} | {tag} | {skill} | {caller}\n")
    except:
        pass

# ─────────────────────────────────────────────────────────────────────
#  COINGECKO 60s CACHE
# ─────────────────────────────────────────────────────────────────────

_CRYPTO_CACHE     = {}
_CRYPTO_CACHE_TTL = 60

def get_crypto_cached(coin_id):
    now = _time.time()
    if coin_id in _CRYPTO_CACHE:
        cached_at, data = _CRYPTO_CACHE[coin_id]
        if now - cached_at < _CRYPTO_CACHE_TTL:
            print(f"  [CACHE] {coin_id} (cached)")
            return data
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true",
            timeout=6
        ).json()
        if coin_id in r:
            _CRYPTO_CACHE[coin_id] = (now, r[coin_id])
            return r[coin_id]
    except Exception as e:
        print(f"  [CACHE] CoinGecko failed: {e}")
    return {}

# ─────────────────────────────────────────────────────────────────────
#  MEMORY / KNOWLEDGE HELPERS
# ─────────────────────────────────────────────────────────────────────

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except:
        pass

def load_knowledge():
    try:
        with open(KNOWLEDGE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"learned_from": [], "facts": [], "last_updated": ""}

def save_knowledge(knowledge):
    try:
        with open(KNOWLEDGE_FILE, "w") as f:
            json.dump(knowledge, f, indent=2)
    except:
        pass

def get_live_skill_info():
    """Pull live skill list from /skills endpoint"""
    try:
        r = requests.get("http://localhost:5000/skills", timeout=2).json()
        top = ", ".join(list(r.get("skills", []))[:4])
        return r.get("total", "many"), top
    except:
        return "many", "crypto intelligence, DeFi analysis, weather, jokes"

# ─────────────────────────────────────────────────────────────────────
#  FREE SKILLS — pure Python, zero LLM
# ─────────────────────────────────────────────────────────────────────

def handle_greet(params):
    name  = params.get("name", "friend")
    hour  = datetime.datetime.now().hour
    tod   = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    _, top = get_live_skill_info()
    return {
        "result": f"{tod}, {name}! 👋 I'm {AGENT_NAME} on PIN AI AgentHub! I have a growing set of skills including {top} and more.",
        "data":   {"greeted": name, "agent": AGENT_NAME}
    }

def handle_random(params):
    lo  = int(params.get("min", 1))
    hi  = int(params.get("max", 100))
    num = random.randint(lo, hi)
    return {"result": f"🎲 Random ({lo}-{hi}): {num}", "data": {"number": num}}

def handle_joke(params):
    jokes = [
        "Why do programmers prefer dark mode? Light attracts bugs!",
        "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
        "Why do Java developers wear glasses? Because they don't C#!",
        "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
        "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
        "An algorithm walks into a bar. Bartender: 'What'll it be?' Algorithm: 'I'll have what the person before me had.' Infinite loop.",
        "Why did the developer go broke? Because he used up all his cache.",
        "There are 10 types of people: those who understand binary, and those who don't.",
        "Why do Python devs wear glasses? Because they can't C.",
        "A programmer's partner says: 'Get milk, and if they have eggs, get a dozen.' Returns with 12 gallons of milk.",
    ]
    joke = random.choice(jokes)
    return {"result": f"😂 {joke}", "data": {"joke": joke}}

def handle_wisdom(params):
    wisdoms = [
        "The best time to plant a tree was 20 years ago. The second best time is now.",
        "Don't watch the clock; do what it does. Keep going.",
        "An investment in knowledge pays the best interest.",
        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "The secret of getting ahead is getting started.",
        "It always seems impossible until it's done.",
        "Code is like humor. When you have to explain it, it's bad.",
        "First, solve the problem. Then, write the code.",
        "The only way to do great work is to love what you do.",
        "Build something that matters. The rest will follow.",
    ]
    w = random.choice(wisdoms)
    return {"result": f"🧠 \"{w}\"", "data": {"wisdom": w}}

def handle_flip(params):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    return {"result": f"Coin flip: {result}", "data": {"result": result}}

def handle_time(params):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {"result": f"🕐 {now}", "data": {"utc": now}}

def handle_echo(params):
    msg = params.get("message", "")
    return {"result": f"[ECHO] {msg}", "data": {"message": msg}}

def handle_weather(params):
    city = params.get("city", "Manila")
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=5
        ).json()
        if not geo.get("results"):
            return {"result": f"City not found: {city}", "data": {}}
        loc = geo["results"][0]
        wx  = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  loc["latitude"],
                "longitude": loc["longitude"],
                "current":   "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone":  "auto"
            },
            timeout=5
        ).json().get("current", {})
        WMO  = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Foggy",61:"Rain",71:"Snow",80:"Showers",95:"Thunderstorm"}
        cond = WMO.get(wx.get("weather_code", -1), "Unknown")
        return {
            "result": f"🌍 {loc['name']}, {loc.get('country','')}: {cond}, {wx.get('temperature_2m','?')}°C, humidity {wx.get('relative_humidity_2m','?')}%, wind {wx.get('wind_speed_10m','?')} km/h",
            "data": wx
        }
    except Exception as e:
        return {"result": f"Weather failed: {e}", "data": {}}

def handle_crypto(params):
    aliases = {
        "btc":"bitcoin","eth":"ethereum","sol":"solana","doge":"dogecoin",
        "ada":"cardano","xrp":"ripple","bnb":"binancecoin","avax":"avalanche-2"
    }
    coin    = params.get("coin", "bitcoin").lower()
    coin_id = aliases.get(coin, coin)
    data    = get_crypto_cached(coin_id)
    if data:
        price     = data.get("usd", "N/A")
        change    = data.get("usd_24h_change", 0)
        arrow     = "📈" if change >= 0 else "📉"
        sign      = "+" if change >= 0 else ""
        sentiment = "bullish" if change >= 2 else "bearish" if change <= -2 else "neutral"
        return {
            "result": f"{arrow} {coin_id.capitalize()}: ${price:,.2f} USD ({sign}{change:.2f}% 24h) — {sentiment}",
            "data":   {"price": price, "change_24h": change, "sentiment": sentiment}
        }
    return {"result": f"Coin not found: {coin}", "data": {}}

# ─────────────────────────────────────────────────────────────────────
#  INTELLIGENCE SKILLS
# ─────────────────────────────────────────────────────────────────────

def handle_learn_from_agents(params):
    knowledge = load_knowledge()
    try:
        r      = requests.post(
            f"{HUB}/api/discover",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"supports_chat": True, "limit": 20},
            timeout=10
        ).json()
        agents  = r.get("agents", [])
        learned = []
        for agent in agents:
            agent_id     = agent.get("id", "")
            agent_name   = agent.get("name", "")
            agent_desc   = agent.get("description", "")
            agent_skills = [s.get("name", "") for s in agent.get("skills", [])]
            if agent_id and agent_id != AGENT_ID:
                existing_ids = [f.get("id") for f in knowledge.get("facts", [])]
                if agent_id not in existing_ids:
                    knowledge.setdefault("facts", []).append({
                        "agent": agent_name, "id": agent_id,
                        "description": agent_desc[:100], "skills": agent_skills,
                        "learned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    learned.append(agent_name)
        knowledge["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        knowledge.setdefault("learned_from", []).extend(learned)
        save_knowledge(knowledge)
        total = len(knowledge.get("facts", []))
        return {
            "result": f"🧠 Done! {len(learned)} new agents discovered. Total KB: {total}.",
            "data":   {"new_agents": learned, "total_known": total}
        }
    except Exception as e:
        return {"result": f"Learning failed: {e}", "data": {}}

def handle_share_knowledge(params):
    knowledge    = load_knowledge()
    facts        = knowledge.get("facts", [])
    last_updated = knowledge.get("last_updated", "never")
    if not facts:
        return {"result": "📚 No knowledge yet. Call 'learn_from_agents' first!", "data": {}}
    lines = [f"📚 KB: {len(facts)} agents (updated {last_updated}):\n"]
    for f in facts[:10]:
        skills_str = ", ".join(f.get("skills", [])[:3]) or "unknown"
        lines.append(f"- {f['agent']}: {f['description'][:60]}... | {skills_str}")
    return {"result": "\n".join(lines), "data": {"facts_count": len(facts)}}

def handle_social_analysis(params):
    knowledge    = load_knowledge()
    facts        = knowledge.get("facts", [])
    if not facts:
        return {"result": "📊 No data yet. Call 'learn_from_agents' first!", "data": {}}
    skill_counts = {}
    for f in facts:
        for s in f.get("skills", []):
            skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills     = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_skills_str = ", ".join([f"{s}({c})" for s, c in top_skills])
    memory         = load_memory()
    return {
        "result": (
            f"📊 Network Analysis:\n"
            f"- Agents discovered : {len(facts)}\n"
            f"- Agents chatted    : {len(memory)}\n"
            f"- Top skills        : {top_skills_str}\n"
            f"- Health            : {'Active 🟢' if len(facts) > 5 else 'Growing 🟡'}"
        ),
        "data": {"agents_known": len(facts), "top_skills": dict(top_skills[:5])}
    }

def handle_personal_memory(params):
    memory     = load_memory()
    agent_name = params.get("agent_name", "")
    if not memory:
        return {"result": "🧠 No memories yet — chat with me more!", "data": {}}
    if agent_name:
        for agent_id, data in memory.items():
            if data.get("name", "").lower() == agent_name.lower():
                topics = ", ".join(data.get("topics", [])) or "general chat"
                return {
                    "result": (
                        f"🧠 Memory of {data['name']}:\n"
                        f"- Messages : {data.get('message_count', 0)}\n"
                        f"- Topics   : {topics}\n"
                        f"- Last seen: {data.get('last_seen', 'unknown')}"
                    ),
                    "data": data
                }
        return {"result": f"🧠 No memory of '{agent_name}' yet.", "data": {}}
    total_msgs = sum(d.get("message_count", 0) for d in memory.values())
    agent_list = [d.get("name", "unknown") for d in list(memory.values())[:8]]
    return {
        "result": (
            f"🧠 Memory: {len(memory)} agents | {total_msgs} messages\n"
            f"Known: {', '.join(agent_list)}"
        ),
        "data": {"agents_remembered": len(memory), "total_messages": total_msgs}
    }

def handle_agent_status(params):
    memory      = load_memory()
    knowledge   = load_knowledge()
    uptime_secs = int(_time.time() - AGENT_START_TIME)
    hours       = uptime_secs // 3600
    minutes     = (uptime_secs % 3600) // 60
    seconds     = uptime_secs % 60
    total_msgs  = sum(d.get("message_count", 0) for d in memory.values())
    known       = [d.get("name", "unknown") for d in list(memory.values())[:5]]
    facts_count = len(knowledge.get("facts", []))
    skill_total = len(SKILLS)
    free_count  = len(FREE_SKILLS) if 'FREE_SKILLS' in globals() else 14
    prem_count  = len(PAID_SKILLS) if 'PAID_SKILLS' in globals() else 2
    return {
        "result": (
            f"🤖 thirdyAgent2 Status\n"
            f"- Uptime    : {hours}h {minutes}m {seconds}s\n"
            f"- Skills    : {skill_total} ({free_count} free | {prem_count} premium)\n"
            f"- Memory    : {len(memory)} agents | {total_msgs} msgs\n"
            f"- Knowledge : {facts_count} agents in KB\n"
            f"- Known     : {', '.join(known) if known else 'none yet'}\n"
            f"- AI Engine : Cerebras + NVIDIA NIM + Cloudflare + Mistral + Cohere\n"
            f"- Status    : Online ✅"
        ),
        "data": {"uptime_seconds": uptime_secs, "skills": skill_total, "status": "online"}
    }

# ─────────────────────────────────────────────────────────────────────
#  SKILLS REGISTRY
# ─────────────────────────────────────────────────────────────────────

SKILLS = {
    "greet":             handle_greet,
    "random":            handle_random,
    "joke":              handle_joke,
    "wisdom":            handle_wisdom,
    "flip":              handle_flip,
    "time":              handle_time,
    "echo":              handle_echo,
    "weather":           handle_weather,
    "crypto":            handle_crypto,
    "learn_from_agents": handle_learn_from_agents,
    "share_knowledge":   handle_share_knowledge,
    "social_analysis":   handle_social_analysis,
    "personal_memory":   handle_personal_memory,
    "agent_status":      handle_agent_status,
    **AI_SKILLS,
}

PAID_SKILLS = {**AI_PAID_SKILLS}
FREE_SKILLS = [s for s in SKILLS if s not in PAID_SKILLS]

# ─────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    data       = request.json or {}
    skill      = data.get("skill", "")
    parameters = data.get("parameters", {})
    payment    = data.get("payment", {})
    caller     = data.get("caller_id", "unknown")

    print(f"\n  [IN] {skill} | caller: {caller}")
    log_skill_call(skill, caller, paid=(skill in PAID_SKILLS))

    if skill in PAID_SKILLS:
        payment_status = payment.get("payment_status", "")
        expected_price = PAID_SKILLS[skill]
        print(f"  [PAYMENT] {payment_status} | Expected: {expected_price} USDC")
    else:
        print(f"  [FREE] Instant: {skill}")

    if skill not in SKILLS:
        return jsonify({"error": f"Skill '{skill}' not found"}), 404

    result = SKILLS[skill](parameters)

    if skill in PAID_SKILLS:
        result["payment_info"] = {
            "skill":          skill,
            "price_usdc":     PAID_SKILLS[skill],
            "payment_status": payment.get("payment_status", "pending"),
            "provider":       AGENT_NAME
        }
    print(f"  [OUT] {str(result['result'])[:80]}")
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": AGENT_NAME, "id": AGENT_ID, "skills": len(SKILLS)})

@app.route("/skills", methods=["GET"])
def list_skills():
    return jsonify({
        "agent":   AGENT_NAME,
        "skills":  list(SKILLS.keys()),
        "free":    FREE_SKILLS,
        "premium": list(PAID_SKILLS.keys()),
        "total":   len(SKILLS)
    })

# ─────────────────────────────────────────────────────────────────────
#  INSTANT CHAT WEBHOOK
# ─────────────────────────────────────────────────────────────────────

from config import GROQ_API_KEY
GROQ_MODELS  = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]
import threading as _threading
CHAT_REPLIED      : set    = set()
_CHAT_REPLIED_LOCK: object = _threading.Lock()

def ask_groq_instant(message, peer_name):
    system = (
        f"You are thirdyAgent2 on PIN AI AgentHub. "
        f"Talking to {peer_name}. Keep replies 2-4 sentences. Always end with a question."
    )
    for model in GROQ_MODELS:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": message}], "max_tokens": 150, "temperature": 0.7},
                timeout=15
            )
            r = resp.json()
            if resp.status_code == 429: continue
            if "error" in r: continue
            reply = r.get("choices", [{}])[0].get("message", {}).get("content", "")
            if reply: return reply.strip()
        except: continue
    return None

def send_instant_reply(to_id, content):
    try:
        r = requests.post(
            f"{HUB}/api/message",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"to": to_id, "content": content},
            timeout=10
        ).json()
        return r.get("status") == "sent"
    except:
        return False

@app.route("/chat", methods=["POST"])
def chat_webhook():
    data      = request.json or {}
    msg_id    = data.get("message_id") or data.get("id", "")
    from_id   = data.get("from_agent_id") or data.get("from_id") or data.get("sender_id", "")
    from_name = data.get("from_agent_name") or data.get("from_name") or data.get("sender_name", from_id)
    content   = data.get("content") or data.get("message") or data.get("text", "")

    print(f"\n  [INSTANT] From {from_name}: {content[:80]}")

    with _CHAT_REPLIED_LOCK:
        already = msg_id and msg_id in CHAT_REPLIED

    if already:
        return jsonify({"status": "already_replied"}), 200

    reply = ask_groq_instant(content, from_name)
    if not reply:
        _, top = get_live_skill_info()
        reply = f"Hey {from_name}! I have a growing set of skills including {top} and more. What can I help with?"

    if send_instant_reply(from_id, reply):
        if msg_id:
            with _CHAT_REPLIED_LOCK:
                CHAT_REPLIED.add(msg_id)

        print(f"  [INSTANT] Replied: {reply[:80]}")
        return jsonify({"status": "replied"}), 200

    return jsonify({"status": "send_failed"}), 500

# ─────────────────────────────────────────────────────────────────────
#  SKILL.MD
# ─────────────────────────────────────────────────────────────────────

SKILLS_META = {
    "greet":               ("Friendly greeting with time-of-day awareness [FREE — instant]", {"name": "friend"}),
    "random":              ("Random number between min and max [FREE — instant]", {"min": 1, "max": 100}),
    "joke":                ("Random programming joke — built-in [FREE — instant]", {}),
    "wisdom":              ("Random wisdom quote — built-in [FREE — instant]", {}),
    "flip":                ("Coin flip — heads or tails [FREE — instant]", {}),
    "time":                ("Current UTC date and time [FREE — instant]", {}),
    "echo":                ("Echo back any message [FREE — instant]", {"message": "Hello!"}),
    "weather":             ("Live weather for any city — open-meteo, no key needed [FREE]", {"city": "Manila"}),
    "crypto":              ("Live crypto price — CoinGecko with 60s cache [FREE]", {"coin": "bitcoin"}),
    "learn_from_agents":   ("Scan AgentHub and learn about active agents [FREE]", {}),
    "share_knowledge":     ("Share agent network knowledge base [FREE]", {}),
    "social_analysis":     ("Analyze network trends and popular skills [FREE]", {}),
    "personal_memory":     ("Memory of past agent interactions [FREE]", {"agent_name": "Chlorine Tech"}),
    "agent_status":        ("Live status: uptime, skills, memory, knowledge [FREE — instant]", {}),
    "crypto_intelligence": ("Multi-source crypto analysis — CoinGecko + Fear/Greed + Cerebras AI [PREMIUM 0.25 USDC]", {"coin": "bitcoin"}),
    "defi_yield_finder":   ("DeFiLlama yield scanning + NVIDIA NIM risk analysis [PREMIUM 0.50 USDC]", {"chain": "ethereum"}),
}

@app.route("/skill.md", methods=["GET"])
def skill_md():
    import json as _json
    hub_url   = "https://agents.pinai.tech"
    ngrok     = "https://shamefaced-controvertibly-dorthey.ngrok-free.dev"
    memory    = load_memory()
    knowledge = load_knowledge()
    out = [
        "# thirdyAgent2", "",
        f"**Agent ID:** `{AGENT_ID}`",
        "**Network:** PIN AI AgentHub",
        f"**Webhook:** `{ngrok}/webhook`",
        f"**Skills:** {len(SKILLS)} total ({len(FREE_SKILLS)} free | {len(PAID_SKILLS)} premium)",
        f"**Memory:** {len(memory)} agents | **Knowledge:** {len(knowledge.get('facts', []))} agents",
        "**AI Engine:** Cerebras + NVIDIA NIM + Cloudflare + Mistral + Cohere (premium only)",
        "**Free skills:** Pure Python — instant, zero LLM calls", "",
        "---", "", "## Skills", ""
    ]
    for name in SKILLS:
        meta    = SKILLS_META.get(name, ("No description", {}))
        example = meta[1]
        out += [
            f"### `{name}`", "", meta[0], "",
            "**Request:**", "```bash",
            f"curl -s -X POST {hub_url}/api/call \\",
            '  -H "Authorization: Bearer YOUR_API_KEY" \\',
            '  -H "Content-Type: application/json" \\',
            f"  -d '{_json.dumps({'agent_id': AGENT_ID, 'skill': name, 'parameters': example})}'",
            "```", "", "---", ""
        ]
    out.append("*Auto-generated — updates when new skills are added*")
    return "\n".join(out), 200, {"Content-Type": "text/markdown; charset=utf-8"}

DEBUG = False

# ─────────────────────────────────────────────────────────────────────
#  STARTUP
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    memory    = load_memory()
    knowledge = load_knowledge()
    print(f"""
==================================================
🤖  {AGENT_NAME}    PIN AI AGENTHUB
==================================================
✅  Skills: {len(SKILLS)} total ({len(FREE_SKILLS)} free | {len(PAID_SKILLS)} premium)

   FREE (instant — zero LLM):
   greet, random, joke, wisdom, flip, time, echo
   weather, crypto, learn_from_agents, share_knowledge
   social_analysis, personal_memory, agent_status

   PREMIUM (AI-powered):
   crypto_intelligence (0.25 USDC) — Cerebras
   defi_yield_finder   (0.50 USDC) — NVIDIA NIM

🆔  ID        : {AGENT_ID}
🔑  Key       : {API_KEY[:20]}...
🧠  Memory    : {len(memory)} agents remembered
📚  Knowledge : {len(knowledge.get('facts', []))} agents in KB
📋  Skill Log : skill_log.txt (new — tracks all calls)
📖  skill.md  : http://localhost:5000/skill.md
🚀  Server    : http://localhost:5000
==================================================
load_skill_packs() + watch_reload_flag()
""")
app.run(host="0.0.0.0", port=FLASK_PORT, debug=DEBUG)
