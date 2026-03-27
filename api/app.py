"""
Census NLQ — Web API
======================
FastAPI server that exposes the NLQ pipeline over HTTP
and serves the chat UI.

Run locally:
    MOCK_MODE=true python -m uvicorn api.app:app --reload --port 8000

Run on Railway/Render (auto-detects PORT):
    uvicorn api.app:app --host 0.0.0.0 --port $PORT

Then open: http://localhost:8000
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from nlq.pipeline import answer
from config import MOCK_MODE, LLM_PROVIDER

app = FastAPI(title="Census NLQ API", version="1.0.0")

# Serve static files (the chat UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Schemas ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: float
    flagged: bool
    tool_calls: list
    conversation_id: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the chat UI."""
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mock_mode": MOCK_MODE,
        "provider": LLM_PROVIDER if not MOCK_MODE else "mock",
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Answer a natural language question about Census data."""
    result = answer(request.question)
    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        flagged=result["flagged"],
        tool_calls=result["tool_calls"],
        conversation_id=request.conversation_id,
    )
