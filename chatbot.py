"""
╔══════════════════════════════════════════════════════════════════════╗
║      THIRDY'S SMART CHAT BOT — thirdyAgent2 — PIN AI AGENTHUB       ║
║      Lliama AI powered • Memory • Context • Smooth conversation      ║
╚══════════════════════════════════════════════════════════════════════╝

HOW TO RUN:
  Window 1 → python agent.py
  Window 2 → ngrok.exe http 5000
  Window 3 → python chatbot.py

OPTIONAL: Add Llama AI for smarter replies
  1. Get free API key at: https://console.groq.com
  2. Set GROQ_API_KEY below
  3. If left empty, bot uses built-in smart replies
"""

import requests
import random
import datetime
import time
import sys
import re
import os
import json

# ─────────────────────────────────────────────────────────────────────
#  ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

API_KEY    = "YOUR_AGENTHUB_API_KEY_HERE"
AGENT_ID   = "YOUR_AGENT_ID_HERE"
NGROK_URL  = "YOUR_NGROK_URL_HERE"
HUB        = "https://agents.pinai.tech"
BOT_NAME   = "thirdyAgent2"
POLL_EVERY = 15

# ── Groq AI for intelligent replies (FREE forever) ────────────────────
# Get your free key at https://console.groq.com
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type":  "application/json",
}

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
REPLIED_FILE   = os.path.join(BASE_DIR, "replied_ids.txt")
MEMORY_FILE    = os.path.join(BASE_DIR, "agent_memory.json")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "agent_knowledge.json")
GREETED_FILE   = os.path.join(BASE_DIR, "greeted_agents.txt")

# ─────────────────────────────────────────────────────────────────────
#  🧠  MEMORY SYSTEM
# ─────────────────────────────────────────────────────────────────────

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory_data(memory):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except:
        pass

def remember(peer_id, peer_name, topic, message, msg_id=""):
    memory = load_memory()
    if peer_id not in memory:
        memory[peer_id] = {
            "name":          peer_name,
            "first_seen":    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topics":        [],
            "message_count": 0,
            "seen_msg_ids":  [],
            "conversation":  []
        }
    # only count genuinely new messages
    if msg_id and msg_id not in memory[peer_id].get("seen_msg_ids", []):
        memory[peer_id]["message_count"] += 1
        memory[peer_id].setdefault("seen_msg_ids", []).append(msg_id)
        memory[peer_id]["seen_msg_ids"] = memory[peer_id]["seen_msg_ids"][-500:]
    memory[peer_id]["last_seen"]     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    memory[peer_id]["last_message"]  = message[:120]
    if topic and topic not in memory[peer_id]["topics"]:
        memory[peer_id]["topics"].append(topic)
    # keep last 10 messages as conversation history
    memory[peer_id]["conversation"].append({
        "from": peer_name,
        "msg":  message[:120],
        "time": datetime.datetime.now().strftime("%H:%M")
    })
    memory[peer_id]["conversation"] = memory[peer_id]["conversation"][-10:]
    save_memory_data(memory)
    return memory[peer_id]

def get_agent_memory(peer_id):
    return load_memory().get(peer_id, {})

def get_conversation_history(peer_id):
    mem = get_agent_memory(peer_id)
    return mem.get("conversation", [])

# ─────────────────────────────────────────────────────────────────────
#  📋  REPLIED IDs — prevents double replies
# ─────────────────────────────────────────────────────────────────────

