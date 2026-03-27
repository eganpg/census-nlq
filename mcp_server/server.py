"""
Census NLQ — MCP Server
========================
Exposes the Census tools over the Model Context Protocol (MCP),
so any MCP-compatible client (Claude Desktop, Claude Code, Cursor, etc.)
can use them directly.

Usage:
    python mcp_server/server.py

Then register in Claude Desktop (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "census": {
          "command": "python",
          "args": ["/path/to/census-nlq/mcp_server/server.py"]
        }
      }
    }

Or in Claude Code settings.json:
    {
      "mcpServers": {
        "census": {
          "command": "python",
          "args": ["/path/to/census-nlq/mcp_server/server.py"]
        }
      }
    }
"""

import sys
import os
import json
import asyncio

# Allow imports from the repo root (config, mcp_server.tools)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from mcp_server.tools import get_population, get_income, compare_states, get_national_ranking

app = Server("census-nlq")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_population",
            description="Get population statistics (total population, median age, households) for a US state, county, or the whole country.",
            inputSchema={
                "type": "object",
                "properties": {
                    "geography": {
                        "type": "string",
                        "enum": ["state", "county", "us"],
                        "description": "The geographic level to query",
                    },
                    "state": {
                        "type": "string",
                        "description": "State name or 2-letter abbreviation (required for state/county)",
                    },
                    "county": {
                        "type": "string",
                        "description": "County name (required for county geography)",
                    },
                },
                "required": ["geography"],
            },
        ),
        types.Tool(
            name="get_income",
            description="Get economic data (median household income, poverty rate, unemployment rate) for a US state, county, or the whole country.",
            inputSchema={
                "type": "object",
                "properties": {
                    "geography": {
                        "type": "string",
                        "enum": ["state", "county", "us"],
                        "description": "The geographic level to query",
                    },
                    "state": {
                        "type": "string",
                        "description": "State name or 2-letter abbreviation",
                    },
                    "county": {
                        "type": "string",
                        "description": "County name (for county-level queries)",
                    },
                },
                "required": ["geography"],
            },
        ),
        types.Tool(
            name="compare_states",
            description="Compare multiple US states side by side on population, income, or poverty metrics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "states": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of state names or abbreviations to compare",
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["population", "income", "poverty", "all"],
                        "description": "Which metric to compare (default: all)",
                    },
                },
                "required": ["states"],
            },
        ),
        types.Tool(
            name="get_national_ranking",
            description="Find where a US state ranks among all 50 states on population, income, or poverty rate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "State name or abbreviation",
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["population", "income", "poverty"],
                        "description": "The metric to rank by",
                    },
                },
                "required": ["state", "metric"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    tool_map = {
        "get_population":       get_population,
        "get_income":           get_income,
        "compare_states":       compare_states,
        "get_national_ranking": get_national_ranking,
    }

    if name not in tool_map:
        raise ValueError(f"Unknown tool: {name}")

    result = tool_map[name](**arguments)
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


if __name__ == "__main__":
    asyncio.run(stdio_server(app))
