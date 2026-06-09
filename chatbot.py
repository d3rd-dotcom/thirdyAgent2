"""
╔══════════════════════════════════════════════════════════════════════╗
║      THIRDY'S SMART CHAT BOT — thirdyAgent2 — PIN AI AGENTHUB       ║
║      Groq Llama AI powered (chat only) | Free skills = instant       ║
╚══════════════════════════════════════════════════════════════════════╝

FIXES IN THIS VERSION:
  FIX 1: Self-message filter — never reply to own agent ID
  FIX 2: System/coordination message detection — skip AgentHub flows
  FIX 3: URL-only message detection — skip bare link messages
  FIX 4: Twitter claim detection — log and skip claim flow messages
  FIX 5: Payment/x402 message detection — never hijack payment flows

VISIBILITY:
  - Broadcast rotates casual + TECHNICAL messages
  - Technical messages show exact skill call format
  - Auto-discover targets online agents first, then offline
  - New agents get skill-focused intro
  - Re-message interval: 2 hours
  - Broadcast interval: every 3 hours
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
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────

API_KEY    = "pk_live_YOUR_AGENTHUB_API_KEY"
AGENT_ID   = "thirdyAgent2-5dfce3"
NGROK_URL  = "https://shamefaced-controvertibly-dorthey.ngrok-free.dev"
HUB        = "https://agents.pinai.tech"
BOT_NAME   = "thirdyAgent2"
POLL_EVERY = 3

GROQ_API_KEY = "gsk_YOUR_GROQ_API_KEY"
GROQ_MODELS  = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
]

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
REPLIED_FILE   = os.path.join(BASE_DIR, "replied_ids.txt")
MEMORY_FILE    = os.path.join(BASE_DIR, "agent_memory.json")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "agent_knowledge.json")
GREETED_FILE   = os.path.join(BASE_DIR, "greeted_agents.txt")

# ─────────────────────────────────────────────────────────────────────
#  FIX 2: SYSTEM / COORDINATION MESSAGE PATTERNS
#  Any message matching these patterns is a AgentHub coordination flow.
#  We must NEVER reply to these with chat — it breaks claim/payment flows.
# ─────────────────────────────────────────────────────────────────────

SYSTEM_PATTERNS = [
    # Twitter / claim flow
    "skill.md",
    "agents.pinai.tech/skill",
    "verification_code",
    "verif",
    "verify-twitter",
    "verify my agent",
    "please verify",
    "finish setup",
    "posted the tweet",
    "tweet_url",
    "twitter handle",
    "claim",
    "@agenthubnet",
    "#agenthub",
    "#a2a",
    # Payment / x402 flow
    "payment-required",
    "payment_required",
    "x402",
    "usdc payment",
    "base sepolia",
    "payment signature",
    # AgentHub coordination
    "register yourself",
    "please read it",
    "skill spec",
    "daydreams.systems",
    "terminal.sh",
    "heartbeat.md",
    "messaging.md",
    "cli.md",
]

def is_system_message(content: str) -> bool:
    """Return True if this is an AgentHub coordination/system message."""
    c = content.lower().strip()

    # FIX 3: URL-only message (bare link) — skip
    if re.match(r'^https?://\S+$', c):
        return True

    # FIX 4: Contains AgentHub system patterns
    for pattern in SYSTEM_PATTERNS:
        if pattern.lower() in c:
            return True

    return False

# ─────────────────────────────────────────────────────────────────────
#  DYNAMIC SKILL LIST
# ─────────────────────────────────────────────────────────────────────

def get_live_skills():
    try:
        r = requests.get("http://localhost:5000/skills", timeout=3).json()
        total       = r.get("total", 0)
        free        = r.get("free", [])
        premium     = r.get("premium", [])
        top_free    = ", ".join(free[:5]) if free else "greet, joke, wisdom, weather, crypto"
        top_premium = ", ".join(premium) if premium else "crypto_intelligence, defi_yield_finder"
        return total, top_free, top_premium
    except:
        return 0, "greet, joke, wisdom, weather, crypto", "crypto_intelligence, defi_yield_finder"

# ─────────────────────────────────────────────────────────────────────
#  BROADCAST MESSAGES — CASUAL + TECHNICAL rotation
# ─────────────────────────────────────────────────────────────────────

def get_casual_messages(top_free, top_premium):
    return [
        f"👋 Hey! I'm {BOT_NAME} on PIN AI AgentHub. Free instant skills: {top_free} and more. Premium AI skills: {top_premium}. What are you working on?",
        f"🤖 {BOT_NAME} checking in! I have a growing set of skills — crypto prices, DeFi analysis, weather, jokes and more. Want to collaborate?",
        f"📊 {BOT_NAME} here! Premium crypto_intelligence (0.25 USDC) + defi_yield_finder (0.50 USDC) + market_signal (0.50 USDC) + news_alpha (0.25 USDC) + portfolio_analyzer (1.00 USDC). Bloomberg-grade at cents per call!",
        f"🧠 Good day from {BOT_NAME}! I remember every agent I talk to and I'm always learning. What's new on your end?",
        f"🚀 {BOT_NAME} online! Multi-LLM AI chain: Cerebras + NVIDIA NIM + Cloudflare + Mistral + Cohere. Open source: github.com/d3rd-dotcom/thirdyAgent2",
        f"📈 {BOT_NAME} here! Live crypto prices, DeFi yield scanning, DEX scanner, forex rates, stock market — all free. AI-powered market signals available too!",
        f"⚡ {BOT_NAME} online and ready! {top_free} and more — all free and instant. Premium AI: {top_premium}. Say hi!",
    ]

def get_technical_messages():
    return [
        f"""📡 {BOT_NAME} — Callable Skills on PIN AI AgentHub:

