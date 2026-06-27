import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl } from "./api.js";

// Manages the /ws/chat connection and the token → citations → done
// streaming protocol. Exposes connection status, a send() fn, and
// callbacks for the consumer to update its message list.
export function useChatSocket({ onToken, onCitations, onDone, onError }) {
  const [status, setStatus] = useState("offline"); // offline|connecting|online
  const wsRef = useRef(null);

  // Keep latest callbacks without forcing reconnects.
  const cbs = useRef({});
  cbs.current = { onToken, onCitations, onDone, onError };

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("offline");
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      disconnect();
      return;
    }
    let ws;
    try {
      ws = new WebSocket(wsUrl());
    } catch (e) {
      cbs.current.onError?.("Could not open WebSocket: " + e.message);
      setStatus("offline");
      return;
    }
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => setStatus("online");

    ws.onmessage = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      switch (msg.type) {
        case "token":
          cbs.current.onToken?.(msg.data || "");
          break;
        case "citations":
          cbs.current.onCitations?.(msg.data);
          break;
        case "done":
          cbs.current.onDone?.();
          break;
        case "error":
          cbs.current.onError?.(msg.data || "Unknown error.");
          break;
      }
    };

    ws.onerror = () => {
      cbs.current.onError?.(
        "WebSocket error. Is the backend running and reachable?"
      );
    };

    ws.onclose = () => {
      wsRef.current = null;
      setStatus("offline");
    };
  }, [disconnect]);

  const send = useCallback((text, sessionId) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      cbs.current.onError?.("Not connected. Click Connect first.");
      return false;
    }
    ws.send(
      JSON.stringify({ type: "query", text, session_id: sessionId })
    );
    return true;
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return { status, connect, disconnect, send };
}
