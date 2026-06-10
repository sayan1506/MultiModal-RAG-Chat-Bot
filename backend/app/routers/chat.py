"""Chat router — WebSocket endpoint with full RAG pipeline and Gemini streaming.

Implements dual-track generation (visual + knowledge graph), merges results,
and streams final answer with citations via Gemini streaming API.
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.config import settings
from app.retrieval.query_analyzer import analyze_query
from app.retrieval.pinecone_retriever import PineconeRetriever
from app.retrieval.reranker import rerank
from app.generation.visual_answerer import VisualAnswerer
from app.generation.kg_answerer import KGAnswerer
from app.generation.history import ConversationHistory

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Accept WebSocket connection and stream RAG responses with Gemini.

    Expected client message:
        {"type": "query", "text": "...", "session_id": "..."}

    Server sends:
        {"type": "token", "data": "..."} → progressive tokens
        {"type": "citations", "data": {...}} → citations with pages and nodes
        {"type": "done"} → completion signal

    Process:
        1. Analyze query and retrieve from Pinecone
        2. Run dual-track generation (visual + KG)
        3. Build final prompt merging both contexts
        4. Stream answer via Gemini
        5. Send citations
        6. Persist conversation turn to Supabase
    """
    await websocket.accept()

    # Initialize components
    gemini_client = genai.Client(api_key=settings.gemini_api_key)
    pinecone_retriever = PineconeRetriever()
    visual_answerer = VisualAnswerer()
    kg_answerer = KGAnswerer()
    history_manager = ConversationHistory()

    try:
        while True:
            # Receive query from client
            raw: str = await websocket.receive_text()
            payload: dict = json.loads(raw)

            query_text: str = payload.get("text", "")
            session_id: str = payload.get("session_id", str(uuid.uuid4()))

            if not query_text:
                await websocket.send_json({"type": "error", "data": "Empty query"})
                continue

            # ── Step 1: Query Analysis ──────────────────────────
            analysis = await analyze_query(query_text)
            keywords = analysis.get("low_level_keywords", [])

            # ── Step 2: Pinecone Retrieval ──────────────────────
            pinecone_results = pinecone_retriever.retrieve(
                query_text=query_text,
                top_k=5,
            )

            # Extract file_id and page numbers from top results
            file_ids = set()
            page_numbers = []

            for result in pinecone_results[:3]:  # Top 3 for visual context
                metadata = result.metadata
                file_id = metadata.get("file_id")
                page_num = metadata.get("page_number")

                if file_id:
                    file_ids.add(file_id)
                if page_num:
                    page_numbers.append(page_num)

            # Use first file_id for visual context (simplification)
            primary_file_id = list(file_ids)[0] if file_ids else None

            # ── Step 3: Dual-Track Generation ───────────────────
            # Run visual and KG answering in parallel
            visual_task = visual_answerer.answer_with_images(
                query=query_text,
                file_id=primary_file_id or "",
                page_numbers=page_numbers[:3],
            ) if primary_file_id else None

            kg_task = kg_answerer.answer_with_graph(
                query=query_text,
                keywords=keywords,
            )

            # Await both
            visual_result = await visual_task if visual_task else None
            kg_result = await kg_task

            # ── Step 4: Build Final Prompt ──────────────────────
            final_prompt = _build_merged_prompt(
                query_text,
                visual_result,
                kg_result,
            )

            # ── Step 5: Stream Answer via Gemini ────────────────
            full_answer = ""

            try:
                stream = gemini_client.models.generate_content_stream(
                    model="gemini-2.0-flash-lite",
                    contents=final_prompt,
                )

                for chunk in stream:
                    if chunk.text:
                        full_answer += chunk.text
                        await websocket.send_json({
                            "type": "token",
                            "data": chunk.text,
                        })

            except Exception as e:
                error_msg = str(e)
                print(f"Streaming error: {error_msg}")

                # Fallback: use fallback model without streaming
                try:
                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=final_prompt,
                    )
                    full_answer = response.text
                    await websocket.send_json({
                        "type": "token",
                        "data": full_answer,
                    })
                except Exception as fallback_error:
                    full_answer = f"Error generating response: {fallback_error}"
                    await websocket.send_json({
                        "type": "token",
                        "data": full_answer,
                    })

            # ── Step 6: Send Citations ──────────────────────────
            citations = _build_citations(visual_result, kg_result)
            await websocket.send_json({
                "type": "citations",
                "data": citations,
            })

            # ── Step 7: Signal Completion ───────────────────────
            await websocket.send_json({"type": "done"})

            # ── Step 8: Persist Conversation Turn ───────────────
            await history_manager.save_turn(
                session_id=session_id,
                user_query=query_text,
                assistant_response=full_answer,
                metadata={
                    "citations": citations,
                    "visual_model": visual_result.get("model_used") if visual_result else None,
                    "kg_model": kg_result.get("model_used"),
                },
            )

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except json.JSONDecodeError:
        await websocket.close(code=1003, reason="Invalid JSON")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except:
            pass


def _build_merged_prompt(
    query: str,
    visual_result: dict | None,
    kg_result: dict,
) -> str:
    """Build a final prompt that merges visual and knowledge graph context."""
    sections = [
        "You are an expert multimodal RAG assistant.",
        f"Answer the user's question: \"{query}\"",
        "",
        "Use the following context to provide a comprehensive answer:",
        "",
    ]

    # Add visual context if available
    if visual_result and visual_result.get("answer"):
        sections.append("=== Visual Context (from page screenshots) ===")
        sections.append(visual_result["answer"])
        sections.append("")

    # Add knowledge graph context
    if kg_result and kg_result.get("answer"):
        sections.append("=== Knowledge Graph Context ===")
        sections.append(kg_result["answer"])
        sections.append("")

    sections.append("Synthesize the above context and provide a clear, detailed answer.")
    sections.append("If the answer is not present in the context, state that clearly.")

    return "\n".join(sections)


def _build_citations(
    visual_result: dict | None,
    kg_result: dict,
) -> dict:
    """Build citations object combining page references and graph nodes."""
    citations = {
        "pages": [],
        "graph_nodes": [],
    }

    # Add page citations
    if visual_result and visual_result.get("pages_used"):
        citations["pages"] = [
            {"page_number": page_num}
            for page_num in visual_result["pages_used"]
        ]

    # Add knowledge graph node citations
    if kg_result and kg_result.get("subgraph"):
        subgraph = kg_result["subgraph"]
        nodes = subgraph.get("nodes", [])
        citations["graph_nodes"] = [
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "type": node.get("type"),
            }
            for node in nodes[:10]  # Limit to top 10 nodes
        ]

    return citations
