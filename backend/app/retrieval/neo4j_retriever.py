"""Neo4j retriever — dense vector search over entity/relation embeddings.

Replaces keyword substring match with cosine similarity search via
Neo4j vector index. Expands results with 1-hop neighbors.

Requires: entity_embedding_index vector index on Neo4j (see SAYAN_SETUP.md)
"""
from __future__ import annotations

from app.ingestion.gme_embedder import embed_text
from app.knowledge_graph.neo4j_store import Neo4jStore
from app.config import settings


class Neo4jRetriever:
    def __init__(self):
        self.store = Neo4jStore()

    async def retrieve(
        self,
        low_level_keywords: list[str],
        high_level_keywords: list[str] | None = None,
    ) -> dict:
        """
        Dense retrieval from Neo4j knowledge graph.

        Strategy (mirrors MegaRAG paper Section 3.2):
        - Embed low-level keywords → query entity vector index → top-k entities
        - Embed high-level keywords → query entity vector index → top-k entities
        - Combine both sets, expand with 1-hop neighbors

        Args:
            low_level_keywords:  Specific entity keywords from query analysis.
            high_level_keywords: Broad concept keywords from query analysis.

        Returns:
            Subgraph dict {nodes, links} with entities and their relationships.
        """
        all_entity_labels: set[str] = set()

        # Retrieve entities using low-level keywords
        if low_level_keywords:
            ll_query = " ".join(low_level_keywords)
            ll_embedding = embed_text(ll_query)
            ll_results = await self.store.vector_search_entities(
                query_embedding=ll_embedding,
                top_k=settings.top_k_entities,
            )
            for r in ll_results:
                if r.get("label"):
                    all_entity_labels.add(r["label"])

        # Retrieve entities using high-level keywords
        if high_level_keywords:
            hl_query = " ".join(high_level_keywords)
            hl_embedding = embed_text(hl_query)
            hl_results = await self.store.vector_search_entities(
                query_embedding=hl_embedding,
                top_k=settings.top_k_entities,
            )
            for r in hl_results:
                if r.get("label"):
                    all_entity_labels.add(r["label"])

        if not all_entity_labels:
            return {"nodes": [], "links": []}

        # Expand retrieved entities with 1-hop neighbors
        subgraph = await self.store.get_one_hop_neighbors(
            entity_labels=list(all_entity_labels)
        )

        await self.store.close()
        return subgraph
