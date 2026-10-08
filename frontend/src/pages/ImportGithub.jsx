import { useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch } from "lucide-react";
import "../functions.css";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const EXAMPLES = ["https://github.com/psf/requests", "https://github.com/pallets/click"];

export default function ImportGithub() {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [exists, setExists] = useState(false); // true when the server says this project already exists
  const [done, setDone] = useState(null);

  async function run(replace = false) {
    setBusy(true);
    setError("");
    setExists(false);
    setDone(null);
    try {
      const res = await fetch(`${BASE}/import/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), name: name.trim() || null, replace }),
      });
      const data = await res.json();
      if (res.status === 409) {
        setExists(true);
        setError(data.detail);
        return;
      }
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      setDone(data);
    } catch (e) {
      setError(e.message === "Failed to fetch" ? "Cannot reach the backend. Is uvicorn running?" : e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fm-wrap">
      <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <GitBranch size={26} /> Import from GitHub
      </h1>
      <p className="fm-meta">
        Paste a public repository link. DriftAI downloads the source files and creates a project for you.
        Private repositories are not supported yet.
      </p>

      <div className="fm-card">
        <label className="fm-label">REPOSITORY LINK</label>
        <input
          className="fm-input"
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && url.trim() && !busy && run(false)}
        />
        <div className="fm-row" style={{ marginTop: 10 }}>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="fm-pill"
              style={{ cursor: "pointer", background: "transparent", color: "inherit" }}
              onClick={() => setUrl(ex)}
            >
              {ex.replace("https://github.com/", "")}
            </button>
          ))}
        </div>

        <label className="fm-label" style={{ marginTop: 16 }}>PROJECT NAME (OPTIONAL)</label>
        <input
          className="fm-input"
          placeholder="Leave empty to use owner/repo"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <button className="fm-btn" disabled={busy || !url.trim()} onClick={() => run(false)}>
          {busy ? "Importing... (can take up to a minute)" : "Import repository"}
        </button>

        {error && <div className={exists ? "fm-warn" : "fm-err"}>{error}</div>}
        {exists && (
          <button className="fm-btn" disabled={busy} onClick={() => run(true)}>
            Replace files in the existing project
          </button>
        )}
      </div>

      {done && (
        <div className="fm-card">
          <h3 style={{ marginTop: 0 }}>
            {done.replaced ? "Updated" : "Imported"} {done.repo}
          </h3>
          <p className="fm-meta">
            Project #{done.project_id} "{done.name}" now has <b>{done.files_imported}</b> files.
            {done.replaced && " Your saved analyses for this project were kept."}
          </p>
          <div className="fm-row" style={{ marginBottom: 12 }}>
            {Object.entries(done.skipped)
              .filter(([, n]) => n > 0)
              .map(([k, n]) => (
                <span className="fm-pill" key={k}>
                  skipped {k.replace(/_/g, " ")}: {n}
                </span>
              ))}
          </div>
          {done.notes.map((n, i) => (
            <p className="fm-meta" key={i}>{n}</p>
          ))}
          <div className="fm-row">
            <Link to="/analyze" className="fm-btn" style={{ textDecoration: "none", display: "inline-block" }}>
              Analyze a requirement
            </Link>
            <Link to="/functions" className="fm-btn" style={{ textDecoration: "none", display: "inline-block" }}>
              Find functions
            </Link>
          </div>
          <p className="fm-meta" style={{ marginTop: 12 }}>
            On the next page choose the project "{done.name}" from the dropdown.
          </p>
        </div>
      )}
    </div>
  );
}