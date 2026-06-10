"""Conversation history persistence — stores and retrieves chat turns via Supabase.

Handles conversation turn persistence to Supabase's chat_history table.
Failures in persistence operations never crash the chat flow.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime

from supabase import create_client, Client

from app.config import settings


class ConversationHistory:
    """Manages conversation history persistence via Supabase."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key,
        )
        self.table_name = "chat_history"

    async def save_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a conversation turn to Supabase.

        Args:
            session_id: Unique session identifier
            user_query: The user's question
            assistant_response: The assistant's answer
            metadata: Optional dict with citations, models_used, etc.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            data = {
                "session_id": session_id,
                "user_query": user_query,
                "assistant_response": assistant_response,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            result = self.client.table(self.table_name).insert(data).execute()

            if result.data:
                print(f"Saved conversation turn for session {session_id}")
                return True
            else:
                print(f"Failed to save conversation turn: no data returned")
                return False

        except Exception as e:
            # Never crash the chat flow due to persistence failure
            print(f"Error saving conversation turn: {e}")
            return False

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve conversation history for a session.

        Args:
            session_id: Unique session identifier
            limit: Maximum number of turns to retrieve (most recent first)

        Returns:
            List of conversation turns, ordered by creation time (oldest first)
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )

            if result.data:
                return result.data
            else:
                return []

        except Exception as e:
            print(f"Error retrieving session history: {e}")
            return []

    async def get_all_sessions(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve all conversation sessions (grouped by session_id).

        Args:
            limit: Maximum number of sessions to retrieve

        Returns:
            List of dicts with session_id and last message timestamp
        """
        try:
            # Get distinct sessions with their most recent message
            result = (
                self.client.table(self.table_name)
                .select("session_id, created_at")
                .order("created_at", desc=True)
                .limit(limit * 10)  # Over-fetch to account for multiple turns per session
                .execute()
            )

            if not result.data:
                return []

            # Group by session_id and keep only the most recent entry per session
            sessions_dict = {}
            for row in result.data:
                session_id = row["session_id"]
                if session_id not in sessions_dict:
                    sessions_dict[session_id] = {
                        "session_id": session_id,
                        "last_message_at": row["created_at"],
                    }

            # Convert to list and limit
            sessions = list(sessions_dict.values())
            sessions.sort(key=lambda x: x["last_message_at"], reverse=True)
            return sessions[:limit]

        except Exception as e:
            print(f"Error retrieving sessions: {e}")
            return []
