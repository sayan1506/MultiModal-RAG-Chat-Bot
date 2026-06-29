export default function TopBar({ status, label, onToggleConnect }) {
  const text =
    status === "online"
      ? "Disconnect"
      : status === "connecting"
      ? "Connecting…"
      : "Connect";
  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo">◆</span>
        <h1>Multimodal RAG</h1>
      </div>
      <div className="conn">
        <span className="backend-label" title={label}>
          {label}
        </span>
        <span className={"dot " + status} title={status} />
        <button onClick={onToggleConnect}>{text}</button>
      </div>
    </header>
  );
}
