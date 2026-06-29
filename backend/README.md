# Multimodal RAG Chatbot — Backend

FastAPI backend for a **multimodal Retrieval-Augmented Generation** chatbot built on the **MegaRAG** architecture. You upload documents (PDF/PPTX), the system reads both their **text** and **page visuals**, stores that knowledge across three backends, and answers natural-language questions with grounded, **cited** responses.

---

## 1. What it does

- **Ingests** PDF/PPTX documents: parses text, renders each page to a PNG, and embeds both into one shared vector space.
- **Stores** knowledge in three places:
  - **Pinecone** — 1536-dim page vectors + page text (for similarity retrieval).
  - **Neo4j** — a multimodal knowledge graph (entities, relationships, per-entity embeddings).
  - **Local disk** — page PNGs (read by the vision model, shown in citations).
- **Answers** questions over a WebSocket with a dual-track strategy: a knowledge-graph answer and a visual (page-image) answer are generated in parallel, then fused with **GPT-4o-mini** using the Pinecone page text as the primary source of truth.
- **Persists** chat history to **Supabase**.

The single embedding model (GME) places text and page images in the **same 1536-dim space**, which is what enables true cross-modal retrieval — a text query can match a page by its visual content.

---

## 2. Tech stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI (async, WebSocket chat) on **Python 3.12** |
| Embeddings | **GME-Qwen2-VL-2B-Instruct** — local, 4-bit quantized, 1536-dim, multimodal |
| Document parsing | PyMuPDF (`fitz`) for PDF; `python-pptx` + **LibreOffice** for PPTX |
| Vector DB | **Pinecone** (serverless, cosine, 1536-dim) |
| Knowledge graph | **Neo4j** (with native vector index on entity embeddings) |
| Reasoning LLM | **GPT-4o-mini** via GitHub Models |
| LLM fallback | **Ollama Gemma4** (local) — used when GitHub Models is rate-limited or down |
| Chat history | **Supabase** (Postgres) |
| Config | `pydantic-settings` reading from `.env` |

---

## 3. Prerequisites

- **Python 3.12** — *not 3.13* (the pinned PyTorch build is incompatible with 3.13).
- **CUDA-capable GPU** strongly recommended. GME loads in 4-bit (~2–3 GB of weights); expect roughly **4–5 GB GPU resident** while serving. A 6 GB card (e.g. RTX 4050) is enough for GME alone — but note the Ollama fallback won't fit alongside it on 6 GB and will run on CPU.
- **Neo4j** running and reachable (default `bolt://127.0.0.1:7687`).
- **Pinecone** account (free tier works).
- **GitHub Personal Access Token** for GitHub Models (no special scopes needed).
- **Ollama** installed with a Gemma4 model pulled, if you want the local fallback:
  ```bash
  ollama pull gemma4:e4b
  ```
- **LibreOffice** installed and on `PATH` **only if you ingest PPTX** — rendering converts the deck to PDF via `libreoffice --headless`. PDF-only workflows don't need it.

---

## 4. Setup

1. Create a Python 3.12 virtual environment:
   ```bash
   py -3.12 -m venv venv312
   venv312\Scripts\activate
   ```
   > Note: this repo may contain a stale `venv/` built on Python 3.13 with no PyTorch — using it makes the server crash at startup with `ModuleNotFoundError: No module named 'torch'`. Use `venv312`.

2. Install PyTorch with CUDA support **first** (before the rest):
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

