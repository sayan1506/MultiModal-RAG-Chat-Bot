"""History router — chat history retrieval endpoints via Supabase.

Provides endpoints to retrieve conversation history for specific sessions
or list all available sessions.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.generation.history import ConversationHistory

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history/{session_id}")
async def get_session_history(
    session_id: str,
    limit: int = Query(50, description="Maximum number of turns to retrieve"),
) -> dict[str, list[dict]]:
    """Retrieve conversation history for a specific session.

    Args:
        session_id: Unique session identifier
        limit: Maximum number of turns to retrieve (default: 50)

    Returns:
        Dict with 'messages' key containing list of conversation turns
    """
    history_manager = ConversationHistory()
    messages = await history_manager.get_session_history(
        session_id=session_id,
        limit=limit,
    )

    return {
        "messages": messages,
    }


@router.get("/sessions")
async def get_all_sessions(
    limit: int = Query(100, description="Maximum number of sessions to retrieve"),
) -> dict[str, list[dict]]:
    """Retrieve all conversation sessions.

    Args:
        limit: Maximum number of sessions to retrieve (default: 100)

    Returns:
        Dict with 'sessions' key containing list of session summaries
    """
    history_manager = ConversationHistory()
    sessions = await history_manager.get_all_sessions(limit=limit)

    return {
        "sessions": sessions,
    }
