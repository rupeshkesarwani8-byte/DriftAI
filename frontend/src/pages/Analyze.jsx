import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { analyze, listProjects } from "../api";

const SAMPLE_OLD = "OTP expires in 10 minutes.\nMaximum login attempts allowed is 3.";
const SAMPLE_NEW = "OTP expires in 5 minutes.\nMaximum login attempts allowed is 5.";

export default function Analyze() {
  const location = useLocation();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(String(location.state?.projectId ?? ""));
  const [oldText, setOldText] = useState(SAMPLE_OLD);
  const [newText, setNewText] = useState(SAMPLE_NEW);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listProjects()
      .then((list) => {
        setProjects(list);
        setProjectId((current) => current || (list.length ? String(list[0].id) : ""));
      })
      .catch((e) => setError(e.message));
  }, []);

  async function handleAnalyze() {
    setError("");
    setBusy(true);
    try {
      const data = await analyze(Number(projectId), oldText, newText);
      navigate(`/analysis/${data.analysis_id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Analyze</h1>
        <p>Paste the old and the new requirement. DriftAI finds what changed and what it touches.</p>
      </div>

      <section className="card">
        {projects.length === 0 ? (
          <div className="empty">
            <p>You need a project first.</p>
            <Link className="btn btn-sm" to="/projects">
              Create a project
            </Link>
          </div>
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

            <div className="two">
              <label className="field">
                Old requirement
                <textarea value={oldText} onChange={(e) => setOldText(e.target.value)} />
              </label>
              <label className="field">
                New requirement
                <textarea value={newText} onChange={(e) => setNewText(e.target.value)} />
              </label>
            </div>

            <button className="btn" disabled={busy || !projectId} onClick={handleAnalyze}>
              {busy ? "Analyzing..." : "Analyze impact"}
            </button>
          </>
        )}
        {error && <p className="error">{error}</p>}
      </section>
    </div>
  );
}