// ── API layer ───────────────────────────────────────────────────────
// CORS strategy:
//   • Leave VITE_BACKEND_URL unset → BASE is "" → all requests are
//     relative ("/api/..."), so they hit the Vite dev origin and get
//     proxied to FastAPI (see vite.config.js). Browser sees same-origin,
//     CORS never fires.
//   • Set VITE_BACKEND_URL to an absolute URL → requests go directly to
//     that backend. We send `credentials: "omit"` so the wildcard CORS
//     config (allow_origins=["*"]) on the backend stays valid.

const BASE = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/+$/, "");

export function apiUrl(path) {
  return BASE + path;
}

// Derive the WebSocket URL. With no BASE, build it from the current page
// origin (the proxy upgrades /ws). With an absolute BASE, swap the scheme.
export function wsUrl(path = "/ws/chat") {
  const origin = BASE || window.location.origin;
  const u = new URL(origin);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.pathname = path;
  u.search = "";
  return u.toString();
}

export function backendLabel() {
  return BASE || window.location.origin + " (proxy)";
}

function networkHint(err) {
  const m = (err && err.message) || String(err);
  if (/Failed to fetch|NetworkError|Load failed/i.test(m)) {
    return (
      `Request failed — backend may be down, the URL wrong, or CORS ` +
      `blocking it. Target: ${BASE || "Vite proxy"}.`
    );
  }
  return m;
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  let res;
  try {
    res = await fetch(apiUrl("/api/upload"), {
      method: "POST",
      body: form,
      credentials: "omit",
    });
  } catch (e) {
    throw new Error(networkHint(e));
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `${res.status} ${res.statusText}`);
  }
  return data; // { file_id, status, filename }
}

export async function fetchHistory(sessionId) {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  let res;
  try {
    res = await fetch(apiUrl("/api/history" + qs), { credentials: "omit" });
  } catch (e) {
    throw new Error(networkHint(e));
  }
  const data = await res.json().catch(() => ({}));
  return data.messages || [];
}

export async function fetchGraph(sessionId) {
  const sid = sessionId || "default";
  let res;
  try {
    res = await fetch(apiUrl("/api/graph/" + encodeURIComponent(sid)), {
      credentials: "omit",
    });
  } catch (e) {
    throw new Error(networkHint(e));
  }
  return res.json();
}

// Backend returns image_url as a local filesystem path. Map it onto an
// HTTP path under the backend's data/ dir (requires a StaticFiles mount).
export function resolveImage(localPath) {
  if (!localPath) return "";
  const norm = String(localPath).replace(/\\/g, "/");
  const idx = norm.indexOf("data/");
  const rel = idx >= 0 ? norm.slice(idx) : norm.replace(/^\/+/, "");
  return apiUrl("/" + rel);
}
