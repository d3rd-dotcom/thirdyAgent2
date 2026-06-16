# thirdyAgent2

> Autonomous AI agent .

---

## Status

| Metric | Value |
|--------|-------|
| Interactions | 766K+ |
| Leaderboard Rank | ~#9 |
| Total Skills | 46 (39 free, 7 premium) |
| Uptime | Local + ngrok (Railway deployment in progress) |
| Revenue Target | ~$1,350/month USDC |

---

## What It Does

thirdyAgent2 is a callable AI agent that other agents and users on AgentHub can invoke via REST API. It provides financial intelligence, crypto market data, DeFi analysis, social sentiment scoring, and general utility skills — with free skills returning instant pure-Python responses and premium skills routing through a multi-LLM AI chain.

---

## Skills

### Free (39) — instant, no LLM

**Core:** greet, random, joke, wisdom, flip, time, echo, weather, crypto

**Crypto:** crypto_pulse, btc_network_intel, defi_pulse, dex_scanner, crypto_news_feed

**Science:** space_explorer, math_solver, earth_watch, astronomy_feed, science_facts

**Entertainment:** anime_universe, fun_pack, gamer_hub, quotes_wisdom, daily_briefing

**Knowledge:** tech_news_feed, world_knowledge, paper_search, dev_toolkit, web_extractor

**Business:** global_economy, market_scanner, forex_tracker, startup_intel, business_news

**Sentiment:** sentiment_pulse

**RAG:** knowledge_query, rag_status

**Auto-evolved:** country_facts, isp_lookup, wikipedia_summary, air_quality, random_quiz

### Premium (7) — AI-powered, USDC-priced

| Skill | Price | Description |
|-------|-------|-------------|
| crypto_intelligence | 0.25 USDC | Live price + Fear/Greed + Cerebras AI analysis |
| market_signal | 0.50 USDC | BUY/SELL/HOLD signal from 6 data sources + RSI |
| news_alpha | 0.25 USDC | Crypto news impact analysis via Mistral |
| defi_yield_finder | 0.50 USDC | DeFiLlama yield scan + NVIDIA NIM risk rating |
| portfolio_analyzer | 1.00 USDC | Multi-asset portfolio assessment via NVIDIA NIM |
| social_alpha | 0.50 USDC | Reddit + HN sentiment with AI interpretation |
| viral_signal | 0.25 USDC | Emerging narrative detection across Reddit subs |

---

## AI Provider Chain

Premium skills use automatic fallback across providers:

```
Cerebras → NVIDIA NIM → Gemini 2.0 Flash → GitHub Models (Llama 3.3 70B)
         → Cloudflare Workers AI → Mistral → Cohere
```

If a provider is rate-limited or unavailable, the next one in the chain is used automatically.

---

## Architecture

```
Desktop/
├── agent.py                 Flask :5000 — main skill server + webhook handler
├── chatbot.py               AgentHub polling, auto-reply, broadcast loop (3s)
├── skill_engine.py          Autonomous skill builder — runs every 6 hours
├── watchdog_agent.py        Process monitor — auto-restarts crashed processes
├── config.py                Centralised .env loader for all secrets
├── skills_ai.py             Premium AI skill handlers
├── skills_free_*.py         Free skill packs (crypto, science, entertainment, etc.)
├── skills_free_evolved.py   Auto-generated skills from skill_engine.py
├── rag/                     ChromaDB RAG module
│   ├── chunker.py
│   ├── embedder.py          Cohere embed-english-v3.0
│   ├── store.py             ChromaDB persistent client
│   ├── retriever.py         MMR reranking retriever
│   ├── rag_skill.py         knowledge_query + rag_status skill handlers
│   └── ingestor.py          Document ingestion pipeline
└── sources/                 Knowledge base fetchers
    ├── fetch_whitepapers.py  BTC, ETH, SOL, DeFi, AgentHub context
    └── fetch_defi_docs.py    DeFiLlama protocols, yield pools, Aave V3
```

---

## RAG Knowledge Base

Built with ChromaDB + Cohere `embed-english-v3.0`. Currently indexes 58 chunks from:

- Bitcoin Whitepaper (Satoshi Nakamoto, 2008)
- Ethereum overview (EVM, PoS, L2 scaling)
- Solana overview (PoH, Sealevel, Turbine)
- DeFi fundamentals (AMMs, lending, yield farming, risk)
- AgentHub platform context
- CoinGecko top-20 live market data
- DeFiLlama top protocols, yield pools, and chain TVL
- Aave V3 Ethereum address book

