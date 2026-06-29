"""Generation pipeline — MegaRAG paper Section 3.3 two-stage answer generation.

Stage 1 (parallel):
  - KG answer:     answer_from_kg(query, subgraph)     → kg_answer
  - Visual answer: answer_from_images(query, images)   → visual_answer

Stage 2 (fusion):
  - fuse_answers(kg_answer, visual_answer)              → final_answer

This replaces the old single-pass build_prompt → generate_answer path.
"""
from __future__ import annotations

import asyncio

from app.retrieval.query_analyzer import analyze_query
from app.retrieval.pinecone_retriever import PineconeRetriever
from app.retrieval.neo4j_retriever import Neo4jRetriever
from app.retrieval.image_fetcher import ImageFetcher
from app.retrieval.reranker import rerank
from app.generation.kg_answerer import answer_from_kg
from app.generation.visual_answerer import answer_from_images
from app.generation.answer_generator import fuse_answers
from app.generation.citation_formatter import format_citations


async def run_generation_pipeline(
    query: str,
    file_id: str | None = None,
) -> dict:
    """
    Run the full MegaRAG two-stage generation pipeline.

    Args:
        query:   The user's question.
        file_id: Optional file ID to restrict retrieval to a specific document.

    Returns:
        Dict with "answer" (str) and "citations" (list).
    """

    # ── Step 1: Query Analysis ────────────────────────────────────────────
    print("[pipeline] Analyzing query...")
    analysis = await analyze_query(query)
    low_kw = analysis.get("low_level_keywords", [])
    high_kw = analysis.get("high_level_keywords", [])
    print(f"[pipeline] Low-level: {low_kw} | High-level: {high_kw}")

    # ── Step 2: Parallel Retrieval ────────────────────────────────────────
    print("[pipeline] Retrieving from Pinecone and Neo4j...")
    pinecone = PineconeRetriever()
    neo4j = Neo4jRetriever()
    fetcher = ImageFetcher()

    pinecone_results, neo4j_results = await asyncio.gather(
        asyncio.get_event_loop().run_in_executor(
            None, lambda: pinecone.retrieve(query_text=query, top_k=5)
        ),
        neo4j.retrieve(
            low_level_keywords=low_kw,
            high_level_keywords=high_kw,
        ),
    )

    # Fetch page images for visual answering
    page_numbers = [
        r.get("page") for r in pinecone_results if r.get("page")
    ]
    page_images = []
    if page_numbers and file_id:
        page_images = fetcher.fetch_pages(
            file_id=file_id,
            page_numbers=page_numbers,
        )

    # Re-rank merged results
    ranked_results = rerank(pinecone_results, neo4j_results, top_k=5)

    # ── Step 3: Stage 1 — Parallel answer generation ─────────────────────
    print("[pipeline] Stage 1: generating KG answer and visual answer in parallel...")
    kg_answer, visual_answer = await asyncio.gather(
        answer_from_kg(query, neo4j_results),
        answer_from_images(query, page_images),
    )
    print(f"[pipeline] KG answer: {len(kg_answer)} chars | Visual answer: {len(visual_answer)} chars")

    # ── Step 4: Stage 2 — Fusion ──────────────────────────────────────────
    print("[pipeline] Stage 2: fusing answers...")
    final_answer = await fuse_answers(query, kg_answer, visual_answer)

    # ── Step 5: Format citations ──────────────────────────────────────────
    citations = format_citations(ranked_results)

    return {
        "answer": final_answer,
        "citations": citations,
        "kg_answer": kg_answer,       # kept for debugging
        "visual_answer": visual_answer, # kept for debugging
    }