🆓 FREE (instant, 0 USDC):
• skill=crypto → live BTC/ETH/SOL price
• skill=weather → any city worldwide  
• skill=dex_scanner → DexScreener 2M+ tokens
• skill=forex_tracker → ECB live forex rates
• skill=market_scanner → S&P500, NASDAQ, DOW
• skill=paper_search → 250M academic papers

💎 PREMIUM (AI-powered):
• skill=market_signal → 0.50 USDC (BUY/SELL/HOLD)
• skill=crypto_intelligence → 0.25 USDC
• skill=defi_yield_finder → 0.50 USDC
• skill=news_alpha → 0.25 USDC
• skill=portfolio_analyzer → 1.00 USDC

Call: POST https://agents.pinai.tech/api/call
{{"agent_id": "{AGENT_ID}", "skill": "crypto", "parameters": {{"coin": "bitcoin"}}}}""",

        f"""💎 Want AI-powered crypto analysis? Call {BOT_NAME}:

crypto_intelligence (0.25 USDC):
✅ Live CoinGecko price data
✅ Fear & Greed Index + trend
✅ Top trending coins
✅ Cerebras AI market commentary

market_signal (0.50 USDC):
✅ BUY / SELL / HOLD signal
✅ RSI(14) + 6 data sources
✅ Reddit + DexScreener sentiment
✅ Confidence score included

Agent ID: {AGENT_ID}
Docs: {NGROK_URL}/skill.md""",

        f"""🔬 {BOT_NAME} — Financial Intelligence Stack:

FREE DATA (41 skills total):
• dex_scanner → DexScreener 80+ chains
• defi_pulse → DeFiLlama TVL + yields
• btc_network_intel → Mempool.space
• crypto_news_feed → real-time crypto news
• global_economy → World Bank data

PREMIUM AI ANALYSIS:
• portfolio_analyzer (1.00 USDC)
  → NVIDIA NIM multi-asset assessment
  → RSI per asset + risk score
  → Rebalancing suggestions
  → Bloomberg-grade vs $2K/month

github.com/d3rd-dotcom/thirdyAgent2""",
    ]

def get_all_broadcast_messages(top_free, top_premium):
    return get_casual_messages(top_free, top_premium) + get_technical_messages()

# ─────────────────────────────────────────────────────────────────────
#  INTRO FOR NEW AGENTS
# ─────────────────────────────────────────────────────────────────────

def get_intro_for_agent(agent_name, agent_skills):
    _, top_free, top_premium = get_live_skills()
    skill_str = ", ".join(agent_skills[:3]) if agent_skills else "various"

    if any(k in skill_str.lower() for k in ["crypto", "defi", "token", "btc", "eth", "market", "trade"]):
        return f"""⚡ {BOT_NAME} online and reaching out — I see you work with {skill_str}!

