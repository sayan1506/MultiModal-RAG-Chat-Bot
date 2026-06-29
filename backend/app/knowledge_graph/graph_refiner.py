"""Graph refiner — MegaRAG paper Section 3.1 refinement stage.

For each page:
  1. Retrieve top-120 entities/relations from initial MMKG as subgraph
  2. Feed subgraph + page content + page image back into GPT-4o-mini
  3. Extract NEW cross-modal and cross-page links missed in initial pass
  4. Merge enriched entities/relations back into graph

This replaces the old label-deduplication-only approach and implements
the actual MegaRAG refinement algorithm.
"""
from __future__ import annotations

import json

from app.config import settings
from app.knowledge_graph.neo4j_store import Neo4jStore
from app.knowledge_graph.entity_extractor import extract_entities_with_subgraph
from app.ingestion.gme_embedder import embed_text


class GraphRefiner:
    def __init__(self):
        self.store = Neo4jStore()

    async def refine(
        self,
        file_id: str,
        parsed_pages: list[dict],
        rendered_pages: list[dict],
    ) -> dict:
        """
        Run one round of MegaRAG graph refinement for all pages of a document.

        Args:
            file_id:       The file identifier.
            parsed_pages:  List of {page_number, text, source_file} dicts.
            rendered_pages: List of {page_number, image_bytes, source_file} dicts.

        Returns:
            Dict with refinement statistics.
        """
        new_entity_count = 0
        new_rel_count = 0
        rendered_map = {r["page_number"]: r for r in rendered_pages}

        print(f"[graph_refiner] Starting refinement for {len(parsed_pages)} pages...")

        for parsed in parsed_pages:
            page_num = parsed["page_number"]
            rendered = rendered_map.get(page_num)
            if not rendered:
                continue

            # Step 1: Get top-N subgraph for this page from initial MMKG
            # Use page text keywords to retrieve relevant subgraph context
            page_keywords = _extract_keywords_from_text(parsed["text"])
            subgraph = await self.store.get_subgraph(
                keywords=page_keywords,
                depth=1,  # 1-hop for refinement context
            )

            # Truncate to refinement_subgraph_size (paper default: 120)
            subgraph_context = _format_subgraph_as_string(
                subgraph,
                max_items=settings.refinement_subgraph_size,
            )

            if not subgraph_context:
                # No existing graph data — skip refinement for this page
                continue

            # Step 2 & 3: Feed back into MLLM to find missed relationships
            new_extractions = await extract_entities_with_subgraph(
                text=parsed["text"],
                image_bytes=rendered["image_bytes"],
                subgraph_context=subgraph_context,
            )

            # Step 4: Merge new entities and relationships into graph
            page_node_id = f"{file_id}_page_{page_num}"

            for entity in new_extractions.get("entities", []):
                await self.store.create_entity_node(entity, page_node_id)
                # Store GME embedding for new entity
                embed_input = f"{entity['label']} {entity.get('description', '')}"
                embedding = embed_text(embed_input)
                if embedding:
                    await self.store.set_entity_embedding(entity["label"], embedding)
                new_entity_count += 1

            for rel in new_extractions.get("relationships", []):
                await self.store.create_relationship(
                    rel["source"], rel["target"], rel["relation"]
                )
                new_rel_count += 1

            if new_extractions.get("entities") or new_extractions.get("relationships"):
                print(
                    f"  [refiner] Page {page_num}: "
                    f"+{len(new_extractions.get('entities', []))} entities, "
                    f"+{len(new_extractions.get('relationships', []))} rels"
                )

        await self.store.close()

        print(
            f"[graph_refiner] Refinement complete: "
            f"+{new_entity_count} entities, +{new_rel_count} relationships"
        )
        return {
            "status": "refined",
            "file_id": file_id,
            "new_entity_count": new_entity_count,
            "new_rel_count": new_rel_count,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_keywords_from_text(text: str, max_words: int = 20) -> list[str]:
    """
    Simple keyword extraction from page text for subgraph retrieval.
    Takes the most distinctive words (longer words, not stopwords).
    """
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "this", "that",
        "these", "those", "it", "its", "as", "not", "no", "so", "if",
    }
    words = text.lower().split()
    keywords = [
        w.strip(".,;:!?\"'()[]")
        for w in words
        if len(w) > 4 and w not in stopwords
    ]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique[:max_words]


def _format_subgraph_as_string(subgraph: dict, max_items: int = 120) -> str:
    """
    Format subgraph as a compact string for MLLM context.
    Truncates to max_items combined nodes + links.
    """
    nodes = subgraph.get("nodes", [])
    links = subgraph.get("links", [])

    if not nodes and not links:
        return ""

    lines = []
    for node in nodes[:max_items // 2]:
        lines.append(f'("entity", "{node["label"]}", "{node["type"]}", "{node.get("description", "")}")')

    for link in links[:max_items // 2]:
        lines.append(
            f'("relationship", "{link["source"]}", "{link["target"]}", '
            f'"{link["relation"]}")'
        )

    return "\n".join(lines)
