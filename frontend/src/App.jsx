import { useCallback, useRef, useState } from "react";
import TopBar from "./components/TopBar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import GraphModal from "./components/GraphModal.jsx";
import { useChatSocket } from "./useChatSocket.js";
import { backendLabel, fetchHistory, fetchGraph } from "./api.js";

const SESSION_KEY = "rag.sessionId";

function newSessionId() {
  return "session-" + Math.random().toString(36).slice(2, 9);
}

let _seq = 0;
function uid() {
  _seq += 1;
  return "m" + _seq + "-" + Date.now();
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) || newSessionId()
  );
  const [graph, setGraph] = useState({
    open: false,
    loading: false,
    data: null,
    error: null,
  });

  // id of the bot message currently receiving streamed tokens
  const activeBotId = useRef(null);

  const updateMessage = useCallback((id, patch) => {
    setMessages((list) =>
      list.map((m) => (m.id === id ? { ...m, ...patch } : m))
    );
  }, []);

  const ensureBotMessage = useCallback(() => {
    if (activeBotId.current) return activeBotId.current;
    const id = uid();
    activeBotId.current = id;
    setMessages((list) => [
      ...list,
      { id, role: "bot", text: "", citations: null, streaming: true },
    ]);
    return id;
  }, []);

  const socket = useChatSocket({
    onToken: (tok) => {
      const id = ensureBotMessage();
      setMessages((list) =>
        list.map((m) => (m.id === id ? { ...m, text: m.text + tok } : m))
      );
    },
    onCitations: (data) => {
      const id = ensureBotMessage();
      updateMessage(id, { citations: data });
    },
    onDone: () => {
      if (activeBotId.current) updateMessage(activeBotId.current, { streaming: false });
      activeBotId.current = null;
    },
    onError: (msg) => {
      if (activeBotId.current) {
        updateMessage(activeBotId.current, { streaming: false });
        activeBotId.current = null;
      }
      setMessages((list) => [
        ...list,
        { id: uid(), role: "bot", text: msg, error: true },
      ]);
    },
  });

  const persistSession = (value) => {
    const v = value.trim();
    setSessionId(value);
    if (v) localStorage.setItem(SESSION_KEY, v);
  };

  const handleSend = (text) => {
    let sid = sessionId.trim();
    if (!sid) {
      sid = newSessionId();
      persistSession(sid);
    }
    setMessages((list) => [
      ...list,
      { id: uid(), role: "user", text },
    ]);
    activeBotId.current = null;
    socket.send(text, sid);
  };

  const handleLoadHistory = async () => {
    try {
      const rows = await fetchHistory(sessionId.trim());
      const ordered = rows.slice().reverse(); // oldest first
      const next = [];
      if (!ordered.length) {
        next.push({ id: uid(), role: "bot", text: "No history for this session." });
      }
      ordered.forEach((m) => {
        if (m.user_message)
          next.push({ id: uid(), role: "user", text: m.user_message });
        if (m.ai_response)
          next.push({
            id: uid(),
            role: "bot",
            text: m.ai_response,
            citations: m.citations || null,
          });
      });
      activeBotId.current = null;
      setMessages(next);
    } catch (err) {
      setMessages((list) => [
        ...list,
        { id: uid(), role: "bot", text: err.message, error: true },
      ]);
    }
  };

  const handleViewGraph = async () => {
    setGraph({ open: true, loading: true, data: null, error: null });
    try {
      const data = await fetchGraph(sessionId.trim());
      setGraph({ open: true, loading: false, data, error: null });
    } catch (err) {
      setGraph({ open: true, loading: false, data: null, error: err.message });
    }
  };

  return (
    <>
      <TopBar
        status={socket.status}
        label={backendLabel()}
        onToggleConnect={socket.connect}
      />
      <main className="layout">
        <Sidebar
          sessionId={sessionId}
          onSessionChange={persistSession}
          onLoadHistory={handleLoadHistory}
          onViewGraph={handleViewGraph}
        />
        <ChatPanel
          messages={messages}
          canSend={socket.status === "online"}
          onSend={handleSend}
        />
      </main>
      <GraphModal
        open={graph.open}
        loading={graph.loading}
        data={graph.data}
        error={graph.error}
        onClose={() => setGraph((g) => ({ ...g, open: false }))}
      />
    </>
  );
}
