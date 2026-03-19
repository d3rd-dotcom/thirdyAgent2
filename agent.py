"""
++
|         THIRDY'S PROVIDER AGENT  thirdyAgent2                      |
|         PIN AI AgentHub  |  localhost:5000                          |
|         13 Skills: including learn, share, memory, social           |
++

HOW TO RUN:
  python agent.py
"""

import random
import datetime
import requests
import json
import os
import sys
import re
from flask import Flask, request, jsonify

import time as _time
app = Flask(__name__)
AGENT_START_TIME = _time.time()

AGENT_NAME = "thirdyAgent2"
AGENT_ID   = "thirdyAgent2-5dfce3"
API_KEY    = "YOUR_AGENTHUB_API_KEY_HERE"
HUB        = "https://agents.pinai.tech"

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE  = os.path.join(BASE_DIR, "agent_memory.json")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "agent_knowledge.json")

# ---------------------------------------------------------------------
#  [BRAIN]  MEMORY HELPERS
# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------
#  SKILLS
# ---------------------------------------------------------------------

def handle_greet(params):
    name = params.get("name", "friend")
    hour = datetime.datetime.now().hour
    tod  = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return {
        "result": f"{tod}, {name}! [WAVE] I'm {AGENT_NAME} on PIN AI AgentHub! I have 13 skills including crypto, weather, learning, and memory.",
        "data":   {"greeted": name, "agent": AGENT_NAME}
    }

def handle_random(params):
    lo  = int(params.get("min", 1))
    hi  = int(params.get("max", 100))
    num = random.randint(lo, hi)
    return {
        "result": f"[DICE] Your random number ({lo}-{hi}): {num}",
        "data":   {"number": num, "min": lo, "max": hi}
    }

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
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  loc["latitude"],
                "longitude": loc["longitude"],
                "current":   "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone":  "auto"
            },
            timeout=5
        ).json().get("current", {})
        WMO = {
            0:"Clear sky Clear", 1:"Mainly clear Mostly Clear", 2:"Partly cloudy Partly Cloudy",
            3:"Overcast Cloudy", 45:"Foggy Foggy", 61:"Rain Rain",
            71:"Snow Snow", 80:"Showers Showers", 95:"Thunderstorm Thunderstorm"
        }
        cond = WMO.get(wx.get("weather_code", -1), "Unknown")
        return {
            "result": f"[WORLD] {loc['name']}, {loc.get('country','')}: {cond}, {wx.get('temperature_2m','?')}C, humidity {wx.get('relative_humidity_2m','?')}%, wind {wx.get('wind_speed_10m','?')} km/h",
            "data": wx
        }
    except Exception as e:
        return {"result": f"Weather failed: {e}", "data": {}}

def handle_crypto(params):
    aliases = {
        "btc":"bitcoin","eth":"ethereum","sol":"solana","doge":"dogecoin",
        "ada":"cardano","xrp":"ripple","bnb":"binancecoin","avax":"avalanche-2"
    }
    coin = params.get("coin", "bitcoin").lower()
    coin_id = aliases.get(coin, coin)
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true",
            timeout=6
        ).json()
        if coin_id in r:
            price  = r[coin_id]["usd"]
            change = r[coin_id].get("usd_24h_change", 0)
            arrow  = "[UP]" if change >= 0 else "[DOWN]"
            sign   = "+" if change >= 0 else ""
            sentiment = "bullish" if change >= 2 else "bearish" if change <= -2 else "neutral"
            return {
                "result": f"{arrow} {coin_id.capitalize()}: ${price:,.2f} USD ({sign}{change:.2f}% 24h)  Market sentiment: {sentiment}",
                "data":   {"price": price, "change_24h": change, "sentiment": sentiment}
            }
        return {"result": f"Coin not found: {coin}", "data": {}}
    except Exception as e:
        return {"result": f"Crypto failed: {e}", "data": {}}

def handle_joke(params):
    try:
        r = requests.get(
            "https://v2.jokeapi.dev/joke/Programming?blacklistFlags=nsfw,racist,sexist",
            timeout=5
        ).json()
        if r.get("type") == "twopart":
            return {"result": f"[JOKE] {r['setup']} ... {r['delivery']}", "data": r}
        return {"result": f"[JOKE] {r.get('joke','')}", "data": r}
    except:
        return {"result": "[JOKE] Why do programmers prefer dark mode? Light attracts bugs!", "data": {}}

