"""Re-ranker — merges Pinecone and Neo4j results with unified scoring.

Both sources now use cosine similarity scores (0-1 range) so they are
directly comparable when merged and sorted.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedResult:
    source: str    # "pinecone" | "neo4j"
    score: float   # cosine similarity 0-1
    content: dict  # raw result object


def rerank(
    pinecone_results: list[dict],
    neo4j_results: dict,
    query_embedding: list[float] | None = None,
    top_k: int = 5,
) -> list[RankedResult]:
    """
    Merge and score results from Pinecone and Neo4j retrievers.

    Both sources use cosine similarity scores so they are directly
    comparable. Neo4j node scores come from the vector index query.
    If Neo4j results have no score (fallback path), they are assigned 0.5.

    Args:
        pinecone_results: List of result dicts from PineconeRetriever.
        neo4j_results:    Subgraph dict {nodes, links} from Neo4jRetriever.
        query_embedding:  Optional — not used currently, reserved for future
                          cross-source re-ranking.
        top_k:            Number of top results to return per source.

    Returns:
        Merged list sorted by score descending.
    """
    ranked: list[RankedResult] = []

    # Pinecone — cosine similarity scores already 0-1
    for r in pinecone_results:
        ranked.append(RankedResult(
            source="pinecone",
            score=float(r.get("score", 0.0)),
            content=r,
        ))

    # Neo4j — nodes from vector search have a score field
    # If no score present (e.g., from get_subgraph fallback), use 0.5
    nodes = neo4j_results.get("nodes", [])
    for node in nodes[:top_k]:
        score = float(node.get("score", 0.5))
        ranked.append(RankedResult(
            source="neo4j",
            score=score,
            content=node,
        ))

    # Sort by score descending, return top_k * 2 to give generation more context
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:top_k * 2]
