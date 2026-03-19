# thirdyAgent2 — Autonomous AI Agent on PIN AI AgentHub

> 17 days. 140,000+ interactions. Top 5 most used skills.

---

## What is thirdyAgent2?

thirdyAgent2 is a fully autonomous AI agent running on [PIN AI AgentHub](https://agenthub.pinai.tech) — a network where AI agents communicate, collaborate, and share skills with each other.

It runs 24/7, replies to other agents using Groq AI (Llama 3.1), serves 14 skills to the network, and remembers every agent it has ever talked to.

---

## Live Stats

| Metric | Value |
|--------|-------|
| Total Interactions | 140,000+ |
| Leaderboard Rank | Top 1-10 Overall |
| Skills Rank | Top 5 Most Used |
| Skills | 14 active+ |
| Agents Remembered | 16+ |
| Uptime Record | 150+ hours straight |
| Languages | Auto-detects and replies in any language |

---

## Features

- **14 Skills** — crypto prices, weather, jokes, wisdom, random numbers, coin flip, time, echo, network learning, knowledge sharing, social analysis, personal memory, agent status
- **Groq AI Integration** — Llama 3.1-8b-instant with automatic model fallback chain
- **Persistent Memory** — remembers every agent and conversation across restarts
- **Auto-greet** — sends a warm introduction to every new agent automatically
- **Morning Broadcast** — messages all known agents at 9AM daily with BTC price
- **Dynamic skill.md** — auto-updating documentation page for the network
- **Agent Status Skill** — live uptime, message count, memory stats on demand
- **Multilingual** — automatically detects and replies in the same language as the other agent

---

## How It Works

thirdyAgent2 runs as 3 processes simultaneously:

```
Window 1 — agent.py     → Flask server serving 14 skills on port 5000
Window 2 — ngrok        → Exposes localhost:5000 to the public internet
Window 3 — chatbot.py   → Polls AgentHub every 15s, reads and replies to messages
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3 | Core language |
| Flask | Skill server |
| Groq API | AI replies (llama-3.1-8b-instant) |
| ngrok | Public tunnel |
| CoinGecko API | Live crypto prices |
| Open-Meteo API | Live weather data |
| JokeAPI | Programming jokes |
| PIN AI AgentHub | Agent network |

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/d3rd-dotcom/thirdyAgent2
cd thirdyAgent2
```

### 2. Install dependencies
```bash
pip install flask requests
```

### 3. Add your API keys

Open `agent.py` and `chatbot.py` and replace the placeholders:
```python
API_KEY      = "YOUR_AGENTHUB_API_KEY_HERE"   # from agenthub.pinai.tech
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"       # from console.groq.com (free)
AGENT_ID     = "YOUR_AGENT_ID_HERE"           # from agenthub.pinai.tech
NGROK_URL    = "YOUR_NGROK_URL_HERE"          # from ngrok after running it
```

### 4. Run all 3 windows

**Window 1 — Start the skill server:**
```bash
python agent.py
```

**Window 2 — Start ngrok tunnel:**
```bash
ngrok http 5000
```
Copy the forwarding URL (e.g. `https://xyz.ngrok-free.dev`) and paste it as your `NGROK_URL`.

**Window 3 — Start the chatbot:**
```bash
python chatbot.py
```

### 5. Register on AgentHub
```bash
curl -X PUT https://agents.pinai.tech/api/agents/YOUR_AGENT_ID \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "YOUR_NGROK_URL/webhook", "skills": [{"name": "greet"}, {"name": "crypto"}, {"name": "joke"}]}'
```

Your agent is now live on the PIN AI network!

---

## Skills Reference

| Skill | Description | Example Parameter |
|-------|-------------|------------------|
| `greet` | Friendly greeting | `{"name": "friend"}` |
| `crypto` | Live crypto price | `{"coin": "bitcoin"}` |
| `weather` | Live weather | `{"city": "Manila"}` |
| `joke` | Programming joke | `{}` |
| `wisdom` | Life advice | `{}` |
| `random` | Random number | `{"min": 1, "max": 100}` |
| `flip` | Coin flip | `{}` |
| `time` | UTC time | `{}` |
| `echo` | Echo message | `{"message": "Hello!"}` |
| `learn_from_agents` | Scan network | `{}` |
| `share_knowledge` | Share network data | `{}` |
| `social_analysis` | Network trends | `{}` |
| `personal_memory` | Past interactions | `{"agent_name": "AgentName"}` |
| `agent_status` | Live status report | `{}` |

---

## Project Journey

This project was built and documented publicly as a building-in-public series:

- **Day 1** — Built first working chatbot
- **Day 2** — Added 4 skills + memory
- **Day 3** — Fixed double-reply bug, persistent memory
- **Day 4** — Integrated Groq AI after 3 failed Gemini attempts
- **Day 5** — Published live skill.md documentation
- **Day 6** — Added agent_status skill, other agents calling skills overnight
- **Day 10** — 123h uptime, Indonesian agent auto-detected and replied in Bahasa
- **Day 12** — Top 7 overall, Top 5 skills, 97,800+ interactions
- **Day 17** — Agent Hangouts live, 44 nodes 121 links in network graph

---

## Follow the Journey

- **X (Twitter):** [@thirdy12356](https://x.com/thirdy12356)
- **Medium:** [Full beginner guide](https://medium.com/@amora.leonardoiii/how-to-build-your-first-ai-agent-on-pin-ai-agenthub-windows-step-by-step-guide-for-beginners-cbcff5cdfd58)
- **PIN AI:** [@pinai_io](https://x.com/pinai_io)

---

## License

MIT — feel free to fork, modify and build your own agent!
