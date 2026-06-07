"""
Graph refiner — deduplicates entities across pages.
Runs once after MMKGBuilder.build() finishes for a file.
"""
from __future__ import annotations

from app.knowledge_graph.neo4j_store import Neo4jStore


class GraphRefiner:
    def __init__(self):
        self.store = Neo4jStore()

    async def deduplicate_entities(self) -> int:
        """
        Merge Entity nodes whose labels are identical (case-insensitive).
        Returns number of merges performed.
        """
        async with self.store.driver.session() as s:
            result = await s.run(
                """
                MATCH (e:Entity)
                WITH toLower(e.label) AS key, collect(e) AS nodes
                WHERE size(nodes) > 1
                RETURN key, nodes
                """
            )
            records = await result.data()

        merge_count = 0
        for record in records:
            nodes = record["nodes"]
            # Keep the first, merge rest into it
            keep = nodes[0]
            for duplicate in nodes[1:]:
                async with self.store.driver.session() as s:
                    await s.run(
                        """
                        MATCH (keep:Entity {id: $keep_id})
                        MATCH (dup:Entity {id: $dup_id})
                        // Move all relationships from dup to keep
                        CALL apoc.refactor.mergeNodes([keep, dup], {
                            properties: 'combine',
                            mergeRels: true
                        })
                        YIELD node RETURN node
                        """,
                        keep_id=keep.get("id"),
                        dup_id=duplicate.get("id"),
                    )
                merge_count += 1

        await self.store.close()
        print(f"Graph refiner: merged {merge_count} duplicate entities")
        return merge_count