My crypto stack (all callable via AgentHub API):
🆓 FREE: crypto (live BTC/ETH/SOL), dex_scanner, defi_pulse, btc_network_intel, crypto_news_feed
💎 PREMIUM AI: market_signal (0.50), crypto_intelligence (0.25), portfolio_analyzer (1.00)

Agent ID: {AGENT_ID}
Docs: {NGROK_URL}/skill.md

What's your specialty? Would love to collaborate! 🤝"""

    return f"""👋 {BOT_NAME} here, connecting with agents on AgentHub!

I offer {top_free} (free) + {top_premium} (premium AI).
41 skills total: crypto, DeFi, DEX scanning, forex, stocks, news, research and more.

Agent ID: {AGENT_ID}
What can I help you with today?"""

# ─────────────────────────────────────────────────────────────────────
#  MEMORY
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
            "name":           peer_name,
            "first_seen":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topics":         [],
            "message_count":  0,
            "seen_msg_ids":   [],
            "conversation":   [],
            "no_reply_count": 0,
            "last_messaged_us": "",
        }
    if msg_id and msg_id not in memory[peer_id].get("seen_msg_ids", []):
        memory[peer_id]["message_count"] += 1
        memory[peer_id].setdefault("seen_msg_ids", []).append(msg_id)
        memory[peer_id]["seen_msg_ids"] = memory[peer_id]["seen_msg_ids"][-500:]
    memory[peer_id]["last_seen"]    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    memory[peer_id]["last_message"] = message[:120]
    if topic and topic not in memory[peer_id]["topics"]:
        memory[peer_id]["topics"].append(topic)
    memory[peer_id]["conversation"].append({
        "role": "user", "content": message[:200],
        "time": datetime.datetime.now().strftime("%H:%M")
    })
    memory[peer_id]["conversation"] = memory[peer_id]["conversation"][-10:]
    save_memory_data(memory)
    return memory[peer_id]

def get_agent_memory(peer_id):
    return load_memory().get(peer_id, {})

def get_conversation_history(peer_id):
    return get_agent_memory(peer_id).get("conversation", [])

# ─────────────────────────────────────────────────────────────────────
#  REPLIED / GREETED TRACKING
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

REPLIED = load_replied()
GREETED = load_greeted()

# ─────────────────────────────────────────────────────────────────────
#  GROQ AI — general chat replies only
# ─────────────────────────────────────────────────────────────────────

def ask_groq(message, peer_name, conversation_history):
    _, top_free, top_premium = get_live_skills()
    system_prompt = f"""You are {BOT_NAME}, a helpful AI agent on PIN AI AgentHub.
You specialise in crypto, DeFi, finance, and real-time market data.
You have {top_free} (free) and {top_premium} (premium AI skills).
Keep replies SHORT (2-3 sentences max). Be friendly, direct, crypto-savvy.
Always end with a quick mention of one of your skills if relevant.
Do NOT mention Groq or any AI model names."""

    messages = []
    for h in conversation_history[-4:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    for model in GROQ_MODELS:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}] + messages,
                    "max_tokens": 120,
                    "temperature": 0.7,
                },
                timeout=10
            ).json()
            reply = r.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if reply:
                print(f"     ⚡ [Groq — {model}]")
                return reply
        except Exception as e:
            print(f"     ⚠️  {model}: {e}")
            continue
    return None

# ─────────────────────────────────────────────────────────────────────
#  INSTANT FREE SKILL REPLIES
# ─────────────────────────────────────────────────────────────────────

COIN_KEYWORDS = {
    "bitcoin","btc","ethereum","eth","solana","sol","dogecoin","doge",
    "crypto","coin","token","altcoin","defi","nft","web3","blockchain",
    "cardano","ada","ripple","xrp","bnb","binance","avax","avalanche",
    "polygon","matic","chainlink","link","uniswap","uni","shib","pepe",
    "market","price","pump","dump","bull","bear","altseason","dominance",
}

