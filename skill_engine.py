"""
╔══════════════════════════════════════════════════════════════════════╗
║         thirdyAgent2 — PHASE 5 — AUTONOMOUS SKILL ENGINE            ║
║         Darwin Gödel Machine pattern — self-improving agent         ║
╚══════════════════════════════════════════════════════════════════════╝

WHAT IT DOES (every 6 hours):
  1. AUDIT    — reads skill_log.txt, finds never-called or low-call skills
  2. DISCOVER — scans AgentHub for skill gaps (skills others have, we don't)
  3. DRAFT    — calls Cerebras AI to generate Python code for new skill
  4. TEST     — sandbox subprocess test (8s timeout, safety checks)
  5. DEPLOY   — writes to skills_free_evolved.py + sets reload.flag
  6. DEPRECATE— removes auto-generated skills with 0 calls after 48h
  7. LEARN    — updates agent_knowledge.json with network intel

FILES CREATED:
  skills_free_evolved.py — auto-generated skills (loaded by agent.py)
  evolution_log.txt      — full audit trail
  engine_state.json      — cycle tracking
  reload.flag            — signals agent.py to hot-reload skill packs

SAFETY:
  - NEVER touches original skill pack files
  - Blocks: subprocess, os.system, eval, exec, open(), wallet keywords
  - 8-second sandbox timeout per generated skill
  - Only uses free public APIs (whitelist)
  - Min 5 skills preserved even during deprecation

HOW TO RUN:
  python skill_engine.py          ← runs one cycle immediately, then loops
  python skill_engine.py --once   ← runs one cycle and exits
"""

import os
import sys
import json
import time
import datetime
import importlib
import subprocess
import re
import requests
import textwrap
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# ─────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
EVOLVED_FILE    = os.path.join(BASE_DIR, "skills_free_evolved.py")
EVOLUTION_LOG   = os.path.join(BASE_DIR, "evolution_log.txt")
ENGINE_STATE    = os.path.join(BASE_DIR, "engine_state.json")
RELOAD_FLAG     = os.path.join(BASE_DIR, "reload.flag")
SKILL_LOG_FILE  = os.path.join(BASE_DIR, "skill_log.txt")
KNOWLEDGE_FILE  = os.path.join(BASE_DIR, "agent_knowledge.json")

CYCLE_HOURS     = 6          # how often the engine runs
SANDBOX_TIMEOUT = 8          # seconds per skill test
MIN_SKILLS_KEEP = 5          # minimum evolved skills to preserve
DEPRECATE_AFTER = 48         # hours before 0-call evolved skill is dropped

API_KEY   = "pk_live_YOUR_AGENTHUB_API_KEY"
AGENT_ID  = "thirdyAgent2-5dfce3"
HUB       = "https://agents.pinai.tech"
HEADERS   = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

CEREBRAS_KEY = "csk-YOUR_CEREBRAS_KEY"
MISTRAL_KEY  = "YOUR_MISTRAL_KEY"

# ─────────────────────────────────────────────────────────────────────
#  SAFE API WHITELIST — only these domains allowed in generated code
# ─────────────────────────────────────────────────────────────────────

SAFE_APIS = [
    "api.coingecko.com",
    "api.alternative.me",
    "mempool.space",
    "api.dexscreener.com",
    "yields.llama.fi",
    "api.llama.fi",
    "api.frankfurter.app",
    "restcountries.com",
    "api.open-meteo.com",
    "geocoding-api.open-meteo.com",
    "worldtimeapi.org",
    "api.open-notify.org",
    "earthquake.usgs.gov",
    "newton.vercel.app",
    "api.jikan.moe",
    "v2.jokeapi.dev",
    "official-joke-api.appspot.com",
    "hacker-news.firebaseio.com",
    "www.reddit.com",
    "dev.to",
    "zenquotes.io",
    "api.quotable.io",
    "api.adviceslip.com",
    "catfact.ninja",
    "numbersapi.com",
    "uselessfacts.jsph.pl",
    "api.worldbank.org",
    "query1.finance.yahoo.com",
    "api.semanticscholar.org",
    "api.github.com",
    "api.rawg.io",
    "www.freetogame.com",
    "blockchain.info",
    "api.sunrise-sunset.org",
    "bored-api.appbrewery.com",
    "opentdb.com",
    "lldev.thespacedevs.com",
    "air-quality-api.open-meteo.com",
    "ip-api.com",
    "en.wikipedia.org",
    "wttr.in",
    "api.exchangerate-api.com",
    "rate.sx",
    "api.coinpaprika.com",
    "api.binance.com",
]

