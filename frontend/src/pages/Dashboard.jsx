import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Files, Folder, GitCompare } from "lucide-react";
import { getProject, listAnalyses, listProjects } from "../api";
import Stat from "../components/Stat";

export default function Dashboard() {
  const [projectCount, setProjectCount] = useState(0);
  const [fileCount, setFileCount] = useState(0);
  const [analyses, setAnalyses] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [list, recent] = await Promise.all([listProjects(), listAnalyses(100)]);
        const details = await Promise.all(list.map((p) => getProject(p.id)));
        if (!alive) return;
        setProjectCount(list.length);
        setFileCount(details.reduce((sum, d) => sum + d.files.length, 0));
        setAnalyses(recent);
      } catch {
        if (alive) setError("Cannot reach the backend. Is it running on port 8000?");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const totalChanges = analyses.reduce((sum, a) => sum + a.change_count, 0);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Dashboard</h1>
        <p>Your requirement drift overview at a glance.</p>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="grid-stats">
        <Stat icon={Folder} value={projectCount} label="Projects" />
        <Stat icon={Files} value={fileCount} label="Files indexed" />
        <Stat icon={Activity} value={analyses.length} label="Analyses run" />
        <Stat icon={GitCompare} value={totalChanges} label="Changes detected" />
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Recent analyses</h2>
          <Link className="btn btn-ghost btn-sm" to="/analyze">
            New analysis
          </Link>
        </div>
        {analyses.length === 0 ? (
          <div className="empty">
            <p>No analyses yet.</p>
            <span className="muted">
              Create a project, upload your code, then paste an old and a new requirement.
            </span>
          </div>
        ) : (
          <ul className="rows">
            {analyses.slice(0, 6).map((a) => (
              <li key={a.id} className="row">
                <div>
                  <strong>
                    #{a.id} · {a.project_name}
                  </strong>
                  <div className="muted small">
                    {new Date(a.created_at).toLocaleString()} · {a.change_count} change(s) · {a.file_count} file(s)
                  </div>
                </div>
                <Link className="btn btn-ghost btn-sm" to={`/analysis/${a.id}`}>
                  View
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}