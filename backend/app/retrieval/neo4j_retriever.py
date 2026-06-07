"""Neo4j retriever — subgraph search by entity label keywords."""
from __future__ import annotations

from app.knowledge_graph.neo4j_store import Neo4jStore


class Neo4jRetriever:
    def __init__(self):
        self.store = Neo4jStore()

    async def retrieve(self, keywords: list[str], depth: int = 2) -> dict:
        """
        Search Neo4j for entities matching keywords.
        Returns subgraph dict with nodes and links.
        """
        if not keywords:
            return {"nodes": [], "links": []}
        return await self.store.get_subgraph(keywords=keywords, depth=depth)