3. Install remaining requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env` (see section 5):
   ```bash
   copy .env.example .env
   ```

5. Create a **Pinecone index**: 1536 dimensions, `cosine` metric, AWS `us-east-1`. (The code will auto-create it on first upsert if it doesn't exist.)

6. Create the **Neo4j vector index** (section 6). This is a one-time manual step — without it, graph retrieval fails and the system silently degrades to Pinecone-only answers.

7. Run the server:
   ```bash
   python -m app.main
   ```
   This serves on **port 8080** (the `__main__` block in `app/main.py`). On startup the GME model is pre-loaded (a warmup embed) so the first real query isn't slow.

   > Prefer the `uvicorn` CLI? It ignores the `__main__` block and defaults to 8000, so pass the port explicitly: `uvicorn app.main:app --reload --port 8080`.

---

## 5. Environment variables (`.env`)

| Key | Required | Purpose |
|-----|----------|---------|
| `PINECONE_API_KEY` | yes | Pinecone access |
| `PINECONE_INDEX_NAME` | yes | Target index name (1536-dim, cosine) |
| `NEO4J_URI` | yes | e.g. `bolt://127.0.0.1:7687` |
| `NEO4J_USER` | yes | Neo4j username |
| `NEO4J_PASSWORD` | yes | Neo4j password |
| `GITHUB_TOKEN` | yes | GitHub Models token for GPT-4o-mini |
| `SUPABASE_URL` | optional | Chat-history persistence (failures are non-fatal) |
| `SUPABASE_KEY` | optional | Supabase key |
| `MAX_UPLOAD_MB` | optional | Upload size limit (default 50) |
| `GEMINI_API_KEY` | unused | Present in config for legacy reasons; the active fallback is Ollama, not Gemini |

MegaRAG hyperparameters (have sensible paper-default values in `config.py`, override via `.env` if needed): `TOP_K_ENTITIES=60`, `TOP_K_RELATIONS=60`, `TOP_M_PAGES=6`, `REFINEMENT_SUBGRAPH_SIZE=120`.

---

## 6. Neo4j vector index setup

Run this once in the Neo4j Browser **before ingesting**:

```cypher
CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
FOR (e:Entity) ON e.embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}}
```

The graph retriever calls `db.index.vector.queryNodes('entity_embedding_index', …)`. If the index is missing, the graph branch fails and answers fall back to Pinecone-only.

---

## 7. API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload a **PDF / PPTX / PPT** (max 50 MB). Returns a `file_id` immediately; ingestion runs in the background. |
| `WS`   | `/ws/chat` | WebSocket chat — full RAG pipeline with word-by-word response delivery. |
| `GET`  | `/api/graph/{session_id}` | Returns the knowledge graph (currently the full graph; per-session filtering is planned). |
| `GET`  | `/api/history?session_id=…` | Past conversation turns, newest first. Omit `session_id` for the 50 most recent globally. |
| `GET`  | `/health` | Liveness check — returns `{"status": "ok"}`. |

**Upload response:**
```json
{"file_id": "uuid", "status": "processing", "filename": "doc.pdf"}
```
Ingestion (parse → render → embed → upsert → graph build → graph refine) then runs asynchronously.

---

## 8. WebSocket message format

**Client sends:**
```json
{"type": "query", "text": "your question", "session_id": "abc"}
```

**Server replies, in order:**
```json
{"type": "token", "data": "word "}     // repeated, one per word
{"type": "citations", "data": {"pages": [...], "nodes": [...]}}
{"type": "done"}
```
On failure: `{"type": "error", "data": "<message>"}`.

> Note: the per-word `token` messages are **simulated streaming** — the full answer is generated first, then split on spaces and emitted with a short delay. It looks live in the UI, but the model has already finished generating.

Each citation page carries `file_name`, `page_number`, an `image_url` for the rendered page, and a text `excerpt`.

---

## 9. Project structure