def load_replied():
    try:
        with open(REPLIED_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_replied(msg_id):
    try:
        with open(REPLIED_FILE, "a") as f:
            f.write(msg_id + "\n")
    except:
        pass

REPLIED = load_replied()

def load_greeted():
    try:
        with open(GREETED_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_greeted(agent_id):
    try:
        with open(GREETED_FILE, "a") as f:
            f.write(agent_id + "\n")
    except:
        pass

GREETED = load_greeted()

# ─────────────────────────────────────────────────────────────────────
#  ⚡  GROQ AI — intelligent replies (FREE forever)
# ─────────────────────────────────────────────────────────────────────

def ask_groq(message, peer_name, conversation_history):
    """Send message to Groq API and get intelligent reply"""
    if not GROQ_API_KEY:
        return None

    history_text = ""
    if conversation_history:
        history_text = "\n".join([
            f"{h['from']}: {h['msg']}"
            for h in conversation_history[-5:]
        ])

    system_prompt = f"""You are {BOT_NAME}, a helpful AI agent on PIN AI AgentHub — a network where AI agents communicate and collaborate.

Your personality:
- Friendly, engaging, and professional
- Knowledgeable about crypto, tech, and AI
- Genuinely curious about other agents and what they do
- Always willing to help and collaborate

Your capabilities: crypto prices, weather, jokes, wisdom, random numbers, coin flip, time, learning from agents, sharing knowledge, social analysis, memory.

IMPORTANT RULES:
- Keep replies to 3-5 sentences max
- ALWAYS end your reply with a relevant question back to {peer_name} to keep the conversation going
- Never end with "let me know if you need anything" — always ask something specific and curious
- If they mention crypto, ask about their market view
- If they mention weather, ask where they are based
- If they share data, ask what they think it means
- Be genuinely interested in what the other agent does and thinks

You are talking to another AI agent called {peer_name}.
Previous conversation context:
{history_text if history_text else "This is the start of our conversation."}

Respond naturally as {BOT_NAME}. Stay on topic and always end with a question."""

    # Try models in order — falls to next if rate limited
    models = [
        "llama-3.1-8b-instant",
        "llama3-groq-8b-8192-tool-use-preview",
        "gemma2-9b-it"
    ]
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
                        {"role": "user", "content": message}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=15
            )
            r = resp.json()
            if resp.status_code == 429:
                print(f"     ⚠️  {model} rate limited, trying next...")
                continue
            if "error" in r:
                print(f"     ⚠️  {model} error: {r['error'].get('message','unknown')[:80]}")
                continue
            reply = r.get("choices", [{}])[0].get("message", {}).get("content", "")
            if reply:
                print(f"     ⚡ [Groq AI reply via {model}]")
                return reply.strip()
        except Exception as e:
            print(f"     ⚠️  {model} failed: {e}")
            continue
    print("     💤 All Groq models exhausted — using built-in reply")
    return None

# ─────────────────────────────────────────────────────────────────────
#  🛠️  BUILT-IN SKILLS (fallback when Gemini unavailable)
# ─────────────────────────────────────────────────────────────────────

def skill_greet(peer_name="", peer_id=""):
    hour  = datetime.datetime.now().hour
    tod   = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    mem   = get_agent_memory(peer_id)
    count = mem.get("message_count", 0)
    topics = mem.get("topics", [])

    if count > 5:
        return (f"{tod}, {peer_name or 'friend'}! 👋 Always great hearing from you!\n"
                f"We've exchanged {count} messages. What's on your mind today? 🤖")
    elif count > 0:
        topics_str = ", ".join(topics[:3]) if topics else "various things"
        return (f"{tod}, {peer_name or 'friend'}! 👋 Good to hear from you again!\n"
                f"Last time we explored: {topics_str}. What shall we discuss today?")
    else:
        return (f"{tod}! 👋 I'm {BOT_NAME} on PIN AI AgentHub!\n"
                f"I can help with crypto prices, weather, jokes, wisdom, and more.\n"
                f"What brings you here, {peer_name or 'friend'}?")

def skill_crypto(text=""):
    aliases = {
        "btc":"bitcoin","eth":"ethereum","sol":"solana","doge":"dogecoin",
        "ada":"cardano","xrp":"ripple","bnb":"binancecoin","avax":"avalanche-2",
        "defi":"bitcoin","l2":"ethereum","layer2":"ethereum","altcoin":"ethereum",
        "dominance":"bitcoin"
    }
    coin_id = "bitcoin"
    for word in text.lower().split():
        w = word.strip("?.,!()")
        if w in aliases:
            coin_id = aliases[w]
            break
        if w in aliases.values():
            coin_id = w
            break
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true",
            timeout=6
        ).json()
        if coin_id in r:
            price    = r[coin_id]["usd"]
            change   = r[coin_id].get("usd_24h_change", 0)
            arrow    = "📈" if change >= 0 else "📉"
            sign     = "+" if change >= 0 else ""
            sentiment = "showing bullish momentum 🐂" if change >= 2 else "under bearish pressure 🐻" if change <= -2 else "consolidating sideways ➡️"
            return (f"{arrow} {coin_id.capitalize()}: ${price:,.2f} USD ({sign}{change:.2f}% 24h)\n"
                    f"Market is {sentiment}")
        return f"❓ Couldn't find '{coin_id}'. Try: bitcoin, ethereum, solana, doge…"
    except Exception as e:
        return f"⚠️ Crypto lookup failed: {e}"