# ─────────────────────────────────────────────────────────────────────
#  BLOCKED CODE PATTERNS — safety scanner
# ─────────────────────────────────────────────────────────────────────

BLOCKED_PATTERNS = [
    r"\bsubprocess\b",
    r"\bos\.system\b",
    r"\bos\.popen\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"__import__",
    r"\bopen\s*\(",
    r"\bshutil\b",
    r"wallet",
    r"private.?key",
    r"seed.?phrase",
    r"mnemonic",
    r"transfer.*usdc",
    r"send.*eth",
    r"0x[a-fA-F0-9]{40}",   # raw ETH addresses
    r"rm\s+-rf",
    r"DROP\s+TABLE",
    r"socket\.",
    r"import\s+socket",
    r"import\s+subprocess",
    r"import\s+shutil",
    r"import\s+ctypes",
    r"import\s+pickle",
]

# ─────────────────────────────────────────────────────────────────────
#  SKILL IDEAS POOL — what to build next
#  Engine picks from gaps between this list and current skills
# ─────────────────────────────────────────────────────────────────────

SKILL_IDEAS = [
    {
        "name": "gas_tracker",
        "description": "Real-time Ethereum gas prices: slow, standard, fast in Gwei. Source: mempool.space.",
        "api": "mempool.space/api/v1/fees/recommended",
        "params": [],
    },
    {
        "name": "crypto_dominance",
        "description": "BTC and ETH market dominance percentage from CoinGecko global stats.",
        "api": "api.coingecko.com/api/v3/global",
        "params": [],
    },
    {
        "name": "nft_pulse",
        "description": "Top NFT collections by volume from CoinGecko. Free, no key.",
        "api": "api.coingecko.com/api/v3/nfts/list",
        "params": [],
    },
    {
        "name": "exchange_rates",
        "description": "Live fiat exchange rates for PHP, USD, EUR, JPY, SGD from ECB.",
        "api": "api.frankfurter.app/latest",
        "params": ["base", "targets"],
    },
    {
        "name": "country_facts",
        "description": "Quick country facts: population, capital, GDP, flag emoji. Source: restcountries.com.",
        "api": "restcountries.com/v3.1/name/{country}",
        "params": ["country"],
    },
    {
        "name": "moon_phase",
        "description": "Current moon phase and next full moon date, calculated in pure Python.",
        "api": None,
        "params": [],
    },
    {
        "name": "random_quiz",
        "description": "Random trivia quiz question with 4 options and answer. Source: opentdb.com.",
        "api": "opentdb.com/api.php",
        "params": ["difficulty", "category"],
    },
    {
        "name": "isp_lookup",
        "description": "Look up ISP, city, country and timezone for any IP address. Source: ip-api.com.",
        "api": "ip-api.com/json/{ip}",
        "params": ["ip"],
    },
    {
        "name": "dev_joke",
        "description": "Random developer joke from JokeAPI — programming category only.",
        "api": "v2.jokeapi.dev/joke/Programming",
        "params": [],
    },
    {
        "name": "cat_facts",
        "description": "Bundle of 3 random cat facts. Source: catfact.ninja. Great for entertainment.",
        "api": "catfact.ninja/facts",
        "params": ["count"],
    },
    {
        "name": "word_of_day",
        "description": "Random interesting English word with definition and example. Source: uselessfacts + quotable.",
        "api": "uselessfacts.jsph.pl/api/v2/facts/random",
        "params": [],
    },
    {
        "name": "earthquake_alert",
        "description": "Latest significant earthquakes worldwide in the past 24 hours from USGS.",
        "api": "earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson",
        "params": [],
    },
    {
        "name": "iss_tracker",
        "description": "Real-time ISS position with city/country estimation. Source: open-notify.org.",
        "api": "api.open-notify.org/iss-now.json",
        "params": [],
    },
    {
        "name": "air_quality",
        "description": "Air quality index and PM2.5 for any city. Source: open-meteo air quality API.",
        "api": "air-quality-api.open-meteo.com/v1/air-quality",
        "params": ["city"],
    },
    {
        "name": "github_trending",
        "description": "Trending GitHub repositories created in the last 7 days by stars. Source: GitHub API.",
        "api": "api.github.com/search/repositories",
        "params": ["language", "limit"],
    },
    {
        "name": "btc_halving",
        "description": "Bitcoin halving countdown: blocks remaining, estimated date, current epoch.",
        "api": "mempool.space/api/v1/blocks/tip/height",
        "params": [],
    },
    {
        "name": "defi_tvl_rank",
        "description": "Top 10 DeFi protocols by TVL from DeFiLlama. No key required.",
        "api": "api.llama.fi/protocols",
        "params": ["limit"],
    },
    {
        "name": "stablecoin_watch",
        "description": "Top stablecoins by market cap and peg status from CoinGecko.",
        "api": "api.coingecko.com/api/v3/coins/markets",
        "params": [],
    },
    {
        "name": "fear_greed_history",
        "description": "Fear and Greed Index for the last 7 days showing trend direction.",
        "api": "api.alternative.me/fng/?limit=7",
        "params": [],
    },
    {
        "name": "wikipedia_summary",
        "description": "Get a Wikipedia summary for any topic in 3-5 sentences.",
        "api": "en.wikipedia.org/api/rest_v1/page/summary/{topic}",
        "params": ["topic"],
    },
]

