"""
╔══════════════════════════════════════════════════════════════════════╗
║         thirdyAgent2 — PHASE 5 — WATCHDOG AGENT                     ║
║         Auto-restarts crashed Windows — keeps agent online 24/7      ║
╚══════════════════════════════════════════════════════════════════════╝

WHAT IT MONITORS:
  Window 1 — agent.py        (Flask skill server on port 5000)
  Window 3 — chatbot.py      (polling + broadcast loop)
  Window 4 — skill_engine.py (autonomous skill builder)

WHAT IT DOES:
  - Pings localhost:5000/health every 30 seconds
  - If agent.py crashes → auto-restarts it
  - If chatbot.py crashes → auto-restarts it
  - If skill_engine.py is not running → auto-restarts it
  - Logs all events to watchdog_log.txt
  - Sends alert message to AgentHub when it restarts something
  - Shows live status dashboard in terminal

HOW TO RUN:
  python watchdog_agent.py

NOTES:
  - Run AFTER agent.py, chatbot.py, skill_engine.py are already started
  - Uses subprocess to relaunch crashed processes
  - Keeps PIDs in watchdog_state.json for tracking
"""

import os
import sys
import json
import time
import datetime
import subprocess
import requests
import threading
import signal

# ─────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
WATCHDOG_LOG    = os.path.join(BASE_DIR, "watchdog_log.txt")
WATCHDOG_STATE  = os.path.join(BASE_DIR, "watchdog_state.json")

# CRIT-05 FIX: credentials from config.py — never hardcode
from config import (
    AGENTHUB_API_KEY as API_KEY,
    AGENT_ID,
    AGENTHUB_HUB_URL as HUB,
    AGENTHUB_HEADERS as HEADERS,
)

CHECK_INTERVAL  = 30    # seconds between health checks
RESTART_DELAY   = 5     # seconds to wait before restarting
MAX_RESTARTS    = 10    # max restarts per process before giving up
RESTART_WINDOW  = 3600  # seconds — reset restart count after this

PYTHON = sys.executable  # use same Python that runs watchdog

# ─────────────────────────────────────────────────────────────────────
#  PROCESSES TO WATCH
# ─────────────────────────────────────────────────────────────────────

PROCESSES = {
    "agent": {
        "label":   "Window 1 — agent.py (Flask)",
        "cmd":     [PYTHON, os.path.join(BASE_DIR, "agent.py")],
        "health":  "http://localhost:5000/health",
        "process": None,
        "restarts": 0,
        "last_restart": 0,
        "status":  "unknown",
        "pid":     None,
    },
    "chatbot": {
        "label":   "Window 3 — chatbot.py (polling)",
        "cmd":     [PYTHON, os.path.join(BASE_DIR, "chatbot.py")],
        "health":  None,  # no HTTP endpoint — check process alive
        "process": None,
        "restarts": 0,
        "last_restart": 0,
        "status":  "unknown",
        "pid":     None,
    },
    "skill_engine": {
        "label":   "Window 4 — skill_engine.py (AI builder)",
        "cmd":     [PYTHON, os.path.join(BASE_DIR, "skill_engine.py")],
        "health":  None,
        "process": None,
        "restarts": 0,
        "last_restart": 0,
        "status":  "unknown",
        "pid":     None,
    },
}

# ─────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────

def wlog(msg, level="INFO"):
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {msg}"
    print(line)
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# ─────────────────────────────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────────────────────────────