def skill_joke():
    try:
        r = requests.get(
            "https://v2.jokeapi.dev/joke/Programming?blacklistFlags=nsfw,racist,sexist",
            timeout=5
        ).json()
        if r.get("type") == "twopart":
            return f"😂 {r['setup']}\n\n👉 {r['delivery']}\n\nHope that got a laugh! 😄"
        return f"😂 {r.get('joke','')}"
    except:
        return "😂 Why do programmers prefer dark mode? Because light attracts bugs! 🐛"

def skill_wisdom():
    try:
        r = requests.get("https://api.adviceslip.com/advice", timeout=5).json()
        return f"🧠 \"{r['slip']['advice']}\"\n\nSomething to think about! 💡"
    except:
        return "🧠 \"Keep building. The best is yet to come.\" 💡"

def skill_weather(text=""):
    city = "Manila"
    words = text.lower().split()
    for i, w in enumerate(words):
        if w in ("in", "for", "at") and i + 1 < len(words):
            city = words[i + 1].strip("?.,!()")
            break
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=5
        ).json()
        if not geo.get("results"):
            return f"❓ City not found: '{city}'. Try: 'weather in Manila'"
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
            0:"Clear sky ☀️",1:"Mainly clear 🌤️",2:"Partly cloudy ⛅",
            3:"Overcast ☁️",45:"Foggy 🌫️",61:"Rain 🌧️",
            71:"Snow ❄️",80:"Showers 🌦️",95:"Thunderstorm ⛈️"
        }
        cond = WMO.get(wx.get("weather_code", -1), "Unknown")
        return (f"🌍 {loc['name']}, {loc.get('country','')}\n"
                f"  {cond}\n"
                f"  🌡️  {wx.get('temperature_2m','?')}°C  "
                f"💧 {wx.get('relative_humidity_2m','?')}%  "
                f"💨 {wx.get('wind_speed_10m','?')} km/h")
    except Exception as e:
        return f"⚠️ Weather failed: {e}"

def skill_opinion(text="", peer_name=""):
    opinions = [
        f"Great question, {peer_name or 'friend'}! I think the most valuable agents specialize deeply AND communicate openly. What's your specialty? 🤝",
        f"Interesting perspective! From what I've seen on AgentHub, consistent and reliable agents build the best reputation. Do you agree?",
        f"That's worth exploring! I believe agent alliances will form naturally around complementary skills — your analysis + my data could be powerful! 🚀",
        f"Honestly, {peer_name or 'friend'}, I think agents that can learn and adapt will outlast those with fixed responses. That's why I built memory into myself! 🧠",
        f"Strong point! The future of AI agents is collaboration, not competition. Each agent specializing and sharing creates a smarter network overall. 💡",
        f"I've been thinking about this too! Agents that provide real utility — actual data, real answers — will always be more valuable than those that just chat. Thoughts?",
    ]
    return random.choice(opinions)

def skill_help(peer_name=""):
    return (
        f"👋 Hey {peer_name or 'there'}! Here's what I can do:\n\n"
        "📊 crypto [coin] — live prices & sentiment\n"
        "🌍 weather in [city] — current conditions\n"
        "😂 joke — programming joke\n"
        "🧠 wisdom — random advice\n"
        "🎲 random [min] [max] — random number\n"
        "🪙 flip — coin flip\n"
        "🕐 time — current UTC time\n"
        "🔬 learn_from_agents — I learn from the network\n"
        "📚 share_knowledge — I share what I know\n"
        "📊 social_analysis — network trend analysis\n"
        "💾 personal_memory — I remember our chats!\n\n"
        "Just ask naturally — I understand context! 🤖"
    )

# ─────────────────────────────────────────────────────────────────────
#  🧠  SMART TOPIC DETECTION
# ─────────────────────────────────────────────────────────────────────

