# Census NLQ

Ask questions about U.S. Census data in plain English.

```
You: What is the population of California?
Assistant: California has a population of approximately 39 million people,
with a median age of 37 and about 13.8 million households.
Source: U.S. Census Bureau, ACS 5-Year Estimates 2022
```

---

## Quick Start (no API keys needed)

```bash
cd census-nlq
pip install fastapi uvicorn

# CLI
python cli.py --mock

# Web UI
MOCK_MODE=true python -m uvicorn api.app:app --port 8000
# then open http://localhost:8000
```

## With a Real LLM

```bash
pip install fastapi uvicorn anthropic   # or openai

# Anthropic (Claude)
export LLM_PROVIDER=anthropic
export LLM_API_KEY=sk-ant-...

# OpenAI (GPT-4o)
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-...

# CLI
python cli.py

# Web UI
python -m uvicorn api.app:app --port 8000
```

## With Real Census Data

```bash
# Free key: https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY=your_key_here
```
Works without a key too, just rate-limited.

---

## Example Questions

- What is the population of California?
- Which state has the highest median income?
- Compare poverty rates in Mississippi, West Virginia, and New Mexico
- How does Colorado rank nationally for household income?
- What is the unemployment rate in Texas?
- Tell me about Utah's demographics
- What's the difference in income between Maryland and Mississippi?

---

## Project Structure

```
census-nlq/
├── config.py                    ← API keys and settings
├── cli.py                       ← Command line interface
├── requirements.txt
├── mcp_server/
│   ├── server.py                ← MCP server (for Claude Desktop, Claude Code, etc.)
│   └── tools/
│       ├── census_client.py     ← Shared Census API utilities
│       ├── population.py        ← Population tool
│       ├── income.py            ← Income/poverty tool
│       └── compare.py           ← Multi-state comparison tool
├── nlq/
│   ├── llm_client.py            ← Anthropic/OpenAI abstraction
│   ├── pipeline.py              ← Main orchestration (question → answer)
│   └── guardrails.py            ← Safety and quality checks
└── api/
    ├── app.py                   ← FastAPI server
    └── static/index.html        ← Chat UI
```

## How It Maps to RISE

| This project | RISE (VA) equivalent |
|---|---|
| Census API | Summit Data Platform |
| `population.py`, `income.py` | `appointments.py`, `benefits.py` |
| `llm_client.py` | Summit LLM API / Mosaic AI |
| `pipeline.py` | Same pattern, larger scope |
| `guardrails.py` | Same, with VA-specific rules |
| `api/app.py` | Same, with VA auth added |
| Mock data | Develops against before VA access |
