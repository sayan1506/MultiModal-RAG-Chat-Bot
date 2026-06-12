"""Chat router — full WebSocket RAG pipeline with Ollama Gemma 4 streaming."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.retrieval.query_analyzer import analyze_query
from app.retrieval.pinecone_retriever import PineconeRetriever
from app.retrieval.neo4j_retriever import Neo4jRetriever
from app.retrieval.image_fetcher import ImageFetcher
from app.retrieval.reranker import rerank
from app.generation.kg_answerer import answer_from_kg
from app.generation.visual_answerer import answer_from_images
from app.generation.history import save_turn
from app.ingestion.github_client import call_gpt4o_mini

router = APIRouter(tags=["chat"])

# Singletons — constructed once at startup, reused for every request
_pinecone_ret  = PineconeRetriever()
_neo4j_ret     = Neo4jRetriever()
_image_fetcher = ImageFetcher()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """
    Full RAG pipeline over WebSocket with Gemma 4 token streaming.

    Expected client message (JSON string):
        {
          "type":       "query",
          "text":       "<user question>",
          "session_id": "<any string>"
        }

    Server sends in this order:
        {"type": "token",     "data": "<token>"}   — repeated per streamed token
        {"type": "citations", "data": <dict>}       — once, after streaming ends
        {"type": "done"}                            — signals end of turn
        {"type": "error",     "data": "<message>"}  — only on unhandled error
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.close(code=1003, reason="Invalid JSON")
                return

            if data.get("type") != "query":
                continue

            query:      str = data.get("text", "").strip()
            session_id: str = data.get("session_id", "default")

            if not query:
                await websocket.send_json({"type": "error", "data": "Empty query."})
                continue

            try:
                # ── 1. Query Analysis ────────────────────────────────────────
                analysis = await analyze_query(query)
                keywords: list[str] = (
                    analysis.get("low_level_keywords", [])
                    + analysis.get("high_level_concepts", [])
                )

                # ── 2. Parallel Retrieval ────────────────────────────────────
                pinecone_results, neo4j_results = await asyncio.gather(
                    asyncio.to_thread(_pinecone_ret.retrieve, query, 5),
                    _neo4j_ret.retrieve(keywords),
                )

                # ── 3. Re-rank ───────────────────────────────────────────────
                ranked = rerank(pinecone_results, neo4j_results, top_k=5)

                # ── 4. Fetch images for ALL cited pages ──────────────────────
                # Group Pinecone hits by file_id so every cited file gets
                # its pages fetched — not just the top hit's file.
                pinecone_hits = [r for r in ranked if r.source == "pinecone"]

                # file_id → set of page numbers
                pages_by_file: dict[str, set] = defaultdict(set)
                for r in pinecone_hits:
                    fid  = r.content.get("file_id")
                    page = r.content.get("page")
                    if fid and page is not None:
                        pages_by_file[fid].add(page)

                # Fetch images — build a lookup dict (file_id, page_no) → image
                image_lookup: dict[tuple, dict] = {}
                all_page_images: list[dict] = []

                for fid, page_nums in pages_by_file.items():
                    fetched = await _image_fetcher.fetch_pages(
                        fid, sorted(page_nums)
                    )
                    for img in fetched:
                        key = (fid, img["page_number"])
                        image_lookup[key] = img
                        all_page_images.append(img)

                # ── 5. Build Pinecone text context ───────────────────────────
                # Always pass raw text excerpts to the LLM so it can answer
                # even when vision/KG context is weak or images are missing.
                pinecone_context = "\n\n".join([
                    f"[Page {r.content.get('page')} "
                    f"from '{r.content.get('source', 'document')}']:\n"
                    f"{r.content.get('text', '')}"
                    for r in pinecone_hits
                    if r.content.get("text")
                ])

                # ── 6. Dual-track generation (parallel) ──────────────────────
                kg_answer, visual_answer = await asyncio.gather(
                    answer_from_kg(query, neo4j_results),
                    answer_from_images(query, all_page_images[:3]),
                )

                # ── 7. Build merge prompt ─────────────────────────────────────
                # Always include Pinecone text context — this is the primary
                # source of ground truth. KG and visual answers supplement it.
                if not pinecone_context and not kg_answer and not visual_answer:
                    merge_prompt = (
                        f"The user asked: {query}\n\n"
                        "No relevant information was found in the uploaded "
                        "documents. Tell the user clearly and briefly."
                    )
                else:
                    supplementary = []
                    if kg_answer:
                        supplementary.append(
                            f"Answer from Knowledge Graph:\n{kg_answer}"
                        )
                    if visual_answer:
                        supplementary.append(
                            f"Answer from Document Pages (visual):\n{visual_answer}"
                        )
                    supplementary_block = (
                        "\n\n".join(supplementary)
                        if supplementary
                        else "(no supplementary context)"
                    )

                    merge_prompt = f"""You are a precise document Q&A assistant.
Answer the user's question using the document context provided below.

Question: {query}

--- Document Text Context (primary source) ---
{pinecone_context or "(no text context available)"}

--- Supplementary Context ---
{supplementary_block}

Instructions:
- Answer using ONLY the context above.
- Be concise and factual.
- Use markdown (bold, bullet points) where it improves clarity.
- If the answer is genuinely not in any context, say so clearly.
- Do NOT invent information."""

                # ── 8. Stream merged answer token by token ────────────────────
                full_response = call_gpt4o_mini(merge_prompt, max_tokens=1000)
                if not full_response:
                    full_response = (
                        "Sorry, I was unable to generate an answer. "
                        "Please try again."
                    )

                # Stream the response token by token (word-level simulation)
                words = full_response.split(" ")
                for word in words:
                    await websocket.send_json({"type": "token", "data": word + " "})
                    await asyncio.sleep(0.02)

                # ── 9. Build citations with correct image_url ─────────────────
                # Use (file_id, page_number) tuple to look up image paths —
                # this works correctly across multiple documents.
                citations: dict = {
                    "pages": [
                        {
                            "file_name":   r.content.get("source", ""),
                            "page_number": r.content.get("page"),
                            "image_url": (
                                image_lookup
                                .get(
                                    (r.content.get("file_id"),
                                     r.content.get("page")),
                                    {}
                                )
                                .get("image_url")
                            ),
                            "excerpt": r.content.get("text", "")[:200],
                        }
                        for r in ranked
                        if r.source == "pinecone"
                    ],
                    "nodes": [
                        r.content for r in ranked if r.source == "neo4j"
                    ],
                }

                await websocket.send_json({"type": "citations", "data": citations})
                await websocket.send_json({"type": "done"})

                # ── 10. Persist turn to Supabase (fire-and-forget) ───────────
                asyncio.create_task(
                    save_turn(session_id, query, full_response, citations)
                )

            except Exception as e:
                print(f"[chat] Pipeline error: {e}")
                await websocket.send_json({"type": "error", "data": str(e)})

    except WebSocketDisconnect:
        pass
