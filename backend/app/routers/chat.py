"""Chat router — WebSocket endpoint with mock token streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Accept a WebSocket connection and stream mock token responses.

    The client sends a JSON message with at least a ``text`` field.
    The server replies with a series of ``{"type": "token", "data": "..."}``
    frames followed by a final ``{"type": "done"}`` frame to signal
    completion.

    In future phases this will be replaced by real Gemini streaming
    with RAG context injection.
    """
    await websocket.accept()

    try:
        while True:
            raw: str = await websocket.receive_text()
            payload: dict[str, str] = json.loads(raw)
            text: str = payload.get("text", "")

            # Build a simple echo-style mock response.
            tokens: list[str] = text.split() if text else ["hello", "world"]

            for token in tokens:
                await websocket.send_json({"type": "token", "data": f"{token} "})
                await asyncio.sleep(0.15)

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError:
        await websocket.close(code=1003, reason="Invalid JSON")