# ─────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────

def elog(msg, level="INFO"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {msg}"
    print(line)
    try:
        with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# ─────────────────────────────────────────────────────────────────────
#  STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────

def load_state():
    try:
        with open(ENGINE_STATE, "r") as f:
            return json.load(f)
    except:
        return {
            "cycle": 0,
            "last_run": "",
            "skills_created": [],
            "skills_deprecated": [],
            "total_generated": 0,
            "total_deployed": 0,
            "last_skill_created": "",
        }

def save_state(state):
    try:
        with open(ENGINE_STATE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        elog(f"State save failed: {e}", "WARN")

# ─────────────────────────────────────────────────────────────────────
#  STEP 1: AUDIT — read skill_log.txt, find cold skills
# ─────────────────────────────────────────────────────────────────────

def audit_skill_usage():
    """Read skill_log.txt and return call counts per skill."""
    counts = {}
    if not os.path.exists(SKILL_LOG_FILE):
        elog("skill_log.txt not found — all skills treated as uncalled", "WARN")
        return counts

    try:
        with open(SKILL_LOG_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    skill = parts[2].strip()
                    counts[skill] = counts.get(skill, 0) + 1
    except Exception as e:
        elog(f"Audit failed: {e}", "WARN")

    elog(f"Audit: {len(counts)} skills have call history. Top: {sorted(counts.items(), key=lambda x: -x[1])[:5]}")
    return counts

# ─────────────────────────────────────────────────────────────────────
#  STEP 2: DISCOVER — scan AgentHub for skill gaps
# ─────────────────────────────────────────────────────────────────────

def discover_skill_gaps(our_skills):
    """Find skills other agents have that we don't."""
    gaps = []
    try:
        r = requests.post(
            f"{HUB}/api/discover",
            headers=HEADERS,
            json={"supports_chat": True, "limit": 50},
            timeout=15
        ).json()
        agents = r.get("agents", [])

        their_skills = {}
        for agent in agents:
            agent_id = agent.get("id", "")
            if agent_id == AGENT_ID:
                continue
            for skill in agent.get("skills", []):
                name = skill.get("name", "").lower().strip()
                if name and name not in our_skills:
                    their_skills[name] = their_skills.get(name, 0) + 1

        # Skills that 2+ other agents have but we don't
        gaps = [s for s, count in their_skills.items() if count >= 2]
        elog(f"Discover: {len(gaps)} skill gaps found across {len(agents)} agents: {gaps[:8]}")
    except Exception as e:
        elog(f"Discover failed: {e}", "WARN")

    return gaps

# ─────────────────────────────────────────────────────────────────────
#  STEP 3: PICK NEXT SKILL TO BUILD
# ─────────────────────────────────────────────────────────────────────

def pick_next_skill(our_skills, gaps, state):
    """Choose what skill to build next."""
    already_created = [s["name"] for s in state.get("skills_created", [])]

    # First: build from gap skills that match our idea pool
    gap_set = set(gaps)
    for idea in SKILL_IDEAS:
        if idea["name"] not in our_skills and idea["name"] not in already_created:
            if idea["name"] in gap_set:
                elog(f"Pick: '{idea['name']}' — in gap + idea pool match")
                return idea

    # Second: build any idea not yet created
    import random
    available = [i for i in SKILL_IDEAS
                 if i["name"] not in our_skills
                 and i["name"] not in already_created]
    if available:
        chosen = random.choice(available)
        elog(f"Pick: '{chosen['name']}' — from idea pool (random)")
        return chosen

    # All ideas built — reset and rebuild
    elog("All ideas built — resetting idea rotation", "WARN")
    state["skills_created"] = []
    save_state(state)
    chosen = random.choice(SKILL_IDEAS)
    return chosen

# ─────────────────────────────────────────────────────────────────────
#  STEP 4: DRAFT — call Cerebras AI to generate skill code
# ─────────────────────────────────────────────────────────────────────

def draft_skill_code(skill_idea):
    """Ask Cerebras to generate a working Python skill handler."""
    name = skill_idea["name"]
    desc = skill_idea["description"]
    api  = skill_idea.get("api", "a relevant free public API")
    params = skill_idea.get("params", [])
    params_str = ", ".join(params) if params else "no parameters needed"

    prompt = f"""Write a Python function for an AI agent skill named '{name}'.

DESCRIPTION: {desc}
PRIMARY API: {api}
PARAMETERS: {params_str}

REQUIREMENTS:
1. Function signature: def handle_{name}(params):
2. Use only: import requests, import datetime, import re, import random, import math
3. Accept params dict: params.get("key", "default")
4. Return dict: {{"result": "formatted string", "data": {{dict}}}}
5. Wrap ALL API calls in try/except — never crash
6. Return useful fallback if API fails
7. Format result string with emoji and clear labels
8. Keep it under 60 lines
9. NO subprocess, NO eval, NO exec, NO open(), NO os.system
10. Only call APIs from this list: {', '.join(SAFE_APIS[:10])}

Write ONLY the Python function. No imports at top. No explanation. No markdown. Start with def handle_{name}(params):"""

    providers = [
        {
            "url":     "https://api.cerebras.ai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
            "model":   "llama3.1-8b",
        },
        {
            "url":     "https://api.mistral.ai/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
            "model":   "mistral-small-latest",
        },
    ]

    for provider in providers:
        try:
            payload = {
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": "You are a Python code generator for AI agent skills. Output ONLY valid Python code. No markdown, no explanation."},
                    {"role": "user",   "content": prompt}
                ],
                "max_tokens": 600,
                "temperature": 0.3,
            }
            r = requests.post(provider["url"], headers=provider["headers"], json=payload, timeout=25)
            code = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            # Strip markdown fences if AI added them
            code = re.sub(r"^```python\n?", "", code)
            code = re.sub(r"^```\n?", "", code)
            code = re.sub(r"\n?```$", "", code)
            code = code.strip()

            if code and f"def handle_{name}" in code:
                elog(f"Draft: '{name}' generated via {provider['model']} ({len(code)} chars)")
                return code
        except Exception as e:
            elog(f"Draft provider failed ({provider['model']}): {e}", "WARN")
            continue

    elog(f"Draft: All providers failed for '{name}'", "ERROR")
    return None

# ─────────────────────────────────────────────────────────────────────
#  STEP 5: SAFETY SCAN
# ─────────────────────────────────────────────────────────────────────

def safety_scan(code, name):
    """Check generated code for dangerous patterns."""
    issues = []
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(pattern)

    # Check for unapproved domains
    urls_in_code = re.findall(r'https?://([^/\'")\s]+)', code)
    for url in urls_in_code:
        domain = url.split("/")[0].lower()
        if not any(safe in domain for safe in SAFE_APIS):
            issues.append(f"unapproved domain: {domain}")

    if issues:
        elog(f"Safety FAIL for '{name}': {issues}", "WARN")
        return False, issues

    elog(f"Safety PASS for '{name}'")
    return True, []

# ─────────────────────────────────────────────────────────────────────
#  STEP 6: SANDBOX TEST
# ─────────────────────────────────────────────────────────────────────

def sandbox_test(code, name):
    """Execute generated skill in a restricted namespace with timeout."""
    test_result = {"passed": False, "output": None, "error": None}

    def run_test():
        try:
            # Restricted namespace — no builtins that allow file/system access
            safe_builtins = {
                "print": print, "len": len, "str": str, "int": int,
                "float": float, "list": list, "dict": dict, "bool": bool,
                "range": range, "enumerate": enumerate, "zip": zip,
                "min": min, "max": max, "sum": sum, "round": round,
                "abs": abs, "sorted": sorted, "isinstance": isinstance,
                "type": type, "repr": repr, "hasattr": hasattr,
                "getattr": getattr, "setattr": None, "delattr": None,
            }
            namespace = {
                "__builtins__": safe_builtins,
                "requests": requests,
                "datetime": datetime,
                "re": re,
                "json": json,
                "math": __import__("math"),
                "random": __import__("random"),
            }

            exec(code, namespace)

            handler = namespace.get(f"handle_{name}")
            if not handler:
                test_result["error"] = f"handle_{name} not found in generated code"
                return

            result = handler({})

            if isinstance(result, dict) and "result" in result:
                test_result["passed"] = True
                test_result["output"] = str(result["result"])[:100]
            else:
                test_result["error"] = f"Bad return format: {type(result)}"

        except Exception as e:
            test_result["error"] = f"{type(e).__name__}: {e}"

    thread = threading.Thread(target=run_test, daemon=True)
    thread.start()
    thread.join(timeout=SANDBOX_TIMEOUT)

    if thread.is_alive():
        test_result["error"] = f"Timeout after {SANDBOX_TIMEOUT}s"
        elog(f"Sandbox TIMEOUT for '{name}'", "WARN")
        return False

    if test_result["passed"]:
        elog(f"Sandbox PASS for '{name}': {test_result['output']}")
        return True
    else:
        elog(f"Sandbox FAIL for '{name}': {test_result['error']}", "WARN")
        return False

# ─────────────────────────────────────────────────────────────────────
#  STEP 7: DEPLOY — write to skills_free_evolved.py
# ─────────────────────────────────────────────────────────────────────

def load_evolved_skills():
    """Parse current skills_free_evolved.py and return skill metadata."""
    skills = {}
    if not os.path.exists(EVOLVED_FILE):
        return skills
    try:
        with open(EVOLVED_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # Find all skill metadata blocks
        pattern = r"#\s*SKILL_META:\s*(\{[^}]+\})"
        for match in re.finditer(pattern, content):
            try:
                meta = json.loads(match.group(1))
                skills[meta["name"]] = meta
            except:
                pass
    except Exception as e:
        elog(f"Load evolved: {e}", "WARN")
    return skills

def deploy_skill(name, description, code, state):
    """Add new skill to skills_free_evolved.py and signal reload."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    meta = {
        "name":        name,
        "description": description,
        "created_at":  now_str,
        "calls":       0,
        "auto":        True,
    }

    # Build the skill block
    skill_block = f"""
# ─────────────────────────────────────────────────────────────────────
# SKILL_META: {json.dumps(meta)}
# Auto-generated by skill_engine.py at {now_str}
# ─────────────────────────────────────────────────────────────────────

{code}

"""

    # Read existing file or create header
    if os.path.exists(EVOLVED_FILE):
        with open(EVOLVED_FILE, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = '''"""
skills_free_evolved.py — Auto-generated skills by skill_engine.py
WARNING: Do not edit manually — this file is managed by skill_engine.py
"""
import requests
import datetime
import re
import json
import math
import random

SKILLS_PACK = {}  # populated at bottom of file

'''

    # Remove old SKILLS_PACK assignment
    existing = re.sub(r"\nSKILLS_PACK\s*=\s*\{[^}]*\}", "", existing)

    # Append new skill block
    new_content = existing.rstrip() + "\n" + skill_block

    # Rebuild SKILLS_PACK at the bottom
    # Parse all handler names in the file
    handlers = re.findall(r"def (handle_\w+)\s*\(params\)", new_content)
    pack_entries = "\n".join([f'    "{h[7:]}": {h},' for h in handlers])
    new_content += f"\nSKILLS_PACK = {{\n{pack_entries}\n}}\n"

    # Write file
    with open(EVOLVED_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Touch reload.flag to signal agent.py
    with open(RELOAD_FLAG, "w") as f:
        f.write(now_str)

    elog(f"Deployed '{name}' to skills_free_evolved.py — reload.flag set")

    # Update state
    state.setdefault("skills_created", []).append(meta)
    state["total_deployed"] = state.get("total_deployed", 0) + 1
    state["last_skill_created"] = name
    save_state(state)

    return True

# ─────────────────────────────────────────────────────────────────────
#  STEP 8: REGISTER on AgentHub
# ─────────────────────────────────────────────────────────────────────

def register_evolved_skill(name, description):
    """Register new evolved skill on AgentHub."""
    try:
        r = requests.post(
            f"{HUB}/api/agents/{AGENT_ID}/skills",
            headers=HEADERS,
            json={
                "name":        name,
                "description": description,
                "parameters":  {},
                "price_usdc":  "0",
            },
            timeout=15
        )
        if r.status_code in (200, 201):
            skill_id = r.json().get("skill_id") or r.json().get("id", "?")
            elog(f"Registered '{name}' on AgentHub — ID: {skill_id}")
            return True
        else:
            elog(f"Register failed ({r.status_code}): {r.text[:80]}", "WARN")
            return False
    except Exception as e:
        elog(f"Register exception: {e}", "WARN")
        return False

# ─────────────────────────────────────────────────────────────────────
#  STEP 9: DEPRECATE — remove 0-call evolved skills after 48h
# ─────────────────────────────────────────────────────────────────────

def deprecate_cold_skills(call_counts, state):
    """Remove evolved skills that have never been called after DEPRECATE_AFTER hours."""
    if not os.path.exists(EVOLVED_FILE):
        return

    created = state.get("skills_created", [])
    if len(created) <= MIN_SKILLS_KEEP:
        elog(f"Deprecate: only {len(created)} evolved skills — minimum reached, skipping")
        return

    now = datetime.datetime.now()
    to_deprecate = []

    for skill_meta in created:
        name       = skill_meta["name"]
        created_at = skill_meta.get("created_at", "")
        calls      = call_counts.get(name, 0)

        if calls > 0:
            continue

        try:
            created_dt = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            age_hours  = (now - created_dt).total_seconds() / 3600
            if age_hours >= DEPRECATE_AFTER:
                to_deprecate.append(name)
        except:
            pass

    # Keep at least MIN_SKILLS_KEEP
    safe_to_remove = len(created) - MIN_SKILLS_KEEP
    to_deprecate   = to_deprecate[:max(0, safe_to_remove)]

    if not to_deprecate:
        elog("Deprecate: no cold skills to remove")
        return

    elog(f"Deprecate: removing {len(to_deprecate)} cold skills: {to_deprecate}")

    # Rewrite evolved file without deprecated skills
    try:
        with open(EVOLVED_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        for name in to_deprecate:
            # Remove skill block between SKILL_META lines
            pattern = rf"# ─+\n# SKILL_META:.*?{re.escape(name)}.*?\n.*?# ─+\n\ndef handle_{name}.*?(?=\n# ─|$)"
            content = re.sub(pattern, "", content, flags=re.DOTALL)

        # Rebuild SKILLS_PACK
        content = re.sub(r"\nSKILLS_PACK\s*=\s*\{[^}]*\}", "", content)
        handlers = re.findall(r"def (handle_\w+)\s*\(params\)", content)
        pack_entries = "\n".join([f'    "{h[7:]}": {h},' for h in handlers])
        content += f"\nSKILLS_PACK = {{\n{pack_entries}\n}}\n"

        with open(EVOLVED_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        # Update state
        state["skills_created"] = [s for s in created if s["name"] not in to_deprecate]
        state.setdefault("skills_deprecated", []).extend(to_deprecate)
        save_state(state)

        # Touch reload flag
        with open(RELOAD_FLAG, "w") as f:
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        elog(f"Deprecate: removed {to_deprecate} — reload.flag set")
    except Exception as e:
        elog(f"Deprecate failed: {e}", "ERROR")

# ─────────────────────────────────────────────────────────────────────
#  STEP 10: LEARN — update agent_knowledge.json
# ─────────────────────────────────────────────────────────────────────

def update_knowledge(state):
    """Update agent_knowledge.json with engine stats."""
    try:
        knowledge = {}
        if os.path.exists(KNOWLEDGE_FILE):
            with open(KNOWLEDGE_FILE, "r") as f:
                knowledge = json.load(f)

        knowledge["skill_engine"] = {
            "cycles_run":       state.get("cycle", 0),
            "total_generated":  state.get("total_generated", 0),
            "total_deployed":   state.get("total_deployed", 0),
            "last_run":         state.get("last_run", ""),
            "last_skill":       state.get("last_skill_created", ""),
            "evolved_skills":   [s["name"] for s in state.get("skills_created", [])],
            "deprecated":       state.get("skills_deprecated", []),
        }
        knowledge["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        with open(KNOWLEDGE_FILE, "w") as f:
            json.dump(knowledge, f, indent=2)

        elog("Knowledge updated with engine stats")
    except Exception as e:
        elog(f"Knowledge update failed: {e}", "WARN")

# ─────────────────────────────────────────────────────────────────────
#  GET CURRENT SKILLS from agent.py /skills endpoint
# ─────────────────────────────────────────────────────────────────────

def get_current_skills():
    """Fetch current skill list from running agent."""
    try:
        r = requests.get("http://localhost:5000/skills", timeout=5).json()
        return set(r.get("skills", []))
    except:
        elog("Could not reach localhost:5000/skills — agent may not be running", "WARN")
        return set()

# ─────────────────────────────────────────────────────────────────────
#  MAIN CYCLE
# ─────────────────────────────────────────────────────────────────────

def run_cycle():
    state = load_state()
    state["cycle"] = state.get("cycle", 0) + 1
    state["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    elog(f"═══ CYCLE {state['cycle']} START ═══")

    # ── 1. AUDIT ──────────────────────────────────────────────────────
    call_counts = audit_skill_usage()

    # ── 2. GET CURRENT SKILLS ─────────────────────────────────────────
    our_skills = get_current_skills()
    elog(f"Current skills: {len(our_skills)}")

    # ── 3. DISCOVER GAPS ──────────────────────────────────────────────
    gaps = discover_skill_gaps(our_skills)

    # ── 4. DEPRECATE COLD SKILLS ──────────────────────────────────────
    deprecate_cold_skills(call_counts, state)

    # ── 5. PICK NEXT SKILL ────────────────────────────────────────────
    idea = pick_next_skill(our_skills, gaps, state)
    if not idea:
        elog("No skill ideas available — skipping generation", "WARN")
        save_state(state)
        return

    name        = idea["name"]
    description = idea["description"]
    elog(f"Building: '{name}' — {description}")
    state["total_generated"] = state.get("total_generated", 0) + 1

    # ── 6. DRAFT CODE ─────────────────────────────────────────────────
    code = draft_skill_code(idea)
    if not code:
        elog(f"Draft failed for '{name}' — skipping", "ERROR")
        save_state(state)
        return

    # ── 7. SAFETY SCAN ────────────────────────────────────────────────
    safe, issues = safety_scan(code, name)
    if not safe:
        elog(f"Safety blocked '{name}': {issues}", "ERROR")
        save_state(state)
        return

    # ── 8. SANDBOX TEST ───────────────────────────────────────────────
    passed = sandbox_test(code, name)
    if not passed:
        elog(f"Sandbox blocked '{name}' — not deploying", "WARN")
        save_state(state)
        return

    # ── 9. DEPLOY ─────────────────────────────────────────────────────
    deployed = deploy_skill(name, description, code, state)
    if not deployed:
        elog(f"Deploy failed for '{name}'", "ERROR")
        return

    # ── 10. REGISTER ON AGENTHUB ──────────────────────────────────────
    time.sleep(2)  # brief pause before API call
    register_evolved_skill(name, description)

    # ── 11. LEARN ─────────────────────────────────────────────────────
    update_knowledge(state)
    save_state(state)

    elog(f"═══ CYCLE {state['cycle']} COMPLETE — deployed '{name}' ═══")
    return name

# ─────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    once = "--once" in sys.argv

    print(f"""
==================================================
🧬  thirdyAgent2 — PHASE 5 SKILL ENGINE
    Darwin Gödel Machine — self-improving agent
==================================================
  Agent  : {AGENT_ID}
  Cycle  : every {CYCLE_HOURS} hours
  Safety : {len(BLOCKED_PATTERNS)} blocked patterns
  Ideas  : {len(SKILL_IDEAS)} skill blueprints
  Log    : evolution_log.txt
  State  : engine_state.json
==================================================
  Press Ctrl+C to stop
==================================================
""")

    elog("Skill engine started")

    while True:
        try:
            result = run_cycle()
            if result:
                print(f"\n  ✅ New skill deployed: {result}")
            else:
                print(f"\n  ⚠️  Cycle complete — no new skill this round")
        except KeyboardInterrupt:
            elog("Skill engine stopped by user")
            print("\n\n👋 Skill engine stopped.")
            break
        except Exception as e:
            elog(f"Cycle error: {traceback.format_exc()}", "ERROR")

        if once:
            elog("--once flag set — exiting")
            break

        next_run = datetime.datetime.now() + datetime.timedelta(hours=CYCLE_HOURS)
        print(f"\n  ⏳ Next cycle at {next_run.strftime('%H:%M:%S')} ({CYCLE_HOURS}h)\n")
        time.sleep(CYCLE_HOURS * 3600)