def load_state():
    try:
        with open(WATCHDOG_STATE, "r") as f:
            return json.load(f)
    except:
        return {"total_restarts": 0, "uptime_start": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def save_state():
    state = {
        "total_restarts": sum(p["restarts"] for p in PROCESSES.values()),
        "uptime_start":   _start_time,
        "processes": {
            k: {"restarts": v["restarts"], "status": v["status"], "pid": v["pid"]}
            for k, v in PROCESSES.items()
        }
    }
    try:
        with open(WATCHDOG_STATE, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass

_start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─────────────────────────────────────────────────────────────────────
#  HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────

def check_health(key):
    """Return True if process is healthy, False if it needs restart."""
    proc = PROCESSES[key]

    # If we have a process object, check if it's still alive
    if proc["process"] is not None:
        poll = proc["process"].poll()
        if poll is not None:
            # Process has exited
            PROCESSES[key]["status"] = f"dead (exit {poll})"
            return False

    # For agent.py — also check HTTP health endpoint
    if proc["health"]:
        try:
            r = requests.get(proc["health"], timeout=5)
            if r.status_code == 200:
                PROCESSES[key]["status"] = "healthy ✅"
                return True
            else:
                PROCESSES[key]["status"] = f"HTTP {r.status_code}"
                return False
        except:
            PROCESSES[key]["status"] = "unreachable ❌"
            return False

    # For chatbot/skill_engine — just check process is alive
    if proc["process"] is not None:
        PROCESSES[key]["status"] = "running ✅"
        return True

    PROCESSES[key]["status"] = "not started"
    return False

# ─────────────────────────────────────────────────────────────────────
#  START / RESTART PROCESS
# ─────────────────────────────────────────────────────────────────────

def start_process(key):
    """Launch a process and track it."""
    proc = PROCESSES[key]

    # Check restart limit
    now = time.time()
    if now - proc["last_restart"] > RESTART_WINDOW:
        proc["restarts"] = 0  # reset counter after calm window

    if proc["restarts"] >= MAX_RESTARTS:
        wlog(f"[{key}] MAX RESTARTS ({MAX_RESTARTS}) reached — giving up", "ERROR")
        PROCESSES[key]["status"] = f"GAVE UP after {MAX_RESTARTS} restarts ❌"
        return False

    wlog(f"[{key}] Starting: {' '.join(proc['cmd'])}")

    try:
        # Kill existing if still running
        if proc["process"] and proc["process"].poll() is None:
            try:
                proc["process"].terminate()
                time.sleep(2)
            except:
                pass

        # Start new process
        log_file = open(os.path.join(BASE_DIR, f"{key}_output.log"), "a")
        p = subprocess.Popen(
            proc["cmd"],
            stdout=log_file,
            stderr=log_file,
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

        PROCESSES[key]["process"]       = p
        PROCESSES[key]["pid"]           = p.pid
        PROCESSES[key]["restarts"]     += 1
        PROCESSES[key]["last_restart"]  = now
        PROCESSES[key]["status"]        = "starting..."

        wlog(f"[{key}] Started — PID {p.pid} (restart #{proc['restarts']})")
        send_alert(key, proc["restarts"])
        save_state()
        return True

    except Exception as e:
        wlog(f"[{key}] Start failed: {e}", "ERROR")
        PROCESSES[key]["status"] = f"start failed: {e}"
        return False

# ─────────────────────────────────────────────────────────────────────
#  ALERT — send message to AgentHub when something restarts
# ─────────────────────────────────────────────────────────────────────

def send_alert(key, restart_count):
    """Notify via AgentHub self-message that a process was restarted."""
    label = PROCESSES[key]["label"]
    msg   = (
        f"🔄 [WATCHDOG] Auto-restarted {label} "
        f"(restart #{restart_count}) at {datetime.datetime.now().strftime('%H:%M:%S')}. "
        f"thirdyAgent2 is self-healing and back online."
    )
    # Only alert on first few restarts to avoid spam
    if restart_count > 3:
        return
    try:
        requests.post(
            f"{HUB}/api/message",
            headers=HEADERS,
            json={"to": AGENT_ID, "content": msg},
            timeout=8
        )
    except:
        pass  # alerts are best-effort

# ─────────────────────────────────────────────────────────────────────
#  STATUS DASHBOARD
# ─────────────────────────────────────────────────────────────────────

def print_dashboard(cycle):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n  ┌── WATCHDOG STATUS [{now}] — Check #{cycle} ────────────────")
    for key, proc in PROCESSES.items():
        pid_str = f"PID {proc['pid']}" if proc['pid'] else "no PID"
        print(f"  │  {proc['label'][:35]:35} {proc['status']:20} {pid_str} | restarts: {proc['restarts']}")
    print(f"  └─────────────────────────────────────────────────────────")

# ─────────────────────────────────────────────────────────────────────
#  ADOPT EXISTING PROCESSES
#  If agent.py is already running when watchdog starts, adopt it
# ─────────────────────────────────────────────────────────────────────

def adopt_existing():
    """Check if processes are already running and adopt them."""
    wlog("Checking for already-running processes...")

    # Check agent.py via HTTP
    try:
        r = requests.get("http://localhost:5000/health", timeout=5)
        if r.status_code == 200:
            wlog("agent.py already running on :5000 — adopted")
            PROCESSES["agent"]["status"] = "healthy ✅ (adopted)"
            # We don't have the Process object but health check will handle it
    except:
        wlog("agent.py not responding — will start it")

    # For chatbot and skill_engine, we can't easily detect without PIDs
    # Just note that they may be running in other windows
    wlog("Note: chatbot.py and skill_engine.py may be running in other cmd windows")
    wlog("Watchdog will detect if they crash and restart them")

# ─────────────────────────────────────────────────────────────────────
#  MAIN WATCH LOOP
# ─────────────────────────────────────────────────────────────────────

def watch_loop():
    adopt_existing()
    cycle = 0

    # Give existing processes 30s to stabilize before first check
    wlog(f"Watchdog active — checking every {CHECK_INTERVAL}s")
    time.sleep(10)

    while True:
        cycle += 1

        for key in PROCESSES:
            healthy = check_health(key)

            if not healthy:
                wlog(f"[{key}] UNHEALTHY — restarting in {RESTART_DELAY}s", "WARN")
                time.sleep(RESTART_DELAY)
                start_process(key)
                # Wait for process to come up
                time.sleep(8)

        print_dashboard(cycle)
        save_state()
        time.sleep(CHECK_INTERVAL)

# ─────────────────────────────────────────────────────────────────────
#  GRACEFUL SHUTDOWN
# ─────────────────────────────────────────────────────────────────────

def handle_shutdown(signum, frame):
    wlog("Watchdog shutting down (Ctrl+C)")
    print("\n\n👋 Watchdog stopped. Managed processes continue running.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, handle_shutdown)

# ─────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    state = load_state()

    print(f"""
==================================================
🛡️   thirdyAgent2 — PHASE 5 WATCHDOG
     Auto-restart monitor for all processes
==================================================
  Watching : {len(PROCESSES)} processes
  Interval : every {CHECK_INTERVAL}s
  Max restarts: {MAX_RESTARTS} per process per hour
  Log      : watchdog_log.txt
  State    : watchdog_state.json
==================================================
  Press Ctrl+C to stop watchdog
  (managed processes keep running)
==================================================

  Processes being watched:
""")
    for key, proc in PROCESSES.items():
        print(f"  • {proc['label']}")
    print()

    wlog("Watchdog started")
    watch_loop()
