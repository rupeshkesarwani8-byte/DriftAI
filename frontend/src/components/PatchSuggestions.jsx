import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import "../patches.css";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Turns the edits of one change into plain text that can be pasted into a chat, ticket or commit message. */
function asText(change) {
  const lines = [`${change.entity} · ${change.property}: ${change.old_value} -> ${change.new_value}`];
  change.edits.forEach((e) => {
    lines.push(`${e.path}:${e.line}`, `- ${e.before}`, `+ ${e.after}`);
  });
  return lines.join("\n");
}

/** Suggested edits under a saved analysis. DriftAI never changes files; a person reviews every line. */
export default function PatchSuggestions({ id }) {
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState(-1);

  useEffect(() => {
    setData(null);
    fetch(`${BASE}/analyses/${id}/patches`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setData)
      .catch(() => setData({ changes: [] }));
  }, [id]);

  const copy = async (change, i) => {
    try {
      await navigator.clipboard.writeText(asText(change));
      setCopied(i);
      setTimeout(() => setCopied(-1), 1800);
    } catch {
      /* clipboard can be blocked; the text is still on screen */
    }
  };

  if (!data || data.changes.length === 0) return null;

  return (
    <div className="ps-section">
      <h2>Suggested edits</h2>
      <p className="ps-note">
        DriftAI never changes your files. These are suggestions: check each line before you edit.
      </p>
      {data.changes.map((c, i) => (
        <div className="ps-change" key={i}>
          <div className="ps-head">
            <span className="ps-title">{c.entity} · {c.property}</span>
            <span className="ps-pill">{c.old_value} → {c.new_value}</span>
            {c.edits.length > 0 && (
              <button className="ps-copy" onClick={() => copy(c, i)}>
                {copied === i ? <Check size={14} /> : <Copy size={14} />}
                {copied === i ? "Copied" : "Copy as text"}
              </button>
            )}
          </div>
          {c.edits.length === 0 && <p className="ps-small">{c.note}</p>}
          {c.edits.map((e, k) => (
            <div className="ps-edit" key={k}>
              <div className="ps-where">
                <span>{e.path}:{e.line}</span>
                <span>{e.qualname}</span>
                <span>{e.confidence}</span>
                {e.kind === "text" && <span>comment or text</span>}
              </div>
              <div className="ps-diff">
                <div className="ps-del">- {e.before}</div>
                <div className="ps-add">+ {e.after}</div>
              </div>
              {e.note && <p className="ps-small">{e.note}</p>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}