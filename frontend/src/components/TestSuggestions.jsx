import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import "../patches.css";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** One pytest command for the Python tests of a change (other languages are listed but not turned into a command). */
function commandFor(change) {
  const ids = change.tests.map((t) => t.pytest).filter(Boolean);
  return ids.length ? `pytest ${ids.join(" ")} -q` : "";
}

/** Tests that probably need a look for each change. DriftAI only reads code; it never runs your tests. */
export default function TestSuggestions({ id }) {
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState(-1);

  useEffect(() => {
    setData(null);
    fetch(`${BASE}/analyses/${id}/tests`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setData)
      .catch(() => setData({ changes: [] }));
  }, [id]);

  const copy = async (text, i) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(-1), 1800);
    } catch {
      /* clipboard can be blocked; the command is still on screen */
    }
  };

  if (!data || data.changes.length === 0) return null;

  return (
    <div className="ps-section">
      <h2>Tests to run</h2>
      <p className="ps-note">
        Tests found by name and by use of the matched code. DriftAI only reads your code and never runs it.
        Paths are relative to your project: adjust them if you run pytest from another folder.
      </p>
      {data.changes.map((c, i) => {
        const cmd = commandFor(c);
        return (
          <div className="ps-change" key={i}>
            <div className="ps-head">
              <span className="ps-title">{c.entity} · {c.property}</span>
              <span className="ps-pill">{c.old_value} → {c.new_value}</span>
              {cmd && (
                <button className="ps-copy" onClick={() => copy(cmd, i)}>
                  {copied === i ? <Check size={14} /> : <Copy size={14} />}
                  {copied === i ? "Copied" : "Copy pytest command"}
                </button>
              )}
            </div>
            {c.tests.map((t, k) => (
              <div className="ps-test" key={k}>
                <code>{t.qualname}</code>
                <span className="ps-where">{t.path}:{t.start_line}</span>
                <span className="ps-why">{t.reason}</span>
              </div>
            ))}
            {c.note && <p className="ps-small">{c.note}</p>}
            {cmd && <div className="ps-cmd">{cmd}</div>}
          </div>
        );
      })}
    </div>
  );
}