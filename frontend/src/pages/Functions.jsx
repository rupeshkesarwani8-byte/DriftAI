import { useEffect, useState } from "react";
import { Braces } from "lucide-react";
import MatchList from "../components/MatchList";
import "../functions.css";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Functions() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [oldText, setOldText] = useState("The maximum number of redirects is 30.");
  const [newText, setNewText] = useState("The maximum number of redirects is 10.");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${BASE}/projects`)
      .then((r) => r.json())
      .then((list) => {
        setProjects(list);
        if (list.length) setProjectId(String(list[0].id));
      })
      .catch(() => setError("Cannot reach the backend. Is uvicorn running?"));
  }, []);

  async function run() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`${BASE}/projects/${projectId}/functions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_text: oldText, new_text: newText, top_k: 5 }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || `Error ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fm-wrap">
      <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Braces size={26} /> Function-level impact
      </h1>
      <p className="fm-meta">
        DriftAI reads your code with the AST and ranks the exact functions and constants a requirement
        change touches. Weak matches are hidden until you ask for them.
      </p>

      <div className="fm-card">
        <label className="fm-label">PROJECT</label>
        <select className="fm-input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} (#{p.id})
            </option>
          ))}
        </select>

        <div className="fm-grid" style={{ marginTop: 16 }}>
          <div>
            <label className="fm-label">OLD REQUIREMENT</label>
            <textarea className="fm-text" value={oldText} onChange={(e) => setOldText(e.target.value)} />
          </div>
          <div>
            <label className="fm-label">NEW REQUIREMENT</label>
            <textarea className="fm-text" value={newText} onChange={(e) => setNewText(e.target.value)} />
          </div>
        </div>

        <button className="fm-btn" disabled={busy || !projectId} onClick={run}>
          {busy ? "Analyzing..." : "Find functions"}
        </button>
        {error && <div className="fm-err">{error}</div>}
      </div>

      {result && (
        <>
          <p className="fm-meta">
            {result.units_indexed} functions/constants indexed · {result.changes.length} change(s) found
          </p>
          {result.changes.map((c, i) => (
            <MatchList key={i} change={c} />
          ))}
        </>
      )}
    </div>
  );
}