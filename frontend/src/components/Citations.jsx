import { useState } from "react";
import { resolveImage } from "../api.js";

function CiteCard({ page }) {
  const [hideImg, setHideImg] = useState(false);
  const title =
    (page.file_name || "document") +
    (page.page_number != null ? " · p." + page.page_number : "");
  return (
    <div className="cite-card">
      <div className="pg">{title}</div>
      {page.excerpt ? <div className="ex">{page.excerpt}</div> : null}
      {page.image_url && !hideImg ? (
        <img
          loading="lazy"
          alt="page preview"
          src={resolveImage(page.image_url)}
          onError={() => setHideImg(true)}
        />
      ) : null}
    </div>
  );
}

export default function Citations({ data }) {
  if (!data) return null;
  const pages = Array.isArray(data.pages) ? data.pages : [];
  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  if (!pages.length && !nodes.length) return null;

  return (
    <div className="citations">
      {pages.length > 0 && (
        <>
          <h4>Sources</h4>
          <div className="cite-grid">
            {pages.map((p, i) => (
              <CiteCard key={i} page={p} />
            ))}
          </div>
        </>
      )}
      {nodes.length > 0 && (
        <>
          <h4>Graph nodes</h4>
          <div className="node-chips">
            {nodes.map((n, i) => (
              <span className="node-chip" key={i}>
                {n.label || n.id || JSON.stringify(n)}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
