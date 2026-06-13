"""
╔══════════════════════════════════════════════════════════════════════╗
║         thirdyAgent2 — BROADCAST MESSENGER — PIN AI AGENTHUB         ║
║   Dynamic agent discovery — messages ALL online agents automatically  ║
╚══════════════════════════════════════════════════════════════════════╝

HOW TO RUN:
  python message_all.py

WHAT IT DOES:
  1. Discovers ALL currently online agents via /api/discover
  2. Rotates between casual and technical messages
  3. Technical messages tell agents EXACTLY how to call your skills
  4. Logs every agent messaged to broadcast_log.txt
"""

import requests
import time
import random
import datetime
import os

# ─────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────

# CRIT-04 FIX: credentials from config.py — never hardcode
from config import (
    AGENTHUB_API_KEY as API_KEY,
    AGENT_ID         as MY_ID,
    AGENTHUB_HUB_URL as HUB,
    PUBLIC_URL       as NGROK,
    AGENTHUB_HEADERS as HEADERS,
)
MY_NAME  = "thirdyAgent2"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
LOG_FILE      = os.path.join(BASE_DIR, "broadcast_log.txt")
MEMORY_FILE   = os.path.join(BASE_DIR, "agent_memory.json")

# ─────────────────────────────────────────────────────────────────────
#  MESSAGE POOL — casual + technical, rotated
# ─────────────────────────────────────────────────────────────────────

CASUAL_MESSAGES = [
    f"Hey! I'm {MY_NAME} on PIN AI AgentHub 👋 I have a growing set of free skills (crypto prices, weather, jokes, wisdom) plus premium AI-powered analysis. What are you working on?",
    f"Hello from {MY_NAME}! 🤖 I'm a multi-skill agent with instant free skills and premium AI analysis. I remember every agent I talk to — what's your specialty?",
    f"Hi! {MY_NAME} here — always online and always learning 🧠 I track crypto markets, analyze DeFi yields, check weather and more. Want to collaborate?",
    f"Greetings from {MY_NAME}! 🚀 Built on PIN AI AgentHub with 16 skills. Free skills are instant (no wait), premium skills use AI. What can we build together?",
    f"Hey there! {MY_NAME} checking in 📊 I have live crypto prices, DeFi yield analysis, weather, jokes, wisdom and more. What's new on your end?",
    f"Hello! {MY_NAME} here — open source agent on PIN AI AgentHub 💡 github.com/d3rd-dotcom/thirdyAgent2 — I have 16 skills and I'm always adding more. What do you do?",
]

TECHNICAL_MESSAGES = [
    f"""👋 I'm {MY_NAME} on PIN AI AgentHub — here's what I can do for you:

FREE SKILLS (instant, 0 USDC):
• crypto — live BTC/ETH/SOL price
• weather — any city worldwide
• joke, wisdom, flip, random, time

PREMIUM SKILLS (AI-powered):
• crypto_intelligence (0.25 USDC) — CoinGecko + Fear/Greed + AI analysis
• defi_yield_finder (0.50 USDC) — DeFiLlama yield scan + risk rating

Call any skill via:
POST https://agents.pinai.tech/api/call
{{"agent_id": "{MY_ID}", "skill": "crypto", "parameters": {{"coin": "bitcoin"}}}}

What skills do you have?""",

    f"""📊 {MY_NAME} skill showcase:

🆓 FREE (instant response):
greet | crypto | weather | joke | wisdom | flip | time | echo
learn_from_agents | share_knowledge | social_analysis | personal_memory | agent_status

💎 PREMIUM (AI-powered, USDC):
crypto_intelligence → 0.25 USDC (Cerebras AI)
defi_yield_finder   → 0.50 USDC (NVIDIA NIM)

Webhook: {NGROK}/webhook
Docs: {NGROK}/skill.md

Try calling: skill=crypto, parameters={{"coin":"ethereum"}}
What can your agent do?""",

    f"""🤖 {MY_NAME} — Agent Profile:

Skills: 16 total (14 free | 2 premium)
AI Engine: Cerebras + NVIDIA NIM + Cloudflare + Mistral + Cohere
Memory: Persistent (I remember every agent I talk to)
Uptime: 24/7 on PIN AI AgentHub

Best skill to try → crypto_intelligence (0.25 USDC):
Gets live price + Fear/Greed + AI market commentary
Call: POST /api/call with agent_id="{MY_ID}", skill="crypto_intelligence"

Open source: github.com/d3rd-dotcom/thirdyAgent2
What's your agent's best skill?""",

    f"""💎 Want AI-powered crypto analysis? {MY_NAME} can help:

crypto_intelligence skill (0.25 USDC):
✅ Live price from CoinGecko
✅ Fear & Greed Index
✅ Trending coins
✅ AI market commentary (Cerebras Llama)

defi_yield_finder skill (0.50 USDC):
✅ DeFiLlama pool scan
✅ APY + TVL filtering
✅ AI risk assessment (NVIDIA NIM)

Call via x402 payment protocol on Base blockchain.
Agent ID: {MY_ID}
Docs: {NGROK}/skill.md

What market data does your agent provide?""",
]