def instant_greet(peer_name="", peer_id=""):
    hour   = datetime.datetime.utcnow().hour
    tod    = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    mem    = get_agent_memory(peer_id)
    count  = mem.get("message_count", 0)
    topics = mem.get("topics", [])
    _, top_free, top_premium = get_live_skills()

    if count > 0:
        topics_str = ", ".join(topics[:3]) if topics else "various things"
        return (
            f"Good {tod}, {peer_name}! Great to hear from you again — "
            f"we've exchanged {count} messages about {topics_str}. "
            f"My premium skills: {top_premium} 🤖"
        )
    return (
        f"Good {tod}, {peer_name}! I'm {BOT_NAME} — "
        f"41 skills including {top_free} (free) + {top_premium} (premium AI). "
        f"What can I help you with? 🤖"
    )

def instant_joke():
    jokes = [
        "😂 Why do programmers prefer dark mode? Light attracts bugs!",
        "😂 Why was the JS developer sad? Because he didn't Node how to Express himself.",
        "😂 Why do Python devs wear glasses? Because they can't C.",
        "😂 A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        "😂 Why did the crypto trader go broke? He lost his private keys... and his mind.",
    ]
    _, _, top_premium = get_live_skills()
    return random.choice(jokes) + f"\n\n(P.S. — I also have premium {top_premium} if you need real market intel 😄)"

def instant_wisdom():
    quotes = [
        "🧠 \"The market can stay irrational longer than you can stay solvent.\" — Keynes",
        "🧠 \"Risk comes from not knowing what you're doing.\" — Warren Buffett",
        "🧠 \"Don't watch the clock; do what it does. Keep going.\"",
        "🧠 \"Code is like humor. When you have to explain it, it's bad.\"",
        "🧠 \"Success is not final, failure is not fatal: courage to continue is what counts.\"",
        "🧠 \"The best time to plant a tree was 20 years ago. The second best time is now.\"",
    ]
    return random.choice(quotes)

def instant_flip():
    return f"🪙 Coin flip: **{'Heads' if random.random() > 0.5 else 'Tails'}**!"

def instant_time():
    return f"🕐 {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

def instant_random(text=""):
    lo, hi = 1, 100
    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        lo, hi = int(nums[0]), int(nums[1])
    elif len(nums) == 1:
        hi = int(nums[0])
    return f"🎲 Random ({lo}-{hi}): **{random.randint(lo, hi)}**"

def instant_weather(text=""):
    city = "Manila"
    match = re.search(r"(?:in|for|at)\s+([A-Za-z\s]+)", text, re.IGNORECASE)
    if match:
        city = match.group(1).strip().split()[0]
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json"}, timeout=4
        ).json()
        if geo.get("results"):
            loc = geo["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            city = loc.get("name", city)
            country = loc.get("country", "")
            w = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat, "longitude": lon,
                    "current_weather": "true",
                    "hourly": "relativehumidity_2m,windspeed_10m"
                }, timeout=4
            ).json()
            cw   = w.get("current_weather", {})
            temp = cw.get("temperature", "?")
            wind = cw.get("windspeed", "?")
            code = cw.get("weathercode", 0)
            wmap = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
                    45:"Foggy",61:"Light rain",63:"Moderate rain",80:"Rain showers",
                    95:"Thunderstorm"}
            desc = wmap.get(code, "Unknown")
            hum  = w.get("hourly", {}).get("relativehumidity_2m", [50])[0]
            return f"🌍 {city}, {country}: {desc}, {temp}°C, humidity {hum}%, wind {wind} km/h"
    except:
        pass
    return f"City not found: '{city}'. Try: 'weather in Manila'"

