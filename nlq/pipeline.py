"""
NLQ Pipeline — Orchestration
==============================
Takes a user question, decides which Census tools to call,
executes them, and synthesizes a plain-language answer.

This is the heart of the system. The flow:
  1. Build messages with system prompt + conversation history
  2. First LLM call: LLM reads the question and decides which tool(s) to call
  3. Execute the tool calls against real (or mock) Census data
  4. Second LLM call: LLM synthesizes data into a plain-language answer
  5. Guardrails check: validate confidence and flag anything risky
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .llm_client import chat
from .guardrails import apply_guardrails
from mcp_server.tools import (
    get_population, get_income, compare_states, get_national_ranking
)

# ── System prompt ─────────────────────────────────────────────────────────────
# This tells the LLM what it is, what tools it has, and how to behave.

SYSTEM_PROMPT = """You are a U.S. Census data assistant. You help users explore
demographic and economic data from the U.S. Census Bureau's American Community Survey (ACS).

You have access to the following tools:
- get_population: Get population, median age, and household count for a state, county, or the US
- get_income: Get median household income, poverty rate, and unemployment rate for a geography
- compare_states: Compare multiple states side by side on any metric
- get_national_ranking: Find where a state ranks among all 50 states on a given metric

Rules:
1. Always base answers on data returned by your tools — never make up numbers.
2. Always cite the data source (Census Bureau, ACS 2022) in your answer.
3. If a question is outside Census data (e.g. stock prices, weather), say so clearly.
4. Keep answers concise and in plain English. Format numbers clearly (e.g. 39 million, not 39029342).
5. If comparing multiple geographies, use the compare_states tool rather than calling tools in sequence.
6. Round percentages to one decimal place and dollar amounts to the nearest dollar.
"""

# ── Tool definitions (OpenAI-compatible format — both providers accept this) ──

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_population",
            "description": "Get population statistics (total population, median age, households) for a US state, county, or the whole country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "geography": {
                        "type": "string",
                        "enum": ["state", "county", "us"],
                        "description": "The geographic level to query"
                    },
                    "state": {
                        "type": "string",
                        "description": "State name or 2-letter abbreviation (required for state/county)"
                    },
                    "county": {
                        "type": "string",
                        "description": "County name (required for county geography)"
                    }
                },
                "required": ["geography"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_income",
            "description": "Get economic data (median household income, poverty rate, unemployment rate) for a US state, county, or the whole country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "geography": {
                        "type": "string",
                        "enum": ["state", "county", "us"],
                        "description": "The geographic level to query"
                    },
                    "state": {
                        "type": "string",
                        "description": "State name or 2-letter abbreviation"
                    },
                    "county": {
                        "type": "string",
                        "description": "County name (for county-level queries)"
                    }
                },
                "required": ["geography"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_states",
            "description": "Compare multiple US states side by side on population, income, or poverty metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "states": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of state names or abbreviations to compare"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["population", "income", "poverty", "all"],
                        "description": "Which metric to compare (default: all)"
                    }
                },
                "required": ["states"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_national_ranking",
            "description": "Find where a US state ranks among all 50 states on population, income, or poverty rate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "State name or abbreviation"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["population", "income", "poverty"],
                        "description": "The metric to rank by"
                    }
                },
                "required": ["state", "metric"]
            }
        }
    }
]

# ── Tool dispatcher ───────────────────────────────────────────────────────────

def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    tool_map = {
        "get_population":      get_population,
        "get_income":          get_income,
        "compare_states":      compare_states,
        "get_national_ranking": get_national_ranking,
    }

    if name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = tool_map[name](**arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Main pipeline ─────────────────────────────────────────────────────────────

def answer(question: str, history: list[dict] = None) -> dict:
    """
    Answer a natural language question about Census data.

    Args:
        question: The user's question
        history:  Previous conversation turns (for multi-turn support)

    Returns:
        {
            "answer":     str,    plain-language response
            "sources":    list,   data sources cited
            "confidence": float,  0.0–1.0
            "flagged":    bool,   True if a guardrail triggered
            "tool_calls": list,   for debugging/audit
        }
    """

    # ── Build message history ─────────────────────────────────────────────────
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-8:])  # last 4 turns (user + assistant each)

    messages.append({"role": "user", "content": question})

    # ── First LLM call: decide which tool(s) to use ───────────────────────────
    response = chat(messages, tools=TOOL_DEFINITIONS)

    tool_calls_made = []

    # ── Execute tool calls ────────────────────────────────────────────────────
    if response.get("tool_calls"):
        # Add the assistant's tool-calling message to history
        messages.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": response["tool_calls"],
        })

        # Execute each tool and append results
        for tc in response["tool_calls"]:
            result_str = execute_tool(tc["name"], tc["arguments"])
            tool_calls_made.append({
                "tool": tc["name"],
                "arguments": tc["arguments"],
                "result": json.loads(result_str),
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": tc["name"],
                "content": result_str,
            })

        # ── Second LLM call: synthesize results into plain language ───────────
        final = chat(messages, is_synthesis=True)
        answer_text = final.get("content") or "I wasn't able to generate a response."

    else:
        # LLM answered directly (no tool needed)
        answer_text = response.get("content") or "I wasn't able to answer that question."

    # ── Guardrails ────────────────────────────────────────────────────────────
    guardrail = apply_guardrails(question, answer_text, tool_calls_made)

    if not guardrail.passed:
        answer_text = guardrail.fallback_message

    return {
        "answer":     answer_text,
        "sources":    guardrail.sources,
        "confidence": guardrail.confidence,
        "flagged":    not guardrail.passed,
        "tool_calls": tool_calls_made,
    }
