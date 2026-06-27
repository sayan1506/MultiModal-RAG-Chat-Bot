export default function GraphModal({ open, loading, data, error, onClose }) {
  if (!open) return null;

  let body;
  if (loading) {
    body = "Loading…";
  } else if (error) {
    body = error;
  } else if (data) {
    const nodes = (data.nodes || []).length;
    const links = (data.links || []).length;
    body = `// ${nodes} nodes · ${links} links\n\n` + JSON.stringify(data, null, 2);
  } else {
    body = "No graph data.";
  }

  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-head">
          <h2>Knowledge graph</h2>
          <button className="icon-btn" onClick={onClose}>
            ✕
          </button>
        </div>
        <pre className="graph-output">{body}</pre>
      </div>
    </div>
  );
}