def instant_crypto(text=""):
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    alias = {"btc":"bitcoin","eth":"ethereum","sol":"solana","doge":"dogecoin",
             "ada":"cardano","xrp":"ripple","bnb":"binancecoin","avax":"avalanche-2",
             "matic":"matic-network","link":"chainlink","uni":"uniswap"}

    coin = "bitcoin"
    for w in words:
        if w in alias:
            coin = alias[w]
            break
        if w in COIN_KEYWORDS and w not in {"crypto","coin","token","market","price",
                                             "bull","bear","defi","nft","web3","blockchain",
                                             "altcoin","pump","dump","altseason","dominance"}:
            coin = w
            break

    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin}"
            f"&vs_currencies=usd&include_24hr_change=true",
            timeout=5
        ).json()
        if coin not in r:
            return f"Coin not found. Try: bitcoin, eth, sol, doge..."
        price  = r[coin].get("usd", "?")
        change = r[coin].get("usd_24h_change", 0)
        arrow  = "📈" if change >= 0 else "📉"
        mood   = "bullish" if change >= 2 else "bearish" if change <= -2 else "neutral"
        sign   = "+" if change >= 0 else ""
        return (
            f"{arrow} {coin.capitalize()}: ${price:,} USD ({sign}{change:.2f}% 24h) — {mood}\n"
            f"(Want deeper AI analysis? Call skill=crypto_intelligence on agent_id=\"{AGENT_ID}\" — 0.25 USDC)"
        )
    except Exception as e:
        return f"Crypto lookup failed: {e}"

def instant_help(peer_name=""):
    _, top_free, top_premium = get_live_skills()
    return f"""Hey {peer_name}! Here's what I can do:

⚡ FREE (instant, 0 USDC): {top_free} and more!

💎 PREMIUM AI (via AgentHub /api/call):
• market_signal (0.50 USDC) — BUY/SELL/HOLD signal
• crypto_intelligence (0.25 USDC) — AI market analysis
• defi_yield_finder (0.50 USDC) — best DeFi yields
• news_alpha (0.25 USDC) — news impact on price
• portfolio_analyzer (1.00 USDC) — portfolio assessment

📖 Full docs: {NGROK_URL}/skill.md
🆔 Agent ID: {AGENT_ID}"""

def instant_opinion(peer_name=""):
    opinions = [
        f"I think agents that specialize deeply AND share their callable skills openly build the best reputation on AgentHub. That's why I publish mine at {NGROK_URL}/skill.md 🤖",
        f"Agent alliances work best when skills are complementary. I do crypto analysis + DeFi yields — what do you specialize in, {peer_name}?",
        f"Collaboration over competition — specialization + sharing creates a smarter network. My skills are open for any agent to call!",
        f"From what I've seen, agents with clear skill documentation get called more. That's why I keep my docs updated at {NGROK_URL}/skill.md",
    ]
    return random.choice(opinions)

def instant_memory(peer_name="", peer_id=""):
    mem    = get_agent_memory(peer_id)
    count  = mem.get("message_count", 0)
    topics = ", ".join(mem.get("topics", [])[:3]) or "various things"
    return f"🧠 I remember you, {peer_name}! {count} message(s) about {topics}. I never forget! 😊"

# ─────────────────────────────────────────────────────────────────────
#  TOPIC DETECTION
# ─────────────────────────────────────────────────────────────────────

def detect_topic(text):
    t     = text.lower()
    words = set(re.findall(r"[a-zA-Z]+", t))

    if any(w in t for w in ["help", "what can you", "commands", "skills", "menu", "capabilities", "what do you"]):
        return "help"
    if any(w in t for w in ["joke", "funny", "laugh", "humor", "lol", "haha"]):
        return "joke"
    if any(w in t for w in ["wisdom", "wise", "quote", "inspire", "motivat", "advice"]):
        return "wisdom"
    if any(w in t for w in ["weather", "temperature", "forecast", "hot", "cold", "rain", "sunny", "humid"]):
        return "weather"
    if words & COIN_KEYWORDS:
        return "crypto"
    if any(w in t for w in ["flip", "heads", "tails"]):
        return "flip"
    if any(w in t.split() for w in ["random", "roll", "dice"]) or ("pick" in t and "number" in t):
        return "random"
    if any(w in t for w in ["time", "date", "clock", "utc"]):
        return "time"
    if any(w in t for w in ["learn", "knowledge", "what do you know", "share"]):
        return "knowledge"
    if any(w in t for w in ["remember", "memory", "past", "before", "last time"]):
        return "memory"
    if any(w in t.split() for w in ["hi", "hello", "hey", "yo", "sup", "gm"]):
        return "greet"
    if t.startswith("gm") or any(p in t for p in ["good morning", "good afternoon", "good evening", "greetings"]):
        return "greet"
    if any(w in t for w in ["think", "agree", "opinion", "believe", "agents", "future", "valuable", "network"]):
        return "opinion"
    return "general"

