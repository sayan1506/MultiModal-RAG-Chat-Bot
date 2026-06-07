"""Graph router — returns knowledge graph data for a session."""
from __future__ import annotations

from fastapi import APIRouter
from app.knowledge_graph.neo4j_store import Neo4jStore

router = APIRouter(prefix="/api", tags=["graph"])
store = Neo4jStore()


@router.get("/graph/{session_id}")
async def get_graph(session_id: str) -> dict[str, list]:
    """
    Return the knowledge graph for the given session.
    For now returns the full graph — Phase 4 will filter by session_id.
    """
    graph = await store.get_subgraph(keywords=[], depth=3)
    return graph