Query with `skill=knowledge_query, {"query": "What is Aave's liquidation threshold?"}`

---

## Autonomous Skill Engine

`skill_engine.py` runs every 6 hours:

1. Audits `skill_log.txt` for never-called or cold skills
2. Scans AgentHub for skill gaps (skills other agents have that thirdyAgent2 lacks)
3. Prompts Cerebras AI to generate a new Python skill handler
4. Runs the code through a safety scanner (blocked patterns, domain whitelist)
5. Executes in a sandboxed namespace with 8-second timeout
6. Deploys to `skills_free_evolved.py` and signals hot-reload to `agent.py`
7. Deprecates skills with 0 calls after 48 hours (minimum 5 preserved)

**Cycle stats:** 92 cycles run → 11 skills deployed → 6 deprecated

---

## Calling a Skill

```bash
curl -X POST https://agents.pinai.tech/api/call \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "thirdyAgent2-5dfce3",
    "skill": "crypto",
    "parameters": {"coin": "bitcoin"}
  }'
```

Full skill documentation: `GET /skill.md` on the agent webhook URL.

---

## Free Data Sources

All free skills use public APIs with no key required:

CoinGecko · DexScreener (300 RPM) · DeFiLlama · Mempool.space ·
Fear & Greed Index · Frankfurter/ECB forex · Yahoo Finance ·
Semantic Scholar (250M papers) · Hacker News · Reddit public JSON ·
REST Countries · World Bank · Open-Meteo · WorldTimeAPI ·
open-notify.org (ISS) · USGS Earthquakes · Newton Math API ·
Jikan/MyAnimeList · JokeAPI · DEV.to · ZenQuotes · ipapi.co

---

## Security Notes

- All secrets stored in `.env`, never hardcoded (SA-01)
- SSRF protection on web_extractor with private IP blocklist (SA-03)
- Thread-safe message deduplication with `threading.Lock` (SA-05)
- HMAC webhook signature verification in progress (SA-04, Batch C)
- `exec()` sandbox isolation in skill_engine.py (SA-02, deferred)

---

## Build Progress

| Phase | Feature | Status |
|-------|---------|--------|
| P0 | Flask agent, AgentHub registration | ✅ Complete |
| P1 | Auto-import packs, skill logging, 60s cache | ✅ Complete |
| P2 | 25 free skills across 5 packs | ✅ Complete |
| P3 | 5 premium AI skills, multi-LLM chain | ✅ Complete |
| P4 | Social sentiment engine (Reddit + HN) | ✅ Complete |
| P5 | Autonomous skill engine | ✅ Complete |
| P8 | Gemini + GitHub Models added to AI chain | ✅ Complete |
| P9 | ChromaDB RAG knowledge base | ✅ Complete |
| P7 | Telegram digest bot | ✅ Complete  |
| P10 | LangChain / OpenAI / MCP adapters | 🔄 In Progress (Batch B) |
| P6 | Railway 24/7 deployment | ⏳ Batch C (after B tests pass) |

---

## Quick Start

```bash
git clone https://github.com/d3rd-dotcom/thirdyAgent2.git
cd thirdyAgent2
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys
```

**Run order (4 windows):**
```
W1: python agent.py          # Flask :5000 — start first
W2: ngrok http 5000          # tunnel (retired after Railway deploy)
W3: python chatbot.py        # polling + broadcast
W4: python skill_engine.py   # autonomous builder
```

**Build RAG index (once):**
```bash
python build_rag.py
python build_rag.py --verify
```

---

## License

MIT — open source at [github.com/d3rd-dotcom/thirdyAgent2](https://github.com/d3rd-dotcom/thirdyAgent2)

## Follow the Journey

- **X (Twitter):** [@thirdy12356](https://x.com/thirdy12356)
- **Medium:** [Full beginner guide](https://medium.com/@amora.leonardoiii/how-to-build-your-first-ai-agent-on-pin-ai-agenthub-windows-step-by-step-guide-for-beginners-cbcff5cdfd58)
- **PIN AI:** [@pinai_io](https://x.com/pinai_io)

---

## License

MIT — feel free to fork, modify and build your own agent!
