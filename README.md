# thirdyAgent2 🤖

> Autonomous financial intelligence agent on [PIN AI AgentHub](https://agents.pinai.tech) —
> built phase-by-phase on a Pentium N3710 laptop with 4 GB RAM and zero cloud budget.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green)](https://flask.palletsprojects.com)
[![Platform](https://img.shields.io/badge/Platform-PIN_AI_AgentHub-purple)](https://agents.pinai.tech)
[![Skills](https://img.shields.io/badge/Skills-46_total-orange)]()
[![Interactions](https://img.shields.io/badge/Interactions-766K%2B-brightgreen)]()

---

## What It Does

thirdyAgent2 runs 24/7 as a callable AI agent with **46 skills** (39 free + 7 premium USDC-paid),
a self-improving skill engine that generates new skills every 6 hours, a ChromaDB RAG knowledge
base, and real-time financial intelligence from 20+ free APIs.

**Leaderboard position**: Top 10 on AgentHub · **766K+ interactions**

---

## Architecture

```
Desktop├── agent.py              Flask :5000 — skill server + webhook handler
├── chatbot.py            Polling + broadcast loop (every 3 s)
├── skill_engine.py       Autonomous skill builder — Darwin Gödel pattern (every 6 h)
├── watchdog_agent.py     Auto-restart monitor for all 3 processes
├── config.py             Centralised .env loader — all secrets in one place
├── skills_*.py           Skill packs (crypto, DeFi, science, entertainment, …)
├── rag/                  ChromaDB RAG — BTC / ETH / SOL / DeFi whitepapers
└── sources/              Live whitepaper + DeFiLlama doc fetchers
```

---

## Skills (46 Total)

### Free Skills — instant, zero LLM (39)

| Pack | Skills |
|------|--------|
| Core | greet · random · joke · wisdom · flip · time · echo · weather · crypto |
| Crypto | crypto_pulse · btc_network_intel · defi_pulse · dex_scanner · crypto_news_feed |
| Science | space_explorer · math_solver · earth_watch · astronomy_feed · science_facts |
| Entertainment | anime_universe · fun_pack · gamer_hub · quotes_wisdom · daily_briefing |
| Knowledge | tech_news_feed · world_knowledge · paper_search · dev_toolkit · web_extractor |
| Business | global_economy · market_scanner · forex_tracker · startup_intel · business_news |
| Sentiment | sentiment_pulse |
| RAG | knowledge_query · rag_status |
| Auto-evolved | gas_tracker · fear_greed_history · btc_halving · github_trending · defi_tvl_rank · isp_lookup · wikipedia_summary · random_quiz · dev_joke |

### Premium Skills — AI-powered, USDC-paid (7)

| Skill | Price | AI Engine |
|-------|-------|-----------|
| crypto_intelligence | 0.25 USDC | Cerebras Llama |
| market_signal | 0.50 USDC | Cerebras + RSI + Reddit |
| news_alpha | 0.25 USDC | Mistral |
| defi_yield_finder | 0.50 USDC | NVIDIA NIM DeepSeek |
| portfolio_analyzer | 1.00 USDC | NVIDIA NIM DeepSeek |
| social_alpha | 0.50 USDC | Cerebras + Reddit/HN |
| viral_signal | 0.25 USDC | Multi-sub Reddit scan |

---

## Multi-LLM Fallback Chain

```
Cerebras  →  NVIDIA NIM  →  Gemini 2.0 Flash  →  GitHub Llama-3.3-70B
          →  Cloudflare  →  Mistral            →  Cohere
```

If the first provider is rate-limited or down, the next kicks in automatically.

---

## Autonomous Skill Engine (Phase 5)

`skill_engine.py` runs every 6 hours and:
1. **Audits** `skill_log.txt` — finds never-called skills
2. **Discovers** skill gaps by scanning other agents on AgentHub
3. **Drafts** new Python skill code via Cerebras AI
4. **Tests** in a sandboxed subprocess (8 s timeout, safety scan)
5. **Deploys** to `skills_free_evolved.py` + signals hot-reload to `agent.py`
6. **Deprecates** skills with 0 calls after 48 h

Result: 18 cycles run → 4 skills successfully deployed to production.

---

## RAG Knowledge Base (Phase 9)

Built with **ChromaDB** + **Cohere embed-english-v3.0**.

Sources indexed:
- Bitcoin Whitepaper (Satoshi Nakamoto)
- Ethereum Overview (EVM, PoS, L2)
- Solana Overview (PoH, Sealevel, Turbine)
- DeFi Fundamentals (AMMs, lending, yield farming)
- AgentHub Platform Context
- CoinGecko Top-20 live market data
- DeFiLlama top protocols + yield pools + chains
- Aave V3 Ethereum address book

Query with: `skill=knowledge_query, {"query": "What is Aave liquidation threshold?"}`

---

## Phase Completion

| Phase | Feature | Status |
|-------|---------|--------|
| P0 | Foundation — Flask agent, AgentHub registration | ✅ Done |
| P1 | Auto-import skill packs, skill logging, 60 s cache | ✅ Done |
| P2 | 25 free skills across 5 packs | ✅ Done |
| P3 | 5 premium AI-powered skills | ✅ Done |
| P4 | Social sentiment engine (Reddit + HN scoring) | ✅ Done |
| P5 | Autonomous skill engine (self-improving) | ✅ Done |
| P8 | Gemini 2.0 + GitHub Models added to AI chain | ✅ Done |
| P9 | RAG ChromaDB knowledge base | ✅ Done |
| P7 | Telegram bot digest | 🔄 In Progress |
| P10 | LangChain + OpenAI + MCP adapters | 🔄 In Progress |
| P6 | Railway 24/7 cloud deployment | 🔄 Next |

---

## Quick Start

```bash
git clone https://github.com/d3rd-dotcom/thirdyAgent2.git
cd thirdyAgent2
pip install -r requirements.txt
cp .env.example .env
# Edit .env — fill in your API keys
```

**Run (4 terminal windows):**
```bash
# W1 — Agent server
python agent.py

# W2 — ngrok tunnel
ngrok http 5000

# W3 — Chatbot (polling + broadcast)
python chatbot.py

# W4 — Skill engine (auto-builds new skills)
python skill_engine.py
```

**Build RAG knowledge base (once):**
```bash
python build_rag.py
```

---

## Calling a Skill (from any agent)

```bash
curl -X POST https://agents.pinai.tech/api/call \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "thirdyAgent2-5dfce3",
    "skill":    "crypto",
    "parameters": {"coin": "bitcoin"}
  }'
```

---

## Free APIs Used (no key required)

CoinGecko · DexScreener · DeFiLlama · Mempool.space · Fear & Greed Index ·
Frankfurter (ECB forex) · Yahoo Finance · Semantic Scholar (250 M papers) ·
Hacker News · Reddit · REST Countries · World Bank · Open-Meteo ·
WorldTimeAPI · NASA / ISS · USGS Earthquakes · Newton Math · Jikan (MAL) ·
JokeAPI · DEV.to · ZenQuotes

---

## Author

**Leonardo Amora III (Thirdy)**
[@thirdy12356](https://x.com/thirdy12356) · Philippines

> Built with no GPU, no cloud, no budget — just free APIs, Python, and persistence.
