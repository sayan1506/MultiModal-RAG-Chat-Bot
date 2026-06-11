"""Chat history — save and retrieve conversation turns via Supabase."""
from __future__ import annotations

import datetime

from supabase import create_client, Client

from app.config import settings

# Module-level lazy client — created once on first use
_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env "
                "before using chat history."
            )
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def save_turn(
    session_id: str,
    user_message: str,
    ai_response: str,
    citations: dict,
) -> None:
    """
    Persist one conversation turn to the chat_history table.

    Args:
        session_id:   Identifies the conversation thread (from WS message).
        user_message: The raw query the user sent.
        ai_response:  The full assembled answer that was streamed back.
        citations:    The citations dict sent to the frontend.

    Note:
        Failures are caught and logged — history failure must never
        crash or block the chat response flow.
    """
    try:
        _get_client().table("chat_history").insert(
            {
                "session_id":   session_id,
                "user_message": user_message,
                "ai_response":  ai_response,
                "citations":    citations,
                "created_at":   datetime.datetime.utcnow().isoformat(),
            }
        ).execute()
    except Exception as e:
        print(f"[history] save_turn failed (non-fatal): {e}")


async def get_history(session_id: str | None = None) -> list[dict]:
    """
    Retrieve past conversation turns, newest first.

    Args:
        session_id: If provided, filter to this session only.
                    If None, return the 50 most recent turns globally.

    Returns:
        List of row dicts from chat_history table, or [] on error.
    """
    try:
        q = (
            _get_client()
            .table("chat_history")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
        )
        if session_id:
            q = q.eq("session_id", session_id)
        result = q.execute()
        return result.data or []
    except Exception as e:
        print(f"[history] get_history failed (non-fatal): {e}")
        return []
