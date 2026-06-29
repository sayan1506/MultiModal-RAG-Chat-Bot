import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ── CORS strategy ──────────────────────────────────────────────────
// In dev, the browser talks ONLY to the Vite origin (localhost:5173).
// These proxy rules forward REST + WebSocket traffic to the FastAPI
// backend, so every request the browser makes is same-origin and CORS
// never comes into play. Override the target with VITE_BACKEND_URL.
const BACKEND = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api":     { target: BACKEND, changeOrigin: true },
      "/ws":      { target: BACKEND, changeOrigin: true, ws: true },
      "/data":    { target: BACKEND, changeOrigin: true },
      "/health":  { target: BACKEND, changeOrigin: true },
    },
  },
});