```
app/
├── main.py                  FastAPI app, router registration, GME warmup
├── config.py                pydantic-settings from .env
│
├── ingestion/
│   ├── ingest_pipeline.py   orchestrates parse → render → embed → upsert → KG
│   ├── parser.py            PDF/PPTX → text per page
│   ├── renderer.py          pages → PNG (150 DPI); PPTX via LibreOffice→PDF
│   ├── gme_embedder.py      GME model: embed text / image / fused
│   ├── pinecone_upserter.py upsert + search Pinecone
│   └── github_client.py     GPT-4o-mini calls + Ollama Gemma4 fallback
│
├── knowledge_graph/
│   ├── mmkg_builder.py      build graph: pages, entities, relationships
│   ├── entity_extractor.py  GPT-4o-mini vision entity extraction
│   ├── graph_refiner.py     MegaRAG stage-2 refinement
│   ├── neo4j_store.py       Neo4j CRUD + vector search
│   └── gcs_store.py         local PNG store (GCS-compatible interface)
│
├── retrieval/
│   ├── query_analyzer.py    split query → low/high-level keywords
│   ├── pinecone_retriever.py embed query → ANN search
│   ├── neo4j_retriever.py   embed keywords → entity vector search → 1-hop
│   ├── image_fetcher.py     load page PNGs from disk
│   └── reranker.py          merge Pinecone + Neo4j by cosine score
│
├── generation/
│   ├── kg_answerer.py       answer from the graph subgraph
│   ├── visual_answerer.py   answer from page images (vision)
│   ├── answer_generator.py  two-stage fusion (offline pipeline)
│   ├── prompt_builder.py    context prompt assembly
│   ├── citation_formatter.py format citations for the UI
│   └── history.py           save/load turns to Supabase
│
└── routers/
    ├── upload.py            POST /api/upload → background ingestion
    ├── chat.py              WS /ws/chat → live query pipeline
    ├── graph.py             graph inspection endpoint
    └── history.py           chat history endpoint
```

> The live query path is `routers/chat.py`. The two-stage `answer_generator.fuse_answers` exists but is **not** on the live WebSocket path — `chat.py` builds a single merge prompt instead.

---

## 10. Models — what runs where

| Model | Location | Job |
|-------|----------|-----|
| GME-Qwen2-VL-2B-Instruct | Local (4-bit, GPU) | All embeddings — text, image, fused. 1536-dim, one shared space. |
| GPT-4o-mini | GitHub Models (cloud) | Entity extraction, query analysis, KG/visual answering, final fusion. |
| Gemma4 | Local via Ollama | Fallback when GitHub Models is rate-limited or errors. |

---

## 11. Rate limits & ingestion time

- **GitHub GPT-4o-mini (free tier):** 150 requests/day, 10 requests/minute.
- Entity extraction sleeps **6 seconds per page** to respect the 10 RPM limit, and runs **twice** (build + refinement). A ~30-page document therefore takes roughly **10–15 minutes** for the graph stages. Embedding + Pinecone upsert is comparatively fast.
- On rate-limit/error, calls fall back to Ollama Gemma4 locally.

---

## 12. Known limitations

These are current, verified limitations — not blockers, but worth knowing. See `../.response/pipeline-verification-2026-06-26.md` for the full analysis.

- **Pinecone text is capped at 500 chars.** The embedding is computed on the full page text (so retrieval finds the right page), but only `text[:500]` is stored and handed to the LLM. The visual answerer reading the full page image partially mitigates this.
- **The graph build pass does not persist entity→entity relationships.** Build-stage extraction returns relationships keyed by entity *id* (`e1`, `e2`), but `create_relationship` matches by *label*, so those edges are silently dropped. Only the **refinement** pass (which keys by label) persists relationships — leaving a large fraction of entities without edges.
- **Entity descriptions are extracted but not stored** on Neo4j nodes (only `label`, `type`, `id` are written), so refinement prompts and KG answers see empty descriptions.
- **Chat searches all uploaded documents.** The live path does not scope retrieval by `file_id`, so it behaves as one shared knowledge base rather than per-document chat.
- **No authentication; CORS is open to `*`.** Fine for local prototyping, not for exposure.
- **No formal evaluation harness** — answer/retrieval quality is currently assessed manually.

---

## 13. Operational notes

- GME loads on first use (~7 s); the startup warmup pre-loads it so the first query isn't slow.
- Neo4j may emit a harmless deprecation warning for `db.index.vector.queryNodes`.
- Page images live under `data/page_images/`, keyed by `file_id`. A `file_id` mismatch (e.g. re-uploading) can leave orphaned images — re-ingest cleanly if citations point to missing images.
- The uvicorn log (`server.log` if you redirect to it) is block-buffered by Python; it can lag well behind actual progress during long ingestions. Query Neo4j/Pinecone directly for ground-truth ingestion status.
