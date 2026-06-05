"""FastAPI application entry-point.

Registers all routers, enables CORS, and exposes a ``/health``
endpoint for liveness checks.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, graph, history, upload

app = FastAPI(
    title="Multimodal RAG Chatbot",
    description="Phase 1 scaffold — clean backend foundation for a multimodal RAG system.",
    version="0.1.0",
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(history.router)


# ── Health ───────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns ``{"status": "ok"}``."""
    return {"status": "ok"}