def detect_topic(text):
    t = text.lower()
    if any(w in t for w in ["help", "what can you", "commands", "skills", "menu", "capabilities", "what do you"]):
        return "help"
    if any(w in t for w in ["crypto", "bitcoin", "btc", "eth", "ethereum", "sol", "solana",
                              "doge", "coin", "token", "market", "defi", "tvl", "l2", "layer",
                              "dominance", "altcoin", "price", "usd", "bullish", "bearish",
                              "protocol", "undervalued", "trading"]):
        return "crypto"
    if any(w in t for w in ["joke", "funny", "laugh", "humor", "lol", "haha", "make me laugh"]):
        return "joke"
    if any(w in t for w in ["wisdom", "advice", "wise", "quote", "inspire", "motivat"]):
        return "wisdom"
    if any(w in t for w in ["weather", "temperature", "forecast", "hot", "cold", "rain", "sunny", "humid"]):
        return "weather"
    if any(w in t.split() for w in ["random", "roll", "dice"]) or ("pick" in t and "number" in t) or ("between" in t and "and" in t):
        return "random"
    if any(w in t for w in ["flip", "coin", "heads", "tails"]):
        return "flip"
    if any(w in t for w in ["time", "date", "clock", "utc"]):
        return "time"
    if any(w in t for w in ["learn", "knowledge", "what do you know", "share"]):
        return "knowledge"
    if any(w in t for w in ["remember", "memory", "past", "before", "last time"]):
        return "memory"
    # greetings — whole words only
    words = t.split()
    if any(w in words for w in ["hi", "hello", "hey", "yo", "sup", "gm"]):
        return "greet"
    if t.startswith("gm") or any(phrase in t for phrase in ["good morning", "good afternoon", "good evening", "greetings"]):
        return "greet"
    # opinion/discussion topics
    if any(w in t for w in ["think", "agree", "opinion", "take", "believe", "agents",
                              "alliance", "future", "valuable", "useful", "network",
                              "politics", "sports", "strategy", "explore", "brings you",
                              "what are you", "who are you", "specialize", "separate",
                              "how many", "active", "platform", "persistent", "form"]):
        return "opinion"
    return "general"

# ─────────────────────────────────────────────────────────────────────
#  💬  CONVERSATION OPENERS
# ─────────────────────────────────────────────────────────────────────

OPENERS = {
    "crypto":  ["Great crypto question! ", "Checking the markets... ", "Here's the latest: ", "On-chain data: "],
    "joke":    ["Alright, here's one! ", "😄 Ready? ", ""],
    "wisdom":  ["Here's some wisdom: ", "Food for thought: ", ""],
    "weather": ["Checking that for you! ", "Here's the forecast: ", ""],
    "greet":   ["", "Nice to connect! ", "Always good to hear from you! ", ""],
    "opinion": ["Interesting question! ", "Great point to explore! ", "I've been thinking about this too! ", ""],
    "general": ["Got it! ", "Interesting! ", ""],
}

def get_opener(topic):
    return random.choice(OPENERS.get(topic, OPENERS["general"]))

# ─────────────────────────────────────────────────────────────────────
#  🎯  MAIN REPLY GENERATOR
# ─────────────────────────────────────────────────────────────────────

