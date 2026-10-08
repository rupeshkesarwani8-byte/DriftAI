import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, Upload, Zap } from "lucide-react";
import { createProject, deleteProject, getProject, listProjects, uploadFiles } from "../api";

export default function Projects() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [files, setFiles] = useState([]);
  const [drag, setDrag] = useState(false);
  const [projects, setProjects] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const list = await listProjects();
      setProjects(await Promise.all(list.map((p) => getProject(p.id))));
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const created = await createProject(name.trim() || "Untitled project");
      const info = await uploadFiles(created.id, files);
      const skipped = info.skipped.length ? `, ${info.skipped.length} skipped (${info.skipped.join(", ")})` : "";
      setMessage(`Project "${created.name}" created: ${info.saved.length} file(s) saved${skipped}`);
      setName("");
      setFiles([]);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(project) {
    if (!window.confirm(`Delete "${project.name}" and all its files?`)) return;
    try {
      await deleteProject(project.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Projects</h1>
        <p>Upload the code you want DriftAI to watch.</p>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>New project</h2>
        </div>

        <label className="field">
          Project name
          <input type="text" value={name} placeholder="e.g. shop-backend" onChange={(e) => setName(e.target.value)} />
        </label>

        <label
          className={`dropzone ${drag ? "drag" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            setFiles(Array.from(e.dataTransfer.files));
          }}
        >
          <Upload size={28} />
          <strong>Drop code files here</strong>
          <span>or click to browse (.py .js .jsx .ts .tsx .md .json ...)</span>
          <input type="file" multiple hidden onChange={(e) => setFiles(Array.from(e.target.files))} />
        </label>

        {files.length > 0 && (
          <div className="chips">
            {files.map((f) => (
              <span className="chip" key={f.name}>
                {f.name}
              </span>
            ))}
          </div>
        )}

        <button className="btn" disabled={busy || files.length === 0} onClick={handleCreate}>
          {busy ? "Uploading..." : "Create project"}
        </button>
        {message && <p className="ok">{message}</p>}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Your projects</h2>
          <span className="muted">{projects.length}</span>
        </div>
        {projects.length === 0 ? (
          <div className="empty">
            <p>No projects yet.</p>
          </div>
        ) : (
          <ul className="rows">
            {projects.map((p) => (
              <li key={p.id} className="row">
                <div>
                  <strong>{p.name}</strong>
                  <div className="muted small">
                    #{p.id} · {p.files.length} file(s) · {new Date(p.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="row-actions">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => navigate("/analyze", { state: { projectId: p.id } })}
                  >
                    <Zap size={14} /> Analyze
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p)} aria-label="Delete project">
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}