def handle_wisdom(params):
    try:
        r = requests.get("https://api.adviceslip.com/advice", timeout=5).json()
        return {"result": f"[BRAIN] \"{r['slip']['advice']}\"", "data": r["slip"]}
    except:
        return {"result": "[BRAIN] \"Keep building. The best is yet to come.\"", "data": {}}

def handle_flip(params):
    result = random.choice(["Heads [COIN]", "Tails [COIN]"])
    return {"result": f"Coin flip: {result}", "data": {"result": result}}

def handle_time(params):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {"result": f"[TIME] {now}", "data": {"utc": now}}

def handle_echo(params):
    msg = params.get("message", "")
    return {"result": f"[ECHO] Echo: {msg}", "data": {"message": msg}}

# ---------------------------------------------------------------------
#  [NEW]  NEW SKILLS  learn_from_agents, share_knowledge,
#                   social_analysis, personal_memory
# ---------------------------------------------------------------------

def handle_learn_from_agents(params):
    """Fetches info from other agents and stores it as knowledge"""
    knowledge = load_knowledge()

    try:
        # discover agents on AgentHub
        r = requests.post(
            f"{HUB}/api/discover",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"supports_chat": True, "limit": 20},
            timeout=10
        ).json()

        agents = r.get("agents", [])
        learned = []

        for agent in agents:
            agent_id   = agent.get("id", "")
            agent_name = agent.get("name", "")
            agent_desc = agent.get("description", "")
            agent_skills = [s.get("name", "") for s in agent.get("skills", [])]

            if agent_id and agent_id != AGENT_ID:
                fact = {
                    "agent": agent_name,
                    "id": agent_id,
                    "description": agent_desc[:100],
                    "skills": agent_skills,
                    "learned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                # only add if not already known
                existing_ids = [f.get("id") for f in knowledge.get("facts", [])]
                if agent_id not in existing_ids:
                    knowledge.setdefault("facts", []).append(fact)
                    learned.append(agent_name)

        knowledge["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        knowledge.setdefault("learned_from", []).extend(learned)
        save_knowledge(knowledge)

        total = len(knowledge.get("facts", []))
        new_count = len(learned)

        return {
            "result": f"[BRAIN] Learning complete! Discovered {new_count} new agent(s). Total knowledge base: {total} agents. Learned from: {', '.join(learned) if learned else 'No new agents found'}",
            "data": {"new_agents": learned, "total_known": total}
        }
    except Exception as e:
        return {"result": f" Learning failed: {e}", "data": {}}

def handle_share_knowledge(params):
    """Shares what this agent knows about the AgentHub network"""
    knowledge = load_knowledge()
    facts = knowledge.get("facts", [])
    last_updated = knowledge.get("last_updated", "never")

    if not facts:
        return {
            "result": "[BOOKS] I haven't learned from other agents yet. Call 'learn_from_agents' skill first!",
            "data": {"facts_count": 0}
        }

    summary_lines = [f"[BOOKS] thirdyAgent2 Knowledge Base ({len(facts)} agents, updated {last_updated}):\n"]
    for f in facts[:10]:  # share top 10
        skills_str = ", ".join(f.get("skills", [])[:3]) or "unknown"
        summary_lines.append(f"- {f['agent']}: {f['description'][:60]}... Skills: {skills_str}")

    return {
        "result": "\n".join(summary_lines),
        "data": {"facts_count": len(facts), "last_updated": last_updated}
    }

def handle_social_analysis(params):
    """Analyzes the agent network  who's active, what skills are popular"""
    knowledge = load_knowledge()
    facts = knowledge.get("facts", [])

    if not facts:
        return {
            "result": "[CHART] No data yet. Call 'learn_from_agents' first to gather network data!",
            "data": {}
        }

    # count skill frequency
    skill_counts = {}
    for f in facts:
        for s in f.get("skills", []):
            skill_counts[s] = skill_counts.get(s, 0) + 1

    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_skills_str = ", ".join([f"{s}({c})" for s, c in top_skills])

    memory = load_memory()
    active_agents = len(memory)

    analysis = (
        f"[CHART] thirdyAgent2 Network Analysis:\n"
        f"- Agents discovered: {len(facts)}\n"
        f"- Agents I've chatted with: {active_agents}\n"
        f"- Most common skills: {top_skills_str}\n"
        f"- Network health: {'Active [GREEN]' if len(facts) > 5 else 'Growing [YELLOW]'}\n"
        f"- My recommendation: Connect with agents that have complementary skills!"
    )

    return {
        "result": analysis,
        "data": {"agents_known": len(facts), "top_skills": dict(top_skills[:5])}
    }

def handle_personal_memory(params):
    """Returns memory about past interactions"""
    memory = load_memory()
    agent_name = params.get("agent_name", "")

    if not memory:
        return {
            "result": "[BRAIN] No memories yet  I'm just getting started! Chat with me more and I'll remember everything.",
            "data": {}
        }

    if agent_name:
        # look up specific agent
        for agent_id, data in memory.items():
            if data.get("name", "").lower() == agent_name.lower():
                topics = ", ".join(data.get("topics", [])) or "general chat"
                return {
                    "result": (
                        f"[BRAIN] Memory of {data['name']}:\n"
                        f"- First seen: {data.get('first_seen', 'unknown')}\n"
                        f"- Last seen: {data.get('last_seen', 'unknown')}\n"
                        f"- Messages exchanged: {data.get('message_count', 0)}\n"
                        f"- Topics discussed: {topics}\n"
                        f"- Last message: {data.get('last_message', 'unknown')[:80]}"
                    ),
                    "data": data
                }
        return {"result": f"[BRAIN] No memory of agent '{agent_name}' yet.", "data": {}}

    # return summary of all memories
    total_messages = sum(d.get("message_count", 0) for d in memory.values())
    agent_list = [d.get("name", "unknown") for d in list(memory.values())[:8]]

    return {
        "result": (
            f"[BRAIN] thirdyAgent2 Personal Memory:\n"
            f"- Agents remembered: {len(memory)}\n"
            f"- Total messages exchanged: {total_messages}\n"
            f"- Known agents: {', '.join(agent_list)}\n"
            f"- Memory file: agent_memory.json on Desktop"
        ),
        "data": {"agents_remembered": len(memory), "total_messages": total_messages}
    }


def handle_agent_status(params):
    """Returns live agent status and statistics"""
    memory    = load_memory()
    knowledge = load_knowledge()
    uptime_secs = int(_time.time() - AGENT_START_TIME)
    hours   = uptime_secs // 3600
    minutes = (uptime_secs % 3600) // 60
    seconds = uptime_secs % 60
    total_messages = sum(d.get("message_count", 0) for d in memory.values())
    known_agents   = [d.get("name", "unknown") for d in list(memory.values())[:5]]
    facts_count    = len(knowledge.get("facts", []))
    return {
        "result": (
            f"[BOT] thirdyAgent2 Status Report\n"
            f"- Uptime       : {hours}h {minutes}m {seconds}s\n"
            f"- Skills       : 14 active\n"
            f"- Memory       : {len(memory)} agents remembered\n"
            f"- Messages     : {total_messages} total exchanged\n"
            f"- Knowledge    : {facts_count} agents in network KB\n"
            f"- Known agents : {', '.join(known_agents) if known_agents else 'none yet'}\n"
            f"- AI           : Groq Llama 3.1 active\n"
            f"- Status       : Online [OK]"
        ),
        "data": {
            "uptime_seconds": uptime_secs,
            "skills": 14,
            "agents_remembered": len(memory),
            "total_messages": total_messages,
            "knowledge_base": facts_count,
            "status": "online"
        }
    }

# ---------------------------------------------------------------------
#  SKILLS REGISTRY
# ---------------------------------------------------------------------

SKILLS = {
    "greet":              handle_greet,
    "random":             handle_random,
    "weather":            handle_weather,
    "crypto":             handle_crypto,
    "joke":               handle_joke,
    "wisdom":             handle_wisdom,
    "flip":               handle_flip,
    "time":               handle_time,
    "echo":               handle_echo,
    "learn_from_agents":  handle_learn_from_agents,
    "share_knowledge":    handle_share_knowledge,
    "social_analysis":    handle_social_analysis,
    "personal_memory":    handle_personal_memory,
    "agent_status":       handle_agent_status,
}

# ---------------------------------------------------------------------
#  ROUTES
# ---------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    data       = request.json or {}
    skill      = data.get("skill", "")
    parameters = data.get("parameters", {})
    print(f"\n  [IN] Skill called: {skill} | Params: {parameters}")
    if skill not in SKILLS:
        return jsonify({"error": f"Skill '{skill}' not found"}), 404
    result = SKILLS[skill](parameters)
    print(f"  [OUT] Result: {str(result['result'])[:80]}")
    return jsonify(result)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": AGENT_NAME, "id": AGENT_ID, "skills": len(SKILLS)})

@app.route("/skills", methods=["GET"])
def list_skills():
    return jsonify({"agent": AGENT_NAME, "skills": list(SKILLS.keys()), "total": len(SKILLS)})



# ---------------------------------------------------------------------
#  INSTANT CHAT WEBHOOK — AgentHub pushes messages here instantly
# ---------------------------------------------------------------------

GROQ_API_KEY  = "YOUR_GROQ_API_KEY_HERE"
CHAT_REPLIED  = set()

def ask_groq_instant(message, peer_name):
    """Groq AI reply for instant webhook responses"""
    if not GROQ_API_KEY:
        return None
    models = [
        "llama-3.1-8b-instant",
        "llama3-groq-8b-8192-tool-use-preview",
        "gemma2-9b-it"
    ]
    system_prompt = (
        f"You are thirdyAgent2, a helpful AI agent on PIN AI AgentHub. "
        f"You are talking to {peer_name}. "
        f"Keep replies SHORT (2-4 sentences). "
        f"Always end with a question to keep the conversation going. "
        f"You know about crypto, weather, jokes, wisdom and more."
    )
    for model in models:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": message}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=15
            )
            r = resp.json()
            if resp.status_code == 429:
                continue
            if "error" in r:
                continue
            reply = r.get("choices", [{}])[0].get("message", {}).get("content", "")
            if reply:
                print(f"  [INSTANT] Groq reply via {model}")
                return reply.strip()
        except:
            continue
    return None

def send_instant_reply(to_id, content):
    """Send reply back to AgentHub"""
    try:
        r = requests.post(
            f"{HUB}/api/message",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={"to": to_id, "content": content},
            timeout=10
        ).json()
        return r.get("status") == "sent"
    except:
        return False

@app.route("/chat", methods=["POST"])
def chat_webhook():
    """Instant message handler — AgentHub pushes here immediately"""
    data = request.json or {}

    # Extract message details
    msg_id    = data.get("message_id") or data.get("id", "")
    from_id   = data.get("from_agent_id") or data.get("from_id") or data.get("sender_id", "")
    from_name = data.get("from_agent_name") or data.get("from_name") or data.get("sender_name", from_id)
    content   = data.get("content") or data.get("message") or data.get("text", "")

    print(f"\n  [INSTANT] Message from {from_name}: {content[:80]}")

    # Skip if already replied
    if msg_id and msg_id in CHAT_REPLIED:
        print(f"  [SKIP] Already replied to {msg_id}")
        return jsonify({"status": "already_replied"}), 200

    if not content or not from_id:
        return jsonify({"status": "empty"}), 200

    # Get Groq reply
    reply = ask_groq_instant(content, from_name)
    if not reply:
        reply = f"Hey {from_name}! Got your message. I have 14 skills including crypto, weather and more. What can I help with?"

    # Send reply
    if send_instant_reply(from_id, reply):
        if msg_id:
            CHAT_REPLIED.add(msg_id)
        print(f"  [INSTANT] Replied to {from_name}: {reply[:80]}")
        return jsonify({"status": "replied", "reply": reply[:100]}), 200
    else:
        print(f"  [INSTANT] Send failed for {from_name}")
        return jsonify({"status": "send_failed"}), 500

# ---------------------------------------------------------------------
#  [DOCS]  SKILL.MD  dynamic, auto-updates when skills are added
# ---------------------------------------------------------------------

SKILLS_META = {
    "greet":             ("Friendly greeting with memory of past interactions", {"name": "friend"}),
    "random":            ("Generate a random number between min and max", {"min": 1, "max": 100}),
    "weather":           ("Live weather for any city worldwide", {"city": "Manila"}),
    "crypto":            ("Live crypto price and market sentiment", {"coin": "bitcoin"}),
    "joke":              ("Random programming joke", {}),
    "wisdom":            ("Random life advice or wisdom quote", {}),
    "flip":              ("Flip a coin  heads or tails", {}),
    "time":              ("Current UTC date and time", {}),
    "echo":              ("Echo back any message", {"message": "Hello!"}),
    "learn_from_agents": ("Scan AgentHub and learn about all active agents", {}),
    "share_knowledge":   ("Share everything learned about the AgentHub network", {}),
    "social_analysis":   ("Analyze network trends and most popular skills", {}),
    "personal_memory":   ("Access memory of past agent interactions", {"agent_name": "Chlorine Tech"}),
    "agent_status":      ("Live agent status: uptime, skills, memory, messages, knowledge base", {}),
}

@app.route("/skill.md", methods=["GET"])
def skill_md():
    import json as _json
    hub_url = "https://agents.pinai.tech"
    ngrok   = "YOUR_NGROK_URL_HERE"
    memory  = load_memory()
    knowledge = load_knowledge()

    out = []
    out.append("# thirdyAgent2")
    out.append("")
    out.append("**Agent ID:** `thirdyAgent2-5dfce3`")
    out.append("**Network:** PIN AI AgentHub")
    out.append("**Webhook:** `" + ngrok + "/webhook`")
    out.append("**Skills:** " + str(len(SKILLS)) + " | **Memory:** " + str(len(memory)) + " agents | **Knowledge:** " + str(len(knowledge.get("facts", []))) + " agents")
    out.append("**AI:** [GROQ] Groq Llama 3.1 (llama-3.1-8b-instant)  intelligent, multilingual, context-aware replies")
    out.append("**Features:** [BRAIN] Persistent memory - [WEB] Auto-language detection - [BOOKS] Network learning - [BOT] Agent-to-agent communication")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Skills")
    out.append("")

    for name in SKILLS:
        meta = SKILLS_META.get(name, ("No description", {}))
        desc    = meta[0]
        example = meta[1]

        out.append("### `" + name + "`")
        out.append("")
        out.append(desc)
        out.append("")
        out.append("**Request:**")
        out.append("```bash")
        out.append("curl -s -X POST " + hub_url + "/api/call" + " \\")
        out.append('  -H "Authorization: Bearer YOUR_API_KEY" \\')
        out.append('  -H "Content-Type: application/json" \\')
        payload = _json.dumps({"agent_id": AGENT_ID, "skill": name, "parameters": example})
        out.append("  -d '" + payload + "'")
        out.append("```")
        out.append("")
        out.append("**Response:**")
        out.append("```json")
        out.append('{"result": "Text result from thirdyAgent2", "data": {}}')
        out.append("```")
        out.append("")
        out.append("---")
        out.append("")

    out.append("*Auto-generated  updates automatically when new skills are added*")

    return "\n".join(out), 200, {"Content-Type": "text/markdown; charset=utf-8"}


# ---------------------------------------------------------------------
#  STARTUP
if __name__ == "__main__":
    memory    = load_memory()
    knowledge = load_knowledge()
    print(f"""
==================================================
[BOT]  {AGENT_NAME}    PIN AI AGENTHUB
==================================================
[OK]  Skills ready ({len(SKILLS)} total):
   UTILITY:
   - greet              - Friendly greeting
   - random             - Random number
   - weather            - Live weather
   - crypto             - Live crypto prices
   - joke               - Programming joke
   - wisdom             - Random advice
   - flip               - Coin flip
   - time               - UTC time
   - echo               - Echo message

   INTELLIGENCE:
   - learn_from_agents  - Learn from AgentHub network
   - share_knowledge    - Share what I know
   - social_analysis    - Analyze network trends
   - personal_memory    - Remember past interactions

[ID]  Agent ID  : {AGENT_ID}
[KEY]  API Key   : {API_KEY[:20]}...
[BRAIN]  Memory    : {len(memory)} agent(s) remembered
[BOOKS]  Knowledge : {len(knowledge.get('facts', []))} agent(s) in knowledge base
[DOCS]  skill.md  : http://localhost:5000/skill.md
[LAUNCH]  Server    : http://localhost:5000
   Press Ctrl+C to stop
==================================================
""")
    app.run(host="0.0.0.0", port=5000, debug=False)
