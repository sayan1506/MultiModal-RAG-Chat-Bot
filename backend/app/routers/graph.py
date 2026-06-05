"""Graph router — knowledge-graph visualisation endpoint (stub)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph/{session_id}")
async def get_graph(session_id: str) -> dict[str, list[object]]:
    """Return the knowledge-graph nodes and links for a session.

    Currently returns empty collections.  Future phases will query
    Neo4j and return real graph data.
    """
    return {
        "nodes": [],
        "links": [],
    }
