"""Re-ranker — merges Pinecone and Neo4j results into a single ranked list."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedResult:
    source: str    # "pinecone" | "neo4j"
    score: float
    content: dict  # raw result object


def rerank(
    pinecone_results: list[dict],
    neo4j_results: dict,
    top_k: int = 5,
) -> list[RankedResult]:
    """
    Merge and score results from both retrievers.
    Strategy:
      - Pinecone results use their cosine similarity score directly (0–1).
      - Neo4j results are scored by position (1.0 decaying by 0.1 per rank).
      - Results are merged, sorted descending, and top_k * 2 returned
        (giving the generation layer more to work with).
    """
    ranked: list[RankedResult] = []

    # Pinecone — cosine scores already in 0–1 range
    for r in pinecone_results:
        ranked.append(RankedResult(
            source="pinecone",
            score=float(r.get("score", 0.0)),
            content=r,
        ))

    # Neo4j — score by rank position
    nodes = neo4j_results.get("nodes", [])
    for i, node in enumerate(nodes[:top_k]):
        score = max(0.0, 1.0 - (i * 0.1))
        ranked.append(RankedResult(
            source="neo4j",
            score=score,
            content=node,
        ))

    # Sort descending, return top_k * 2
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:top_k * 2]