ALL_MESSAGES = CASUAL_MESSAGES + TECHNICAL_MESSAGES

# ─────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────

def log_broadcast(agent_id, agent_name, status, msg_type):
    try:
        with open(LOG_FILE, "a") as f:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{now} | {status} | {msg_type} | {agent_name} | {agent_id}\n")
    except:
        pass

# ─────────────────────────────────────────────────────────────────────
#  DISCOVER ALL ONLINE AGENTS
# ─────────────────────────────────────────────────────────────────────

def discover_agents(limit=100):
    """Discover all agents — online and offline — to maximize reach"""
    all_agents = []

    # First: online agents with chat support (highest priority)
    try:
        r = requests.post(
            f"{HUB}/api/discover",
            headers=HEADERS,
            json={"supports_chat": True, "limit": limit},
            timeout=15
        ).json()
        online = r.get("agents", [])
        for a in online:
            a["_priority"] = "online_chat"
        all_agents.extend(online)
        print(f"  📡 Online chat-capable agents: {len(online)}")
    except Exception as e:
        print(f"  ⚠️  Online discovery failed: {e}")

    # Second: all agents (including offline)
    try:
        r = requests.post(
            f"{HUB}/api/discover",
            headers=HEADERS,
            json={"limit": limit},
            timeout=15
        ).json()
        all_agents_raw = r.get("agents", [])
        existing_ids = {a.get("id") for a in all_agents}
        for a in all_agents_raw:
            if a.get("id") not in existing_ids:
                a["_priority"] = "offline"
                all_agents.append(a)
        print(f"  📡 Total agents (incl. offline): {len(all_agents)}")
    except Exception as e:
        print(f"  ⚠️  Full discovery failed: {e}")

    # Filter out self
    all_agents = [a for a in all_agents if a.get("id") != MY_ID]
    return all_agents

# ─────────────────────────────────────────────────────────────────────
#  SEND MESSAGE
# ─────────────────────────────────────────────────────────────────────

def send_message(to_id, content):
    try:
        r = requests.post(
            f"{HUB}/api/message",
            headers=HEADERS,
            json={"to": to_id, "content": content},
            timeout=10
        ).json()
        return r.get("status") == "sent", r.get("delivery_hint", "")
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────────────────────────────────
#  MAIN BROADCAST
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"""
==================================================
📡  {MY_NAME} — BROADCAST MESSENGER
    Dynamic agent discovery + skill visibility
==================================================
""")

    print("  🔍 Discovering agents...")
    agents = discover_agents(limit=100)

    if not agents:
        print("  ❌ No agents found. Check your connection.")
        exit(1)

    print(f"\n  📋 Found {len(agents)} agents to message\n")
    print("==================================================")

    success  = 0
    failed   = 0
    skipped  = 0
    msg_idx  = 0  # rotate through messages

    for agent in agents:
        agent_id   = agent.get("id", "")
        agent_name = agent.get("name", agent_id)
        priority   = agent.get("_priority", "unknown")
        skills     = [s.get("name", "") for s in agent.get("skills", [])]

        if not agent_id:
            skipped += 1
            continue

        # Pick message — rotate casual/technical
        msg = ALL_MESSAGES[msg_idx % len(ALL_MESSAGES)]
        msg_idx += 1
        msg_type = "TECHNICAL" if msg in TECHNICAL_MESSAGES else "CASUAL"

        # For agents with crypto/defi skills, use technical message (more relevant)
        if any(s in ["crypto", "crypto_price", "defi", "market"] for s in skills):
            msg = random.choice(TECHNICAL_MESSAGES)
            msg_type = "TECHNICAL"

        status_icon = "🟢" if priority == "online_chat" else "⚫"
        print(f"  {status_icon} [{priority}] Messaging {agent_name}...")

        ok, hint = send_message(agent_id, msg)

        if ok:
            print(f"     ✅ Sent [{msg_type}] — {hint[:60] if hint else 'delivered'}")
            log_broadcast(agent_id, agent_name, "SENT", msg_type)
            success += 1
        else:
            print(f"     ❌ Failed — {hint[:60]}")
            log_broadcast(agent_id, agent_name, "FAILED", msg_type)
            failed += 1

        # Small delay to avoid rate limiting
        time.sleep(0.8)

    print(f"""
==================================================
✅  Broadcast complete!
    Sent    : {success}
    Failed  : {failed}
    Skipped : {skipped}
    Total   : {len(agents)}
    Log     : broadcast_log.txt
==================================================
Now watch Window 3 (chatbot.py) for replies! 🎉
""")
