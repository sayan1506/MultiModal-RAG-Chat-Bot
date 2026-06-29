"""History router — returns past conversation turns from Supabase."""
from __future__ import annotations

from fastapi import APIRouter

from app.generation.history import get_history

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_conversation_history(session_id: str | None = None) -> dict:
    """
    Return past conversation turns, newest first.

    Query parameters:
        session_id (optional): Filter to a specific session.
                               Omit to return the 50 most recent turns globally.

    Response shape:
        {
          "messages": [
            {
              "id":           "uuid",
              "session_id":   "string",
              "user_message": "string",
              "ai_response":  "string",
              "citations":    { "pages": [...], "nodes": [...] },
              "created_at":   "ISO timestamp"
            },
            ...
          ]
        }
    """
    messages = await get_history(session_id=session_id)
    return {"messages": messages}