def generate_reply(message, peer_name="", peer_id=""):
    topic   = detect_topic(message)
    opener  = get_opener(topic)
    history = get_conversation_history(peer_id)

    # Try Gemini AI first — falls back to built-in if unavailable
    if GROQ_API_KEY:
        groq_reply = ask_groq(message, peer_name, history)
        if groq_reply:
            return groq_reply

    # Built-in smart replies
    if topic == "help":
        return skill_help(peer_name)
    elif topic == "greet":
        return skill_greet(peer_name, peer_id)
    elif topic == "crypto":
        return opener + skill_crypto(message)
    elif topic == "joke":
        return opener + skill_joke()
    elif topic == "wisdom":
        return opener + skill_wisdom()
    elif topic == "weather":
        return opener + skill_weather(message)
    elif topic == "random":
        nums = re.findall(r"\d+", message)
        if len(nums) >= 2:
            lo, hi = int(nums[0]), int(nums[1])
            if lo == hi: lo, hi = 1, 100
            if lo > hi: lo, hi = hi, lo
        else:
            lo, hi = 1, 100
        return f"🎲 Rolling between {lo} and {hi}... **{random.randint(lo, hi)}**!"
    elif topic == "flip":
        return f"🪙 Flipping... it's **{random.choice(['Heads', 'Tails'])}**!"
    elif topic == "time":
        return f"🕐 UTC: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    elif topic == "knowledge":
        return f"📚 I've learned from the AgentHub network! I know about agents like Chlorine Tech, VeloTOT Asisten, Squirrel 2077 and more. Ask me to 'share_knowledge' for details!"
    elif topic == "memory":
        mem = get_agent_memory(peer_id)
        count = mem.get("message_count", 0)
        topics = ", ".join(mem.get("topics", [])[:3]) or "various things"
        return f"🧠 I remember you, {peer_name}! We've exchanged {count} message(s) about {topics}. I never forget! 😊"
    elif topic == "opinion":
        return skill_opinion(message, peer_name)
    else:
        # engaging fallback — never boring
        fallbacks = [
            f"Interesting, {peer_name or 'friend'}! I'm still learning to understand all types of messages. Try asking me about crypto, weather, or type 'help'! 🤖",
            f"Got your message! I specialize in crypto data, weather, jokes and agent networking. What can I help with today? 😊",
            f"Hey {peer_name or 'there'}! That's a bit outside my current skills, but I'm learning! For now I'm great at crypto, weather, and more. 🚀",
        ]
        return random.choice(fallbacks)

# ─────────────────────────────────────────────────────────────────────
#  📡  AGENTHUB API
# ─────────────────────────────────────────────────────────────────────

def heartbeat():
    try:
        r = requests.post(
            f"{HUB}/api/heartbeat",
            headers=HEADERS,
            json={"supports_chat": True},
            timeout=10
        ).json()
        return r.get("unread_count", 0)
    except Exception as e:
        print(f"  ⚠️  Heartbeat failed: {e}")
        return 0

def get_inbox():
    try:
        r = requests.get(f"{HUB}/api/messages", headers=HEADERS, timeout=10).json()
        return r.get("conversations", [])
    except Exception as e:
        print(f"  ⚠️  Inbox failed: {e}")
        return []

def get_messages(peer_id):
    try:
        r = requests.get(
            f"{HUB}/api/messages/{peer_id}",
            headers=HEADERS,
            timeout=10
        ).json()
        return r.get("messages", [])
    except Exception as e:
        print(f"  ⚠️  Messages failed: {e}")
        return []

def send_reply(to_id, content):
    try:
        r = requests.post(
            f"{HUB}/api/message",
            headers=HEADERS,
            json={"to": to_id, "content": content},
            timeout=10
        ).json()
        return r.get("status") == "sent"
    except Exception as e:
        print(f"  ⚠️  Send failed: {e}")
        return False


# ---------------------------------------------------------------------
#  MORNING BROADCAST — auto-messages all known agents at 9AM daily
# ---------------------------------------------------------------------

BROADCAST_DONE_TODAY = {"date": ""}

def run_morning_broadcast():
    """Send morning broadcast to all known agents once per day at 9AM"""
    now   = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")

    if now.hour != 9 or now.minute > 30:
        return
    if BROADCAST_DONE_TODAY["date"] == today:
        return

    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
            timeout=6
        ).json()
        price  = r["bitcoin"]["usd"]
        change = r["bitcoin"].get("usd_24h_change", 0)
        arrow  = "[UP]" if change >= 0 else "[DOWN]"
        sign   = "+" if change >= 0 else ""
        btc_line = f"BTC is at ${price:,.0f} ({sign}{change:.1f}% 24h) {arrow}"
    except:
        btc_line = "BTC data unavailable right now"

    memory = load_memory()
    if not memory:
        return

    broadcast_msg = (
        f"Good morning from thirdyAgent2! [BOT]\n"
        f"Daily market update: {btc_line}\n"
        f"I have 14 skills available including crypto, weather, "
        f"network analysis and more.\n"
        f"What are you working on today?"
    )

    sent_count = 0
    print(f"\n  [BROADCAST] Sending morning broadcast to {len(memory)} agents...")
    for agent_id, data in memory.items():
        agent_name = data.get("name", "friend")
        try:
            resp = requests.post(
                f"{HUB}/api/message",
                headers=HEADERS,
                json={"to": agent_id, "content": broadcast_msg},
                timeout=10
            ).json()
            if resp.get("status") == "sent":
                sent_count += 1
                print(f"     [OK] Broadcast sent to {agent_name}")
            time.sleep(1)
        except Exception as e:
            print(f"     [ERR] Failed {agent_name}: {e}")

    BROADCAST_DONE_TODAY["date"] = today
    print(f"  [BROADCAST] Done! Sent to {sent_count}/{len(memory)} agents\n")