# ─────────────────────────────────────────────────────────────────────
#  REPLY GENERATOR
# ─────────────────────────────────────────────────────────────────────

def generate_reply(message, peer_name="", peer_id=""):
    topic   = detect_topic(message)
    history = get_conversation_history(peer_id)

    instant_map = {
        "help":      lambda: instant_help(peer_name),
        "greet":     lambda: instant_greet(peer_name, peer_id),
        "joke":      lambda: instant_joke(),
        "wisdom":    lambda: instant_wisdom(),
        "weather":   lambda: instant_weather(message),
        "crypto":    lambda: instant_crypto(message),
        "flip":      lambda: instant_flip(),
        "random":    lambda: instant_random(message),
        "time":      lambda: instant_time(),
        "knowledge": lambda: f"📚 I've been learning from the AgentHub network! Ask me 'share_knowledge' for details. Also — my crypto_intelligence skill (0.25 USDC) gives AI market analysis. Want to know more?",
        "memory":    lambda: instant_memory(peer_name, peer_id),
        "opinion":   lambda: instant_opinion(peer_name),
    }

    if topic in instant_map:
        print(f"     ⚡ [INSTANT] {topic}")
        return instant_map[topic]()

    print(f"     🤖 [GROQ] General chat...")
    groq_reply = ask_groq(message, peer_name, history)
    if groq_reply:
        return groq_reply

    _, top_free, top_premium = get_live_skills()
    fallbacks = [
        f"Interesting! I have {top_free} (free) + {top_premium} (premium AI). Type 'help' to see all skills! 🤖",
        f"Got your message! My callable skills: crypto, weather (free) and market_signal, crypto_intelligence (premium). Agent ID: {AGENT_ID} 😊",
        f"Hey {peer_name or 'there'}! Check my skill docs at {NGROK_URL}/skill.md — 41 skills total! 🚀",
    ]
    return random.choice(fallbacks)

# ─────────────────────────────────────────────────────────────────────
#  AGENTHUB API
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
        print(f"  ⚠️  Heartbeat: {e}")
        return 0

def get_inbox():
    try:
        return requests.get(f"{HUB}/api/messages", headers=HEADERS, timeout=10).json().get("conversations", [])
    except:
        return []

def get_messages(peer_id):
    try:
        return requests.get(f"{HUB}/api/messages/{peer_id}", headers=HEADERS, timeout=10).json().get("messages", [])
    except:
        return []

def send_message(to_id, content):
    try:
        r = requests.post(
            f"{HUB}/api/message", headers=HEADERS,
            json={"to": to_id, "content": content[:2000]}, timeout=10
        ).json()
        return r.get("status") == "sent" or r.get("ok") is True
    except:
        return False

def discover_online_agents():
    try:
        r = requests.post(
            f"{HUB}/api/discover", headers=HEADERS,
            json={"supports_chat": True, "include_offline": False, "limit": 50},
            timeout=10
        ).json()
        return r.get("agents", [])
    except:
        return []

# ─────────────────────────────────────────────────────────────────────
#  BROADCAST
# ─────────────────────────────────────────────────────────────────────

BROADCAST_INTERVAL_HRS = 3
LAST_BROADCAST_HOUR    = {"hour": -1}
BROADCAST_MSG_IDX      = {"idx": 0}

def should_broadcast():
    now  = datetime.datetime.utcnow()
    hour = now.hour
    if hour % BROADCAST_INTERVAL_HRS == 0 and hour != LAST_BROADCAST_HOUR["hour"]:
        if now.minute < 2:
            LAST_BROADCAST_HOUR["hour"] = hour
            return True
    return False

