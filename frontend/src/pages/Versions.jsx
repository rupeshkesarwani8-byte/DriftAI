import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, GitCompare, Trash2, Upload } from "lucide-react";
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  async function handleDelete(v) {
    if (!window.confirm(`Delete version ${v.number}?`)) return;
    setError("");
    setMessage("");
    try {
      await call(`/projects/${projectId}/versions/${v.id}`, { method: "DELETE" });
    } catch (e) {
      setError(e.message);
    }
    await loadVersions(projectId);
  }

// fetch is patched in auth.js, so the login token is added automatically.

async function call(path, options) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = data && data.detail;
    throw new Error((Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail) || `Error ${res.status}`);
  }
  return data;
}

export default function Versions() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [versions, setVersions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadVersions = useCallback(async (id) => {
    if (!id) return setVersions([]);
    try {
      setVersions(await call(`/projects/${id}/versions`));
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const list = await call("/projects");
        setProjects(list);
        if (list.length) setProjectId(String(list[0].id));
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  useEffect(() => {
    loadVersions(projectId);
  }, [projectId, loadVersions]);

  async function handleUpload(fileList) {
    const picked = Array.from(fileList || []);
    if (!projectId || picked.length === 0) return;
    setError("");
    setMessage("");
    setBusy(true);
    let done = 0;
    try {
      // one file = one version, uploaded in the order they were picked
      for (const file of picked) {
        const form = new FormData();
        form.append("file", file);
        await call(`/projects/${projectId}/versions`, { method: "POST", body: form });
        done += 1;
      }
      setMessage(`${done} version(s) uploaded.`);
    } catch (e) {
      setError(`${e.message}${done ? ` (${done} uploaded before this error)` : ""}`);
    } finally {
      setBusy(false);
      await loadVersions(projectId);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Requirement versions</h1>
        <p>Upload your requirement document again and again. Each new version is compared with the one before it.</p>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Upload a version</h2>
        </div>

        {projects.length === 0 ? (
          <p className="muted">Create a project with your code first (Projects page).</p>
        ) : (
          <>
            <label className="field">
              Project
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (#{p.id})
                  </option>
                ))}
              </select>
            </label>

            <label className="dropzone">
              <Upload size={28} />
              <strong>{busy ? "Uploading..." : "Choose requirement file(s)"}</strong>
              <span>.txt .md .docx. Pick several to upload v1, v2, v3 in order.</span>
              <input
                type="file"
                multiple
                hidden
                accept=".txt,.md,.docx"
                disabled={busy}
                onChange={(e) => {
                  handleUpload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </>
        )}
        {message && <p className="ok">{message}</p>}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Timeline</h2>
          <span className="muted">{versions.length}</span>
        </div>
        {versions.length === 0 ? (
          <div className="empty">
            <p>No versions yet.</p>
          </div>
        ) : (
          <ul className="rows">
            {versions.map((v) => (
              <li key={v.id} className="row">
                <div>
                  <strong>
                    <FileText size={14} /> Version {v.number}
                  </strong>
                  <div className="muted small">
                    {v.filename} · {new Date(v.created_at).toLocaleString()}
                  </div>
                                    {v.summary && v.summary.length > 0 && (
                    <ul className="muted small" style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                      {v.summary.map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="row-actions">
                  {v.analysis_id ? (
                    <>
                      <span className="muted small">
                        v{v.number - 1} → v{v.number}: {v.change_count} change(s) · {v.file_count} file(s)
                      </span>
                      {v.risk_level && (
                        <span className={`risk-level ${v.risk_level}`}>
                          {v.risk_level} {v.risk_score}
                        </span>
                      )}
                    {v.id === versions[versions.length - 1].id && (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(v)}
                      aria-label="Delete latest version"
                    >
                      <Trash2 size={14} />
                    </button>
                    )}
                      <Link className="btn btn-ghost btn-sm" to={`/analysis/${v.analysis_id}`}>
                        <GitCompare size={14} /> Open
                      </Link>
                    </>
                  ) : (
                    <span className="muted small">first version (baseline)</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}