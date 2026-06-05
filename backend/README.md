# Multimodal RAG Chatbot — Backend

A modular FastAPI backend scaffold for a **Multimodal RAG Chatbot** that will eventually accept text, images, audio, PDFs, and PPTX files, using **Gemini**, **Pinecone**, **Neo4j**, and **CLIP** under the hood.

> **Current status — Phase 1**: clean project structure with stub endpoints ready for future integration.

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, CORS, router registration
│   ├── config.py           # pydantic-settings configuration
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── upload.py       # POST /api/upload
│   │   ├── chat.py         # WS   /ws/chat
│   │   ├── graph.py        # GET  /api/graph/{session_id}
│   │   └── history.py      # GET  /api/history
│   ├── ingestion/          # (future) file parsing & chunking
│   ├── retrieval/          # (future) vector search & ranking
│   ├── generation/         # (future) Gemini response generation
│   └── knowledge_graph/    # (future) Neo4j graph operations
├── .env.example
├── requirements.txt
└── README.md
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/api/upload` | Accepts a file upload, returns a stub acknowledgement |
| `GET` | `/api/graph/{session_id}` | Returns knowledge-graph nodes & links (stub) |
| `GET` | `/api/history` | Returns chat history (stub) |
| `WS` | `/ws/chat` | WebSocket — mock token-by-token streaming |

---

## Setup

### 1. Clone & navigate

```bash
cd backend
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **Windows (CMD):** `.\venv\Scripts\activate.bat`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Edit `.env` and fill in any keys you need (not required for Phase 1).

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

The API is now available at **http://127.0.0.1:8000**.

Interactive docs: **http://127.0.0.1:8000/docs**

---

## Testing the WebSocket

You can use [websocat](https://github.com/vi/websocat) or the Swagger UI to test:

```bash
websocat ws://127.0.0.1:8000/ws/chat
{"text": "hello world"}
```

Expected streamed response:

```json
{"type":"token","data":"hello "}
{"type":"token","data":"world "}
{"type":"done"}
```

---

## License

This project is private and not yet licensed for distribution.