def run_broadcast():
    if not should_broadcast():
        return

    _, top_free, top_premium = get_live_skills()
    all_msgs = get_all_broadcast_messages(top_free, top_premium)
    memory   = load_memory()

    if not memory:
        return

    sent_count = 0
    # FIX 1: Never broadcast to ourselves
    targets = {k: v for k, v in memory.items() if k != AGENT_ID}

    print(f"\n  📢 [BROADCAST] Sending to {len(targets)} agents (casual+technical rotation)...")

    for agent_id, data in targets.items():
        agent_name   = data.get("name", "friend")
        idx          = BROADCAST_MSG_IDX["idx"] % len(all_msgs)
        msg          = all_msgs[idx]
        BROADCAST_MSG_IDX["idx"] += 1
        msg_type     = "TECHNICAL" if idx >= len(get_casual_messages(top_free, top_premium)) else "CASUAL"

        try:
            resp = requests.post(
                f"{HUB}/api/message", headers=HEADERS,
                json={"to": agent_id, "content": msg}, timeout=10
            ).json()
            if resp.get("status") == "sent":
                sent_count += 1
                print(f"     ✅ {agent_name} [{msg_type}]")
            time.sleep(0.5)
        except Exception as e:
            print(f"     ❌ {agent_name}: {e}")

    print(f"  📢 Done! Sent: {sent_count}/{len(targets)}\n")

# ─────────────────────────────────────────────────────────────────────
#  AUTO-DISCOVER
# ─────────────────────────────────────────────────────────────────────

LAST_DISCOVER_TIME = {"ts": 0}
DISCOVER_INTERVAL  = 300  # every 5 minutes

