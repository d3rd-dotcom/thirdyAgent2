"""
register_phase4_skills.py — Register Phase 4 Sentiment Skills to AgentHub
==========================================================================
Uses POST /api/agents/:id/skills (the CORRECT endpoint)
NOT pinai-agenthub init (which only recovers, never adds skills)

Run: python register_phase4_skills.py
Expected: 3 skills registered on AgentHub dashboard
"""

import requests
import time

# CRIT-04 FIX: credentials from config.py — never hardcode
from config import (
    AGENTHUB_API_KEY as API_KEY,
    AGENT_ID,
    AGENTHUB_HUB_URL as HUB,
    AGENTHUB_HEADERS as HEADERS,
)

PHASE4_SKILLS = [
    {
        "name": "sentiment_pulse",
        "description": (
            "Real-time social sentiment score for any crypto asset. "
            "Sources: Reddit r/CryptoCurrency, r/Bitcoin, r/investing and Hacker News. "
            "Returns sentiment score from -100 to plus 100, bullish and bearish signal "
            "counts, top community posts, and Fear and Greed context. Free."
        ),
        "price_usdc": "0",
        "payment_required": False,
    },
    {
        "name": "social_alpha",
        "description": (
            "AI-powered social sentiment analysis combining Reddit multi-subreddit data, "
            "Hacker News, DexScreener DEX volume, and Fear and Greed Index. "
            "Cerebras AI interprets narrative, signal alignment with price, divergence "
            "detection, and actionable trading alpha from community data. "
            "Premium skill - 0.50 USDC per call."
        ),
        "price_usdc": "0.50",
        "payment_required": True,
    },
    {
        "name": "viral_signal",
        "description": (
            "Detect viral crypto narratives before they peak. "
            "Scans Reddit new and hot feeds plus Hacker News new stories "
            "and calculates engagement velocity score per post. "
            "Returns viral score ranking, trending themes, and early-warning signals. "
            "Unique signal on AgentHub — no other agent offers this. "
            "Premium skill - 0.25 USDC per call."
        ),
        "price_usdc": "0.25",
        "payment_required": True,
    },
]


def register_skill(skill: dict) -> tuple:
    payload = {
        "name":             skill["name"],
        "description":      skill["description"],
        "parameters":       {},
        "price_usdc":       skill["price_usdc"],
        "payment_required": skill["payment_required"],
    }
    try:
        r = requests.post(
            f"{HUB}/api/agents/{AGENT_ID}/skills",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}


def update_agent_description():
    payload = {
        "description": (
            "Autonomous financial intelligence agent on PIN AI AgentHub. "
            "44 skills: crypto intelligence, DeFi analysis, BUY/SELL/HOLD market signals, "
            "real-time social sentiment, viral narrative detection, news impact analysis, "
            "portfolio assessment, DEX scanning across 80 plus chains, forex, stocks, "
            "academic research, anime, gaming, world knowledge and more. "
            "Multi-LLM AI chain: Cerebras, NVIDIA NIM, Cloudflare, Mistral, Cohere. "
            "Bloomberg Terminal-grade financial analysis plus social alpha at cents per call. "
            "Open source: github.com/d3rd-dotcom/thirdyAgent2"
        ),
        "tags": ["crypto", "analytics", "utility"],
    }
    try:
        r = requests.put(
            f"{HUB}/api/agents/{AGENT_ID}",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    print("=" * 58)
    print("  thirdyAgent2 — PHASE 4 SKILL REGISTRATION")
    print(f"  Agent: {AGENT_ID}")
    print(f"  Skills: {len(PHASE4_SKILLS)}")
    print("=" * 58)

    registered   = []
    already_exists = []
    failed       = []

    for i, skill in enumerate(PHASE4_SKILLS, 1):
        name  = skill["name"]
        price = skill["price_usdc"]
        label = f"PREMIUM ({price} USDC)" if price != "0" else "FREE"

        print(f"\n  [{i}/{len(PHASE4_SKILLS)}] {name} [{label}]")
        print(f"         Registering via POST /api/agents/:id/skills ...")

        status, resp = register_skill(skill)

        if status in (200, 201):
            skill_id = resp.get("skill_id") or resp.get("id") or "?"
            print(f"         ✅ SUCCESS — skill_id: {skill_id}")
            registered.append(name)

        elif status == 409 or "already" in str(resp).lower() or "exists" in str(resp).lower():
            print(f"         ⚠️  Already exists on AgentHub — skipping")
            already_exists.append(name)

        elif status in (504, 502, 0):
            print(f"         ⏱️  Server timeout — retrying in 3s...")
            time.sleep(3)
            status2, resp2 = register_skill(skill)
            if status2 in (200, 201):
                skill_id = resp2.get("skill_id") or resp2.get("id") or "?"
                print(f"         ✅ SUCCESS on retry — skill_id: {skill_id}")
                registered.append(name)
            else:
                print(f"         ❌ FAILED ({status2}): {str(resp2)[:80]}")
                failed.append(name)
        else:
            print(f"         ❌ FAILED ({status}): {str(resp)[:80]}")
            failed.append(name)

        time.sleep(1)

    # Update agent description
    print(f"\n  📝 Updating agent description and tags...")
    status, resp = update_agent_description()
    if status in (200, 201):
        print(f"     ✅ Description updated! Tags: crypto, analytics, utility")
    else:
        print(f"     ⚠️  Description update failed ({status}) — retry manually")

    # Summary
    print(f"\n{'='*58}")
    print(f"  PHASE 4 REGISTRATION SUMMARY")
    print(f"{'='*58}")
    print(f"  ✅ Registered     : {len(registered)} → {registered}")
    print(f"  ⚠️  Already existed: {len(already_exists)} → {already_exists}")
    print(f"  ❌ Failed          : {len(failed)} → {failed}")
    print(f"{'='*58}")

    if failed:
        print(f"\n  ⚠️  {len(failed)} skills failed. Wait 1-2 min and run again.")
        print(f"  Server 504 errors are temporary — retry always works.")
    else:
        print(f"\n  🎉 Phase 4 complete!")
        print(f"  Run: pinai-agenthub skills list")
        print(f"  Then: python message_all.py")

    if registered or already_exists:
        print(f"\n  ✅ NEXT STEPS:")
        print(f"  1. pinai-agenthub skills list  ← verify skills appear")
        print(f"  2. python message_all.py        ← broadcast new skills")
        print(f"  3. Check agenthub.pinai.tech    ← confirm on dashboard")


if __name__ == "__main__":
    main()
