// Minimal, XSS-safe markdown → React nodes (bold, inline code, bullets).
// Text nodes are rendered by React, so no manual escaping is needed.
import React from "react";

function parseInline(text, keyPrefix) {
  const nodes = [];
  const regex = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    if (m[2] !== undefined) {
      nodes.push(<strong key={`${keyPrefix}-b${i}`}>{m[2]}</strong>);
    } else if (m[3] !== undefined) {
      nodes.push(<code key={`${keyPrefix}-c${i}`}>{m[3]}</code>);
    }
    last = regex.lastIndex;
    i++;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function renderMarkdown(text) {
  const lines = String(text).split("\n");
  return lines.map((line, idx) => {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const content = bullet ? "• " + bullet[1] : line;
    return (
      <React.Fragment key={idx}>
        {parseInline(content, idx)}
        {idx < lines.length - 1 ? "\n" : null}
      </React.Fragment>
    );
  });
}
