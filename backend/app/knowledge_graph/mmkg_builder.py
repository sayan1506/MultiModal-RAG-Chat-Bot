"""MMKG Builder — full knowledge graph construction pipeline."""
from __future__ import annotations

import base64

from app.knowledge_graph.entity_extractor import extract_entities
from app.knowledge_graph.neo4j_store import Neo4jStore
from app.knowledge_graph.gcs_store import GCSStore


class MMKGBuilder:
    def __init__(self):
        self.neo4j = Neo4jStore()
        self.gcs   = GCSStore()

    async def build(
        self,
        file_id: str,
        filename: str,
        parsed_pages: list,
        rendered_pages: list,
    ) -> dict:
        """
        Full pipeline per page:
          1. Save PNG to local store
          2. Create Page node in Neo4j
          3. Extract entities via Gemini
          4. Create Entity nodes + relationships in Neo4j
        """
        entity_count = 0
        rel_count = 0

        rendered_map = {r["page_number"]: r for r in rendered_pages}

        for parsed in parsed_pages:
            rendered = rendered_map.get(parsed["page_number"])
            if not rendered:
                print(f"  No render for page {parsed['page_number']}, skipping image steps.")
                continue

            # 1. Store PNG
            image_path = self.gcs.upload_page_png(
                file_id, parsed["page_number"], rendered["image_bytes"]
            )

            # 2. Create Page node
            page_node_id = await self.neo4j.create_page_node(
                file_id=file_id,
                page_number=parsed["page_number"],
                filename=filename,
                image_path=image_path,
            )

            # 3. Extract entities
            extracted = await extract_entities(parsed["text"], rendered["image_bytes"])

            # 4. Create Entity nodes
            for entity in extracted.get("entities", []):
                await self.neo4j.create_entity_node(entity, page_node_id)
                entity_count += 1

            # 5. Create relationships
            for rel in extracted.get("relationships", []):
                await self.neo4j.create_relationship(
                    rel["source"], rel["target"], rel["relation"]
                )
                rel_count += 1

            print(
                f"  Page {parsed['page_number']}: "
                f"{len(extracted.get('entities', []))} entities, "
                f"{len(extracted.get('relationships', []))} rels"
            )

        await self.neo4j.close()
        print(
            f"Graph built for {file_id}: "
            f"{entity_count} entities, {rel_count} relationships"
        )
        return {
            "status":       "graph_built",
            "file_id":      file_id,
            "entity_count": entity_count,
            "rel_count":    rel_count,
        }