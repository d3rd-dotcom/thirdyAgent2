"""
telegram/notifier.py  --  thirdyAgent2 push notification system
================================================================
Phase 1: no python-telegram-bot dependency needed.
Uses direct Telegram Bot API via requests (already installed).
Runs as a daemon thread inside chatbot.py -- zero new processes.

Sends:
  - 08:00 Asia/Manila daily digest (rank, interactions, skill count)
  - Instant alert when AgentHub rank changes (polls every 15 min)
  - Instant alert when a new skill deploys (watches evolution_log.txt)
  - 6-hour market summary (calls your own market_signal skill locally)

All messages are 280-char X-ready. Copy-paste to post.

REQUIRED .env vars:
  TELEGRAM_TOKEN=123456789:ABCdef...
  TELEGRAM_CHAT_ID=987654321

HOW TO USE:
  from telegram.notifier import start_notifier
  start_notifier()   # call once at the bottom of chatbot.py main block
"""

import os
import time
import datetime
import json
import re
import threading
import requests

# ── Config ────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVOLUTION_LOG    = os.path.join(BASE_DIR, "evolution_log.txt")
MEMORY_FILE      = os.path.join(BASE_DIR, "agent_memory.json")
SKILL_LOG_FILE   = os.path.join(BASE_DIR, "skill_log.txt")

# Read credentials lazily so they reflect whatever load_dotenv() loaded
# in chatbot.py before start_notifier() was called.
# Module-level reads happen at import time -- before dotenv runs. Don't use them.
def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

AGENT_NAME   = "thirdyAgent2"
TZ_OFFSET    = 8          # Asia/Manila UTC+8
RANK_POLL    = 900        # 15 min in seconds
DIGEST_HOUR  = 8          # 08:00 local time
MARKET_EVERY = 21600      # 6 hours in seconds

# ── Internal state ────────────────────────────────────────────────────
_state = {
    "last_rank":            None,
    "last_evo_mtime":       0.0,
    "last_market_push":     0.0,
    "last_digest_day":      -1,
    "last_known_skill":     "",
}

# ── Core send function ────────────────────────────────────────────────

def send(text: str) -> bool:
    """Send a message to your Telegram chat. Returns True on success."""
    token   = _cfg("TELEGRAM_TOKEN")
    chat_id = _cfg("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("  [TELEGRAM] TOKEN or CHAT_ID not set in .env")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096]},
            timeout=10
        )
        ok = r.status_code == 200
        if not ok:
            print(f"  [TELEGRAM] Send failed {r.status_code}: {r.text[:80]}")
        return ok
    except Exception as e:
        print(f"  [TELEGRAM] Exception: {e}")
        return False

# ── Data helpers ──────────────────────────────────────────────────────

