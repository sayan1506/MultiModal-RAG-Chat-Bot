import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Message from "./Message.jsx";

export default function ChatPanel({ messages, canSend, onSend }) {
  const [text, setText] = useState("");
  const taRef = useRef(null);
  const scrollRef = useRef(null);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const grow = () => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  };
  useEffect(grow, [text]);

  const submit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(e);
    }
  };

  return (
    <section className="chat">
      <div className="messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="empty-hint">
            Connect to your backend, upload a document, then ask a question.
          </div>
        ) : (
          messages.map((m) => (
            <Message
              key={m.id}
              role={m.role}
              text={m.text}
              citations={m.citations}
              error={m.error}
              streaming={m.streaming}
            />
          ))
        )}
      </div>
      <form className="composer" onSubmit={submit}>
        <textarea
          ref={taRef}
          rows={1}
          placeholder="Ask about your documents…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="submit" disabled={!canSend || !text.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
