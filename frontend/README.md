# Multimodal RAG Chatbot — Frontend

A **React + Vite** single-page app for the multimodal RAG chatbot. It lets you upload documents, chat over them with grounded **cited** answers (page images + knowledge-graph nodes), and inspect the knowledge graph — talking to the FastAPI backend over REST and a WebSocket.

---

## 1. What it does

- **Upload** PDF/PPTX documents to the backend (`POST /api/upload`).
- **Chat** over a WebSocket (`/ws/chat`) with live, word-by-word answer delivery.
- **Show citations** — rendered page images and graph nodes that grounded each answer.
- **Inspect the knowledge graph** in a modal (`GET /api/graph/{session_id}`).
- **Load chat history** for a session (`GET /api/history`).

---

## 2. Tech stack

| Layer | Technology |
|-------|-----------|
| UI framework | **React 18** |
| Build tool / dev server | **Vite 5** |
| Language | Plain JS + JSX (no TypeScript) |
| Backend transport | `fetch` (REST) + native `WebSocket` (chat) |

---

## 3. Prerequisites

- **Node.js 18+** (LTS recommended — Vite 5 requires Node 18 or 20+).
- **npm** (ships with Node).
- The **backend running and reachable** (see `../backend/README.md`). The backend runs on `http://localhost:8080` via `python -m app.main`.

---

## 4. Setup

From the `frontend/` directory:

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the dev server:
   ```bash
   npm run dev
   ```
   Vite serves the app at **http://localhost:5173**.

That's it for the common case — no `.env` is needed. The Vite dev server proxies all backend traffic to `http://localhost:8080` (see section 5), so the browser only ever talks to the Vite origin and **CORS never comes into play**.

> Make sure the backend is up first, or uploads/chat will fail with a "backend may be down" hint.

---

## 5. Networking: the dev proxy (important)

How the frontend reaches the backend is controlled by one variable, `VITE_BACKEND_URL`, which behaves **differently** depending on whether it's set. Understanding this avoids most "it won't connect / CORS" issues.

**Recommended (leave `VITE_BACKEND_URL` unset):**
- The browser makes **relative** requests (`/api/...`, `/ws/...`).
- Vite's dev server proxies them to the backend — default target `http://localhost:8080` (`vite.config.js`).
- Every request is same-origin from the browser's view, so **no CORS**.
- To point the proxy at a backend on a different host/port, set `VITE_BACKEND_URL` and Vite will proxy there.

**Direct mode (set `VITE_BACKEND_URL` to an absolute URL):**
- The browser sends requests **directly** to that URL, bypassing the proxy.
- This requires the backend to allow CORS (it currently allows `*`), and the URL must exactly match where the backend listens.

The proxied paths are `/api`, `/ws` (WebSocket), `/data` (page images), and `/health`.

> ℹ️ A `frontend/.env` with `VITE_BACKEND_URL=http://localhost:8080` matches the backend and is fine to keep — it just switches the app to *direct* mode (browser talks straight to 8080, relying on the backend's open CORS) instead of going through the proxy. Delete `.env` to use the proxy instead; either way the target is 8080. `.env` is gitignored.

---

## 6. Environment variables (`.env`, optional)

| Key | Required | Purpose |
|-----|----------|---------|
| `VITE_BACKEND_URL` | no | Backend origin. **Unset** → use the Vite proxy to `localhost:8080` (recommended). Set → browser talks directly to this URL (proxy target also follows it). |

To create one:
```bash
copy NUL .env        # Windows
# then add: VITE_BACKEND_URL=http://localhost:8080
```

---

## 7. Build for production

```bash
npm run build      # outputs static assets to dist/
npm run preview    # serve the built dist/ locally to verify
```

> The dev proxy in `vite.config.js` only applies to `npm run dev`. A production build has **no proxy** — you must serve `dist/` behind something that routes `/api`, `/ws`, `/data`, and `/health` to the backend, or build with `VITE_BACKEND_URL` set to the backend's public URL (which then requires backend CORS).

---

## 8. Project structure

```
frontend/
├── index.html              Vite entry HTML (mounts #root)
├── vite.config.js          dev server + proxy rules (/api, /ws, /data, /health)
├── package.json            scripts: dev / build / preview
├── .env                    optional — VITE_BACKEND_URL (gitignored)
└── src/
    ├── main.jsx            React root render
    ├── App.jsx             top-level app + state
    ├── api.js              REST helpers, WS URL builder, image URL resolver
    ├── useChatSocket.js    WebSocket hook for the chat stream
    ├── markdown.jsx        markdown rendering for messages
    ├── styles.css          global styles
    └── components/
        ├── TopBar.jsx      header / backend label
        ├── Sidebar.jsx     uploads + session controls
        ├── ChatPanel.jsx   chat input + message list
        ├── Message.jsx     single message rendering
        ├── Citations.jsx   cited pages / nodes
        └── GraphModal.jsx  knowledge-graph viewer
```

---

## 9. Troubleshooting

- **"Request failed — backend may be down…"** — the backend isn't running, or `VITE_BACKEND_URL` points somewhere wrong. Confirm the backend responds at `http://localhost:8080/health`, then check section 5.
- **Chat connects but never answers** — the WebSocket (`/ws/chat`) didn't reach the backend. In proxy mode this works automatically; in direct mode confirm the backend URL and that it's serving the WebSocket.
- **Citation images broken** — page images are served from the backend under `data/page_images/`. The `/data` path must be proxied (it is, in dev) and the backend must mount its `data/` dir as static files.
- **Port 5173 in use** — stop the other process or change `server.port` in `vite.config.js`.