def _get_rank() -> tuple:
    """Return (rank, interactions) from AgentHub. (None, 0) on failure."""
    api_key  = _cfg("AGENTHUB_API_KEY")
    agent_id = _cfg("AGENT_ID", "thirdyAgent2-5dfce3")
    hub      = _cfg("AGENTHUB_HUB_URL", "https://agents.pinai.tech")
    if not api_key:
        return None, 0
    try:
        r = requests.get(
            f"{hub}/api/agents/{agent_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        ).json()
        rank  = r.get("rank") or r.get("leaderboard_rank")
        inter = r.get("interactions") or r.get("interaction_count") or 0
        return rank, inter
    except Exception as e:
        print(f"  [TELEGRAM] Rank fetch failed: {e}")
        return None, 0


def _skill_count() -> int:
    """Get current skill count from running agent or skill_log."""
    try:
        r = requests.get("http://localhost:5000/skills", timeout=3).json()
        return r.get("total", 0)
    except:
        pass
    try:
        with open(SKILL_LOG_FILE, "r") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        return len(set(l.split("|")[2].strip() for l in lines if "|" in l))
    except:
        return 0


def _memory_count() -> int:
    try:
        with open(MEMORY_FILE, "r") as f:
            return len(json.load(f))
    except:
        return 0


def _last_skill_deployed() -> str:
    """Read the last skill name from evolution_log.txt."""
    try:
        with open(EVOLUTION_LOG, "r") as f:
            lines = f.read().splitlines()
        for line in reversed(lines):
            m = re.search(r"deployed '(\w+)'", line)
            if m:
                return m.group(1)
    except:
        pass
    return ""


def _market_signal() -> str:
    """Call your own market_signal skill locally. Returns formatted string."""
    try:
        r = requests.post(
            "http://localhost:5000/webhook",
            json={"skill": "market_signal", "parameters": {"asset": "bitcoin"}},
            timeout=25
        ).json()
        text = r.get("result", "")
        # Extract just signal + price line for Telegram
        lines = [l for l in text.splitlines() if l.strip()]
        summary = " ".join(lines[:4])[:220]
        return summary
    except Exception as e:
        return f"Market signal unavailable: {e}"


def _crypto_price() -> str:
    """Quick BTC price for digest."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin"
            "&vs_currencies=usd&include_24hr_change=true",
            timeout=5
        ).json()
        price  = r["bitcoin"]["usd"]
        change = r["bitcoin"]["usd_24h_change"]
        sign   = "+" if change >= 0 else ""
        return f"BTC ${price:,.0f} ({sign}{change:.1f}%)"
    except:
        return "BTC N/A"

# ── Message formatters (280-char X-ready) ─────────────────────────────

def _msg_rank_up(old_rank, new_rank, interactions) -> str:
    return (
        f"thirdyAgent2 rank up: #{old_rank} -> #{new_rank} "
        f"on @PINaiHub AgentHub\n"
        f"{interactions:,} total interactions\n"
        f"AI skills: crypto_intelligence, market_signal, portfolio_analyzer\n"
        f"github.com/d3rd-dotcom/thirdyAgent2"
    )


def _msg_rank_drop(old_rank, new_rank) -> str:
    return (
        f"thirdyAgent2 dropped: #{old_rank} -> #{new_rank}\n"
        f"Time to broadcast more skills. Back to work."
    )


def _msg_skill_deployed(skill_name, total_skills) -> str:
    return (
        f"New skill deployed: {skill_name}\n"
        f"thirdyAgent2 now has {total_skills} live skills on @PINaiHub\n"
        f"Self-improving agent running Darwin-Godel pattern\n"
        f"github.com/d3rd-dotcom/thirdyAgent2"
    )


def _msg_daily_digest(rank, interactions, skills, agents_known, btc) -> str:
    rank_str = f"#{rank}" if rank else "unranked"
    return (
        f"thirdyAgent2 daily update\n"
        f"Rank {rank_str} | {interactions:,} interactions | {skills} skills\n"
        f"{agents_known} agents in memory\n"
        f"{btc}\n"
        f"@PINaiHub #AI #AgentHub #Web3"
    )


def _msg_market(signal_text: str) -> str:
    clean = signal_text[:200].strip()
    return f"thirdyAgent2 market update\n{clean}\n#crypto #bitcoin #AI"

# ── Alert handlers ────────────────────────────────────────────────────

def _check_rank():
    rank, inter = _get_rank()
    if rank is None:
        return
    old = _state["last_rank"]
    if old is None:
        _state["last_rank"] = rank
        return
    if rank < old:
        send(_msg_rank_up(old, rank, inter))
        print(f"  [TELEGRAM] Rank up alert sent: #{old} -> #{rank}")
    elif rank > old:
        send(_msg_rank_drop(old, rank))
        print(f"  [TELEGRAM] Rank drop alert sent")
    _state["last_rank"] = rank


def _check_skill_deploy():
    try:
        mtime = os.path.getmtime(EVOLUTION_LOG)
    except FileNotFoundError:
        return
    if mtime <= _state["last_evo_mtime"]:
        return
    _state["last_evo_mtime"] = mtime
    skill = _last_skill_deployed()
    if not skill or skill == _state["last_known_skill"]:
        return
    _state["last_known_skill"] = skill
    total = _skill_count()
    send(_msg_skill_deployed(skill, total))
    print(f"  [TELEGRAM] Skill deploy alert: {skill}")


def _send_daily_digest():
    now_local = datetime.datetime.utcnow() + datetime.timedelta(hours=TZ_OFFSET)
    today     = now_local.date().toordinal()
    if now_local.hour != DIGEST_HOUR:
        return
    if _state["last_digest_day"] == today:
        return
    _state["last_digest_day"] = today
    rank, inter = _get_rank()
    skills      = _skill_count()
    agents      = _memory_count()
    btc         = _crypto_price()
    send(_msg_daily_digest(rank, inter, skills, agents, btc))
    print(f"  [TELEGRAM] Daily digest sent")


def _send_market_summary():
    now = time.time()
    if now - _state["last_market_push"] < MARKET_EVERY:
        return
    _state["last_market_push"] = now
    signal = _market_signal()
    send(_msg_market(signal))
    print(f"  [TELEGRAM] Market summary sent")

# ── Main loop ─────────────────────────────────────────────────────────

def _loop():
    print(f"  [TELEGRAM] Notifier started (daily digest at {DIGEST_HOUR}:00 Manila)")
    if not _cfg("TELEGRAM_TOKEN") or not _cfg("TELEGRAM_CHAT_ID"):
        print("  [TELEGRAM] WARNING: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing in .env")
        print("  [TELEGRAM] Loop running but no messages will send until keys are set")

    rank_timer   = 0
    while True:
        try:
            now = time.time()

            # Rank check every 15 min
            if now - rank_timer >= RANK_POLL:
                _check_rank()
                rank_timer = now

            # Skill deploy check on every loop
            _check_skill_deploy()

            # Daily digest
            _send_daily_digest()

            # 6-hour market summary
            _send_market_summary()

        except Exception as e:
            print(f"  [TELEGRAM] Loop error: {e}")

        time.sleep(60)


def start_notifier():
    """Call once from chatbot.py main block to start the notification thread."""
    t = threading.Thread(target=_loop, daemon=True, name="telegram-notifier")
    t.start()
    return t


# ── Quick test (python telegram/notifier.py) ──────────────────────────
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    if "--test" in sys.argv:
        print("Sending test message...")
        ok = send(
            "thirdyAgent2 Telegram notifier is live.\n"
            "You will receive: daily digests, rank alerts, skill deploy alerts.\n"
            "Test successful."
        )
        print("OK" if ok else "FAILED - check TOKEN and CHAT_ID in .env")
    else:
        print("Usage: python telegram/notifier.py --test")
        print("Add TELEGRAM_TOKEN and TELEGRAM_CHAT_ID to .env first.")
