"""Neo4j CRUD — create/query Page and Entity nodes."""
from __future__ import annotations

from neo4j import AsyncGraphDatabase
from app.config import settings


class Neo4jStore:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self):
        await self.driver.close()

    # ── Write operations ─────────────────────────────────────────────────

    async def create_page_node(
        self,
        file_id: str,
        page_number: int,
        filename: str,
        image_path: str,
    ) -> str:
        """Create or update a Page node. Returns the node ID string."""
        node_id = f"{file_id}_page_{page_number}"
        async with self.driver.session() as s:
            await s.run(
                """
                MERGE (p:Page {id: $id})
                SET p.file_id     = $file_id,
                    p.page_number = $page_number,
                    p.filename    = $filename,
                    p.image_path  = $image_path
                """,
                id=node_id,
                file_id=file_id,
                page_number=page_number,
                filename=filename,
                image_path=image_path,
            )
        return node_id

    async def create_entity_node(self, entity: dict, page_node_id: str):
        """Create or update an Entity node and link it to its Page."""
        async with self.driver.session() as s:
            await s.run(
                """
                MERGE (e:Entity {label: $label, type: $type})
                ON CREATE SET e.id = $id
                WITH e
                MATCH (p:Page {id: $page_id})
                MERGE (p)-[:CONTAINS]->(e)
                """,
                id=entity["id"],
                label=entity["label"],
                type=entity["type"],
                page_id=page_node_id,
            )

    async def create_relationship(
        self, source_label: str, target_label: str, relation: str
    ):
        """Create a relationship between two Entity nodes."""
        # Sanitise relation name — Neo4j relationship types can't have spaces
        rel = relation.upper().replace(" ", "_").replace("-", "_")
        async with self.driver.session() as s:
            await s.run(
                f"""
                MATCH (a:Entity {{label: $src}})
                MATCH (b:Entity {{label: $tgt}})
                MERGE (a)-[:{rel}]->(b)
                """,
                src=source_label,
                tgt=target_label,
            )

    # ── Read operations ──────────────────────────────────────────────────

    async def get_subgraph(
        self, keywords: list[str], depth: int = 2
    ) -> dict:
        """Return subgraph matching keywords. Used by graph router + retriever."""
        if not keywords:
            # Return a sample of the full graph if no keywords
            async with self.driver.session() as s:
                result = await s.run(
                    """
                    MATCH (e:Entity)
                    OPTIONAL MATCH (e)-[r]-(related:Entity)
                    RETURN e, r, related
                    LIMIT 100
                    """
                )
                records = await result.data()
        else:
            async with self.driver.session() as s:
                result = await s.run(
                    """
                    UNWIND $keywords AS kw
                    MATCH (e:Entity)
                    WHERE toLower(e.label) CONTAINS toLower(kw)
                    MATCH path = (e)-[*1..2]-(related)
                    RETURN nodes(path) AS nodes, relationships(path) AS rels
                    LIMIT 50
                    """,
                    keywords=keywords,
                )
                records = await result.data()

        return self._format_subgraph(records)

    async def get_page_nodes(self, file_id: str) -> list[dict]:
        """Get all Page nodes for a given file_id."""
        async with self.driver.session() as s:
            result = await s.run(
                "MATCH (p:Page {file_id: $file_id}) RETURN p ORDER BY p.page_number",
                file_id=file_id,
            )
            records = await result.data()
        return [r["p"] for r in records]

    def _format_subgraph(self, records: list) -> dict:
        nodes, links = {}, []
        for r in records:
            # Handle both path-style and direct node-style results
            raw_nodes = r.get("nodes", [])
            if not raw_nodes:
                for key in ("e", "related"):
                    if r.get(key):
                        raw_nodes.append(r[key])

            for n in raw_nodes:
                if n is None:
                    continue
                nid = str(n.get("id", id(n)))
                nodes[nid] = {
                    "id":    nid,
                    "label": n.get("label", ""),
                    "type":  n.get("type", "Entity"),
                }

            for rel in r.get("rels", []):
                if rel is None:
                    continue
                links.append({
                    "source":   str(rel.start_node.id),
                    "target":   str(rel.end_node.id),
                    "relation": type(rel).__name__,
                })

        return {"nodes": list(nodes.values()), "links": links}