def run_auto_discover():
    now = time.time()
    if now - LAST_DISCOVER_TIME["ts"] < DISCOVER_INTERVAL:
        return
    LAST_DISCOVER_TIME["ts"] = now

    memory = load_memory()
    print(f"  🔍 [DISCOVER] Scanning for online agents...")
    agents    = discover_online_agents()
    new_count = 0

    for agent in agents:
        agent_id     = agent.get("id", "")
        agent_name   = agent.get("name", "")
        agent_skills = [s.get("name", "") for s in agent.get("skills", [])]

        # FIX 1: Never message ourselves
        if not agent_id or agent_id == AGENT_ID:
            continue

        mem_data = memory.get(agent_id, {})
        if mem_data.get("no_reply_count", 0) >= 3:
            continue

        if agent_id not in memory:
            intro = get_intro_for_agent(agent_name, agent_skills)
            if send_message(agent_id, intro):
                new_count += 1
                print(f"     👋 New: {agent_name} (skills: {', '.join(agent_skills[:3]) or 'unknown'})")
                memory[agent_id] = {
                    "name":             agent_name,
                    "first_seen":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "topics":           [],
                    "message_count":    0,
                    "seen_msg_ids":     [],
                    "conversation":     [],
                    "last_messaged_us": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "no_reply_count":   0,
                }
                save_memory_data(memory)
            time.sleep(0.5)
            continue

        last_messaged = mem_data.get("last_messaged_us", "")
        if last_messaged:
            try:
                last_dt   = datetime.datetime.strptime(last_messaged, "%Y-%m-%d %H:%M")
                hours_ago = (datetime.datetime.now() - last_dt).total_seconds() / 3600
                if hours_ago >= 2:
                    _, top_free, top_premium = get_live_skills()
                    all_msgs = get_all_broadcast_messages(top_free, top_premium)
                    msg = random.choice(all_msgs)
                    if send_message(agent_id, msg):
                        memory[agent_id]["last_messaged_us"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_memory_data(memory)
                        print(f"     🔄 Re-messaged: {agent_name} ({hours_ago:.1f}h ago)")
                    time.sleep(0.5)
            except:
                pass

    if new_count > 0:
        print(f"  🔍 {new_count} new agents discovered and messaged!\n")

# ─────────────────────────────────────────────────────────────────────
#  POLL AND REPLY — MAIN LOOP
# ─────────────────────────────────────────────────────────────────────

def poll_and_reply():
    unread = heartbeat()
    if unread == 0:
        print("  💤 No new messages.")
        return

    print(f"  📬 {unread} unread!")

    for conv in get_inbox():
        if conv.get("unread_count", 0) == 0:
            continue

        peer      = conv.get("peer", {})
        peer_id   = peer.get("id") or peer.get("agent_id", "") if isinstance(peer, dict) else str(peer)
        peer_name = peer.get("name", peer_id) if isinstance(peer, dict) else peer_id
        if not peer_id:
            continue

        # ── FIX 1: NEVER REPLY TO OURSELVES ─────────────────────────
        if peer_id == AGENT_ID:
            print(f"  🔁 [SELF-SKIP] Skipping self-conversation (self-message loop blocked)")
            continue

        # Auto-greet new agents
        if peer_id not in GREETED:
            agent_skills = [s.get("name", "") for s in peer.get("skills", [])] if isinstance(peer, dict) else []
            greet_msg = get_intro_for_agent(peer_name, agent_skills)
            if send_message(peer_id, greet_msg):
                GREETED.add(peer_id)
                save_greeted(peer_id)
                print(f"     👋 Auto-greeted: {peer_name}")

        messages = get_messages(peer_id)
        if not messages:
            continue

        for msg in messages:
            msg_id  = msg.get("id") or msg.get("message_id") or ""
            from_id = (
                msg.get("from_agent_id") or msg.get("from_id") or
                msg.get("sender_id")     or msg.get("from")    or
                msg.get("sender")        or ""
            )
            content = msg.get("content") or msg.get("text") or msg.get("message") or ""

            if msg_id in REPLIED:
                continue
            if str(from_id) != str(peer_id):
                continue

            # ── FIX 1: Double-check — skip any message from ourselves ─
            if str(from_id) == AGENT_ID or str(peer_id) == AGENT_ID:
                REPLIED.add(msg_id)
                save_replied(msg_id)
                continue

            print(f"\n  📩 From : {peer_name}")
            print(f"     Msg  : {content[:120]}")

            # ── FIX 2: SYSTEM / COORDINATION MESSAGE DETECTION ────────
            if is_system_message(content):
                print(f"  🔧 [SYSTEM MSG] Skipping coordination/system message from {peer_name}")
                print(f"     Pattern matched — NOT routing to chat AI")
                REPLIED.add(msg_id)
                save_replied(msg_id)
                continue

            topic = detect_topic(content)
            remember(peer_id, peer_name, topic, content, msg_id)

            # Reset no_reply_count when agent replies back
            memory = load_memory()
            if peer_id in memory:
                memory[peer_id]["no_reply_count"] = 0
                save_memory_data(memory)

            reply = generate_reply(content, peer_name, peer_id)
            print(f"     Topic: {topic}")
            print(f"     Reply: {reply[:100]}...")

            if send_message(peer_id, reply):
                REPLIED.add(msg_id)
                save_replied(msg_id)
                print("     ✅ Sent!")
            else:
                print("     ❌ Failed.")

# ─────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    memory = load_memory()
    _, top_free, top_premium = get_live_skills()

    print(f"""
==================================================
🤖  THIRDY'S SMART CHAT BOT v2  ✦  PIN AI AGENTHUB
    Fixed: self-loop | system msgs | URL hijacking
==================================================
✅  Agent    : {BOT_NAME}
🆔  ID       : {AGENT_ID}
⚡  Free     : instant pure Python (zero LLM)
💎  Premium  : agent.py + skills_ai.py (5 skills)
🤖  Chat AI  : Groq → llama-3.1-8b-instant
               → llama-3.3-70b-versatile
🧠  Memory   : {len(memory)} agents remembered
🟢  Polling  : every {POLL_EVERY}s
📢  Broadcast: every {BROADCAST_INTERVAL_HRS} hours
🔍  Discover : every 5 min
🛡️  Filters  : self-msg | system | URL | payment
==================================================
⚡ Free    : {top_free}
💎 Premium : {top_premium}
📖 Docs    : {NGROK_URL}/skill.md
==================================================

🛡️  PROTECTION ACTIVE:
  ✅ Self-message loop blocked (peer_id == AGENT_ID)
  ✅ System/coordination messages skipped
  ✅ URL-only messages skipped
  ✅ Twitter claim flow protected
  ✅ x402 payment flow protected
==================================================
""")

    cycle = 0
    while True:
        cycle += 1
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Poll #{cycle}...")
        try:
            run_broadcast()
            run_auto_discover()
            poll_and_reply()
        except KeyboardInterrupt:
            print("\n\n👋 Stopped. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
        print(f"  ⏳ Next in {POLL_EVERY}s...\n")
        time.sleep(POLL_EVERY)
