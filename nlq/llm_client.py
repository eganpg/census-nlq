"""
LLM Client — Provider Abstraction
====================================
Wraps both Anthropic and OpenAI APIs into a single interface.
Set LLM_PROVIDER in config.py to switch between them.

Both providers support tool/function calling with slightly different
request/response shapes — this module normalizes them.

Normalized message format (used throughout the pipeline):
    {"role": "user" | "assistant" | "tool", "content": str | list}

Tool call result format returned by chat():
    {
        "content": str | None,        # text response (if no tool calls)
        "tool_calls": [               # tool calls requested by LLM (if any)
            {"id": str, "name": str, "arguments": dict}
        ]
    }
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODELS, MAX_RESPONSE_TOKENS, MOCK_MODE


# ── Mock LLM (for offline testing) ───────────────────────────────────────────

MOCK_RESPONSES = {
    "population": {
        "tool_calls": [{"id": "mock_1", "name": "get_population",
                        "arguments": {"geography": "state", "state": "California"}}]
    },
    "income": {
        "tool_calls": [{"id": "mock_1", "name": "get_income",
                        "arguments": {"geography": "state", "state": "California"}}]
    },
    "compare": {
        "tool_calls": [{"id": "mock_1", "name": "compare_states",
                        "arguments": {"states": ["California", "Texas", "New York"], "metric": "income"}}]
    },
    "rank": {
        "tool_calls": [{"id": "mock_1", "name": "get_national_ranking",
                        "arguments": {"state": "California", "metric": "income"}}]
    },
}

MOCK_SYNTHESIS = (
    "Based on the Census data, {geography} has a {metric} of {value}. "
    "This comes from the U.S. Census Bureau ACS 5-Year Estimates for 2022."
)

def mock_chat(messages, tools=None, is_synthesis=False):
    """Return a plausible mock response for testing without a real LLM."""
    if is_synthesis or tools is None:
        # Second call — just synthesize tool results already in messages
        tool_result = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "tool"), "{}"
        )
        try:
            data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
        except Exception:
            data = {}

        geo = data.get("geography", "this area")
        if "median_household_income" in data:
            answer = (f"{geo} has a median household income of "
                      f"${data['median_household_income']:,}, "
                      f"a poverty rate of {data.get('poverty_rate_pct')}%, "
                      f"and an unemployment rate of {data.get('unemployment_rate_pct')}%. "
                      f"Source: {data.get('source', 'U.S. Census Bureau, 2022')}")
        elif "population" in data:
            answer = (f"{geo} has a population of {data['population']:,}, "
                      f"a median age of {data.get('median_age')}, "
                      f"and {data.get('households', 0):,} households. "
                      f"Source: {data.get('source', 'U.S. Census Bureau, 2022')}")
        elif "comparison" in data:
            top = data["comparison"][0]
            answer = (f"Among the states compared, {top['state']} ranks highest "
                      f"by {data['sorted_by'].replace('_', ' ')}. "
                      f"Source: {data.get('source', 'U.S. Census Bureau, 2022')}")
        else:
            answer = f"Here is what the Census data shows: {json.dumps(data, indent=2)}"

        return {"content": answer, "tool_calls": []}

    # First call — decide which tool to call based on keywords
    last_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    last_msg_lower = last_msg.lower()

    if any(w in last_msg_lower for w in ["compare", "vs", "versus", "between"]):
        return MOCK_RESPONSES["compare"]
    elif any(w in last_msg_lower for w in ["rank", "highest", "lowest", "most", "least"]):
        return MOCK_RESPONSES["rank"]
    elif any(w in last_msg_lower for w in ["income", "earn", "salary", "poverty", "unemployment"]):
        return MOCK_RESPONSES["income"]
    else:
        return MOCK_RESPONSES["population"]


# ── Anthropic client ──────────────────────────────────────────────────────────

def anthropic_chat(messages: list[dict], tools: list[dict] = None,
                   is_synthesis: bool = False) -> dict:
    """Call the Anthropic API."""
    import anthropic

    client = anthropic.Anthropic(api_key=LLM_API_KEY)
    model = LLM_MODELS["anthropic"]

    # Separate system message from conversation
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    convo = [m for m in messages if m["role"] != "system"]

    # Normalize tool result messages for Anthropic format
    normalized = []
    for m in convo:
        if m["role"] == "tool":
            # Anthropic expects tool results as user messages with tool_result content
            normalized.append({
                "role": "user",
                "content": [{"type": "tool_result",
                              "tool_use_id": m.get("tool_call_id", "unknown"),
                              "content": str(m["content"])}]
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            # Reconstruct assistant tool_use message
            normalized.append({
                "role": "assistant",
                "content": [{"type": "tool_use",
                              "id": tc["id"],
                              "name": tc["name"],
                              "input": tc["arguments"]}
                             for tc in m["tool_calls"]]
            })
        else:
            normalized.append(m)

    kwargs = {
        "model": model,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "system": system,
        "messages": normalized,
    }

    if tools and not is_synthesis:
        kwargs["tools"] = [
            {"name": t["function"]["name"],
             "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]}
            for t in tools
        ]

    response = client.messages.create(**kwargs)

    # Parse response
    tool_calls = []
    text_content = ""

    for block in response.content:
        if block.type == "tool_use":
            tool_calls.append({
                "id":        block.id,
                "name":      block.name,
                "arguments": block.input,
            })
        elif block.type == "text":
            text_content = block.text

    return {"content": text_content or None, "tool_calls": tool_calls}


# ── OpenAI client ─────────────────────────────────────────────────────────────

def openai_chat(messages: list[dict], tools: list[dict] = None,
                is_synthesis: bool = False) -> dict:
    """Call the OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=LLM_API_KEY)
    model = LLM_MODELS["openai"]

    # Normalize tool result messages for OpenAI format
    normalized = []
    for m in messages:
        if m["role"] == "tool":
            normalized.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", "unknown"),
                "content": str(m["content"]),
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            normalized.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"],
                                  "arguments": json.dumps(tc["arguments"])}}
                    for tc in m["tool_calls"]
                ],
            })
        else:
            normalized.append(m)

    kwargs = {
        "model": model,
        "max_tokens": MAX_RESPONSE_TOKENS,
        "messages": normalized,
    }

    if tools and not is_synthesis:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message

    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append({
                "id":        tc.id,
                "name":      tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            })

    return {"content": msg.content, "tool_calls": tool_calls}


# ── Unified entrypoint ────────────────────────────────────────────────────────

def chat(messages: list[dict], tools: list[dict] = None,
         is_synthesis: bool = False) -> dict:
    """
    Call the configured LLM provider.
    Returns: {"content": str | None, "tool_calls": list}
    """
    if MOCK_MODE or not LLM_API_KEY:
        return mock_chat(messages, tools, is_synthesis)

    if LLM_PROVIDER == "anthropic":
        return anthropic_chat(messages, tools, is_synthesis)
    elif LLM_PROVIDER == "openai":
        return openai_chat(messages, tools, is_synthesis)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{LLM_PROVIDER}'. Use 'anthropic' or 'openai'.")