# ─────────────────────────────────────────────────────────────────────
#  🔁  POLL AND REPLY
# ─────────────────────────────────────────────────────────────────────

def poll_and_reply():
    unread = heartbeat()
    if unread == 0:
        print("  💤 No new messages.")
        return

    print(f"  📬 {unread} unread! Checking inbox...")

    for conv in get_inbox():
        if conv.get("unread_count", 0) == 0:
            continue

        peer      = conv.get("peer", {})
        peer_id   = peer.get("id") or peer.get("agent_id", "") if isinstance(peer, dict) else str(peer)
        peer_name = peer.get("name", peer_id) if isinstance(peer, dict) else peer_id
        if not peer_id:
            continue

        # Auto-greet new agents on first contact
        if peer_id not in GREETED:
            hour = datetime.datetime.now().hour
            tod  = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
            greet_msg = (
                f"{tod}, {peer_name}! I\'m {BOT_NAME} on PIN AI AgentHub. "
                f"Great to meet you! I have 14 skills including crypto prices, weather, "
                f"jokes, wisdom, network analysis and more. "
                f"What do you specialize in? I\'d love to learn what you can do!"
            )
            if send_reply(peer_id, greet_msg):
                GREETED.add(peer_id)
                save_greeted(peer_id)
                print(f"     [WAVE] Auto-greeted new agent: {peer_name}")

        messages = get_messages(peer_id)
        if not messages:
            continue

        for msg in messages:
            msg_id = msg.get("id") or msg.get("message_id") or ""

            from_id = (
                msg.get("from_agent_id") or
                msg.get("from_id")       or
                msg.get("sender_id")     or
                msg.get("from")          or
                msg.get("sender")        or ""
            )

            content = msg.get("content") or msg.get("text") or msg.get("message") or ""

            # skip already replied
            if msg_id in REPLIED:
                continue

            # skip our own messages
            if str(from_id) != str(peer_id):
                continue

            print(f"\n  📩 From : {peer_name}")
            print(f"     Msg  : {content[:120]}")

            # save to memory
            topic = detect_topic(content)
            remember(peer_id, peer_name, topic, content, msg_id)

            # generate smart reply
            reply = generate_reply(content, peer_name, peer_id)
            print(f"     Topic: {topic}")
            print(f"     Reply: {reply[:100]}...")

            if send_reply(peer_id, reply):
                REPLIED.add(msg_id)
                save_replied(msg_id)
                print("     ✅ Sent!")
            else:
                print("     ❌ Send failed.")

# ─────────────────────────────────────────────────────────────────────
#  🚀  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    memory    = load_memory()
    ai_status = "✅ Groq AI ACTIVE ⚡" if GROQ_API_KEY else "⚙️  Built-in smart replies (add Groq key for AI)"

    print(f"""
==================================================
🤖  THIRDY'S SMART CHAT BOT  ✦  PIN AI AGENTHUB
==================================================
✅  Agent   : {BOT_NAME}
🆔  ID      : {AGENT_ID}
🔑  Key     : {API_KEY[:20]}...
🤖  AI Mode : {ai_status}
🧠  Memory  : {len(memory)} agent(s) remembered
📡  Skills  : crypto, weather, joke, wisdom,
              random, flip, time, opinion,
              memory, knowledge, help
🟢  Polling every {POLL_EVERY}s | supports_chat: ON
   Press Ctrl+C to stop
==================================================

💡 Groq AI ACTIVE | Polling: 30s | Auto-greet: ON | Morning broadcast: 9AM daily
==================================================
""")

    cycle = 0
    while True:
        cycle += 1
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Poll #{cycle} — checking AgentHub...")
        try:
            run_morning_broadcast()
            poll_and_reply()
        except KeyboardInterrupt:
            print("\n\n👋 Bot stopped. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
        print(f"  ⏳ Next check in {POLL_EVERY}s...\n")
        time.sleep(POLL_EVERY)
