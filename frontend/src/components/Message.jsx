import Citations from "./Citations.jsx";
import { renderMarkdown } from "../markdown.jsx";

export default function Message({ role, text, citations, error, streaming }) {
  const showTyping = streaming && !text;
  return (
    <div className={"msg " + role}>
      <div className="role">{role === "user" ? "You" : "Assistant"}</div>
      <div className={"bubble" + (error ? " error" : "")}>
        {showTyping ? (
          <span className="typing">
            <span></span>
            <span></span>
            <span></span>
          </span>
        ) : (
          <>
            {renderMarkdown(text || "")}
            {streaming ? <span className="caret" /> : null}
          </>
        )}
      </div>
      {citations ? <Citations data={citations} /> : null}
    </div>
  );
}
