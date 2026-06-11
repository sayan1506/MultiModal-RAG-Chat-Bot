const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/chat";

export class ChatWebSocket {
  constructor({ onToken, onDone, onError }) {
    this.onToken = onToken;
    this.onDone = onDone;
    this.onError = onError;
    this.ws = null;
  }

  connect() {
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => console.log("✅ WebSocket Connected");
    this.ws.onclose = () => console.log("❌ WebSocket Disconnected");
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "token") {
        this.onToken(msg.data);
      } else if (msg.type === "done") {
        this.onDone();
      } else if (msg.type === "error") {
        this.onError(msg.data);
      }
    };
  }

  send(text) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ text }));
    }
  }

  disconnect() {
    this.ws?.close();
  }
}