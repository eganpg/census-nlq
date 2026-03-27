"""
Census NLQ — Configuration
============================
Set your API keys here, or export them as environment variables.

Quick start (no keys needed):
    python cli.py --mock

With a real LLM:
    export LLM_PROVIDER=anthropic
    export LLM_API_KEY=sk-ant-...
    python cli.py

With the Census API key (optional — works without it, just rate-limited):
    export CENSUS_API_KEY=your_key_here
    Get a free key at: https://api.census.gov/data/key_signup.html
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ──────────────────────────────────────────────────────────────
# Set to "anthropic" or "openai"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")

# Your API key for the chosen provider
# Falls back to OPENAI_API_KEY when using the openai provider
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

# Model to use
LLM_MODELS = {
    "anthropic": os.environ.get("LLM_MODEL", "claude-opus-4-6"),
    "openai":    os.environ.get("LLM_MODEL", "gpt-4o"),
}

# ── Census API ────────────────────────────────────────────────────────────────
# Free key: https://api.census.gov/data/key_signup.html
# Works without a key but rate-limited to ~500 requests/day
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
CENSUS_BASE_URL = "https://api.census.gov/data"
CENSUS_YEAR = "2022"
CENSUS_DATASET = "acs/acs5"

# ── Mock mode ─────────────────────────────────────────────────────────────────
# Set to True to run without any API keys — uses realistic sample data
MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"

# ── Guardrails ────────────────────────────────────────────────────────────────
MIN_CONFIDENCE = 0.70
MAX_RESPONSE_TOKENS = 1024
