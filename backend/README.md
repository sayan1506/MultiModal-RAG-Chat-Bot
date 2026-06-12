# Multimodal RAG Chatbot — Backend

## 1. Project Overview

The backend for a **Multimodal RAG Chatbot** built on the **MegaRAG architecture**.

- Ingests documents (PDF/PPTX) and builds both a dense vector store and a multimodal knowledge graph (MMKG).
- Uses **GME multimodal embeddings** — text and page images share a single 1536-dim vector space, enabling true cross-modal retrieval.
- **Two-stage generation**: a knowledge-graph answer and a visual (page-image) answer are produced in parallel, then fused into a single response by **GPT-4o-mini**.

## 2. Tech Stack

- **FastAPI** on **Python 3.12**
- **GME-Qwen2-VL-2B-Instruct** — local, 4-bit quantized, 1536-dim multimodal embeddings
- **Pinecone** — 1536-dim cosine similarity index
- **Neo4j Desktop** — vector index + knowledge graph store
- **GitHub Models GPT-4o-mini** — entity extraction, graph refinement, and answer generation
- **Google Gemini** — fallback model
- **Supabase** — chat history persistence

## 3. Prerequisites

- **Python 3.12** (not 3.13 — PyTorch is incompatible)
- **CUDA-capable GPU** recommended (RTX 4050 or better)
- **Neo4j Desktop** installed and running
- **Pinecone** free tier account
- **GitHub Personal Access Token** (no scopes needed)

## 4. Setup Instructions

1. Clone the repository.
2. Create a virtual environment with Python 3.12:
   ```bash
   py -3.12 -m venv venv312
   ```
3. Activate it:
   ```bash
   venv312\Scripts\activate
   ```
4. Install PyTorch with CUDA support **first**:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
5. Install the remaining requirements:
   ```bash
   pip install -r requirements.txt
   ```
6. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   copy .env.example .env
   ```
7. Create a **Pinecone index**: 1536 dimensions, `cosine` metric, AWS `us-east-1`.
8. Create the **Neo4j vector index** (see section 5).
9. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## 5. Neo4j Vector Index Setup

Run this Cypher in the Neo4j Browser before ingesting documents:

```cypher
CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
FOR (e:Entity) ON e.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}}
```

## 6. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Ingest a PDF document |
| `WS`   | `/ws/chat` | WebSocket chat with streaming responses |
| `GET`  | `/api/graph/{session_id}` | Knowledge graph for a session |
| `GET`  | `/api/history` | Chat history |
| `GET`  | `/health` | Liveness check |

## 7. WebSocket Message Format

**Client sends:**

```json
{"type": "query", "text": "your question", "session_id": "abc"}
```

**Server streams:**

```json
{"type": "token", "data": "word "}
```
(repeated per word)

```json
{"type": "citations", "data": {...}}
{"type": "done"}
```

## 8. Project Structure

```
app/
├── ingestion/        - PDF parsing, GME embeddings, entity extraction
├── knowledge_graph/  - Neo4j store, MMKG builder, graph refiner
├── retrieval/        - Query analyzer, Pinecone + Neo4j retrieval, reranker
├── generation/       - KG answerer, visual answerer, answer generator,
│                       generation pipeline
└── routers/          - FastAPI route handlers
```

## 9. Rate Limits

- **GitHub GPT-4o-mini**: 150 requests/day, 10 requests/minute
- **Gemini**: free tier quotas apply
- For large documents, ingestion may be slow due to rate limiting (entity extraction is throttled to respect the 10 RPM limit).

## 10. Known Issues

- GME loads on the first request (~7s) but is cached for all subsequent requests. The startup warmup pre-loads it to avoid a slow first query.
- Neo4j `db.index.vector.queryNodes` may emit a deprecation warning (harmless).
- Images require a clean re-ingestion if a `file_id` mismatch occurs.
