"""History router — chat history retrieval endpoint (stub)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_history() -> dict[str, list[object]]:
    """Return the conversation history.

    Currently returns an empty list.  Future phases will read from
    Supabase or another persistence layer.
    """
    return {
        "messages": [],
    }
