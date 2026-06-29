import { useRef, useState } from "react";
import { uploadDocument } from "../api.js";

export default function Sidebar({
  sessionId,
  onSessionChange,
  onLoadHistory,
  onViewGraph,
}) {
  const fileInputRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [drag, setDrag] = useState(false);
  const [uploads, setUploads] = useState([]); // {name, state, detail}

  const pick = (file) => setSelected(file || null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) pick(f);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!selected) return;
    const file = selected;
    pick(null);
    if (fileInputRef.current) fileInputRef.current.value = "";

    const id = Date.now() + ":" + file.name;
    setUploads((u) => [
      { id, name: file.name, state: "uploading", detail: "" },
      ...u,
    ]);
    try {
      const data = await uploadDocument(file);
      setUploads((u) =>
        u.map((it) =>
          it.id === id
            ? {
                ...it,
                state: data.status || "ok",
                detail: "id: " + (data.file_id || ""),
              }
            : it
        )
      );
    } catch (err) {
      setUploads((u) =>
        u.map((it) =>
          it.id === id
            ? { ...it, state: "failed", detail: err.message }
            : it
        )
      );
    }
  };

  return (
    <aside className="sidebar">
      <section className="panel">
        <h2>Upload document</h2>
        <form onSubmit={submit} className="upload-form">
          <label
            className={"dropzone" + (drag ? " drag" : "")}
            onDragEnter={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.pptx,.ppt"
              hidden
              onChange={(e) => pick(e.target.files[0])}
            />
            <span>
              {selected
                ? selected.name
                : "Drop a PDF / PPTX here or click to browse"}
            </span>
          </label>
          <button type="submit" disabled={!selected}>
            Upload &amp; ingest
          </button>
        </form>

        <ul className="upload-list">
          {uploads.map((u) => (
            <li key={u.id}>
              <span className={"tag " + (u.state === "failed" ? "bad" : "")}>
                {u.state}
              </span>
              {u.name}
              {u.detail ? (
                <>
                  <br />
                  <small>{u.detail}</small>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Session</h2>
        <input
          type="text"
          spellCheck={false}
          placeholder="session id"
          value={sessionId}
          onChange={(e) => onSessionChange(e.target.value)}
        />
        <div className="row">
          <button className="ghost" onClick={onLoadHistory}>
            Load history
          </button>
          <button className="ghost" onClick={onViewGraph}>
            View graph
          </button>
        </div>
      </section>
    </aside>
  );
}
