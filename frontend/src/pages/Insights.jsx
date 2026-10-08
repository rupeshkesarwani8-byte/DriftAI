import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, BarChart3, FileDiff, Folder, ThumbsUp, Zap } from "lucide-react";
import { apiStats } from "../api6";
import "../insights.css";

const LEVELS = [
  ["high", "High risk"],
  ["medium", "Medium risk"],
  ["low", "Low risk"],
];

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="ins-stat">
      <Icon size={18} />
      <div className="ins-num">{value}</div>
      <div className="ins-label">{label}</div>
    </div>
  );
}

export default function Insights() {
  const [s, setS] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiStats().then(setS).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="ins"><div className="ins-error">{error}</div></div>;
  if (!s) return <div className="ins"><div className="ins-muted">Loading insights...</div></div>;

  const total = s.analyses || 0;
  const judged = s.feedback.relevant + s.feedback.not_relevant;
  const helpful = judged ? Math.round((s.feedback.relevant / judged) * 100) : null;

  return (
    <div className="ins">
      <h1><BarChart3 size={22} /> Insights</h1>
      <p className="ins-muted">A summary of your own projects and analyses.</p>

      <div className="ins-grid">
        <Stat icon={Folder} label="Projects" value={s.projects} />
        <Stat icon={Zap} label="Analyses run" value={s.analyses} />
        <Stat icon={FileDiff} label="Changes found" value={s.changes_found} />
        <Stat icon={ThumbsUp} label="Matches marked useful" value={helpful === null ? "-" : `${helpful}%`} />
      </div>

      {total === 0 ? (
        <div className="ins-card ins-empty">
          <AlertTriangle size={20} />
          <div>
            No analyses yet. <Link to="/analyze">Run your first analysis</Link> and the numbers will appear here.
          </div>
        </div>
      ) : (
        <div className="ins-two">
          <div className="ins-card">
            <h3>Risk levels</h3>
            {LEVELS.map(([key, label]) => {
              const n = s.risk_levels[key] || 0;
              return (
                <div className="ins-bar-row" key={key}>
                  <span className="ins-bar-name">{label}</span>
                  <div className="ins-bar"><div className={`ins-fill ${key}`} style={{ width: `${(n / total) * 100}%` }} /></div>
                  <span className="ins-bar-n">{n}</span>
                </div>
              );
            })}
          </div>

          <div className="ins-card">
            <h3>Most analysed projects</h3>
            {s.top_projects.map((p) => (
              <div className="ins-row" key={p.id}>
                <span>{p.name}</span>
                <b>{p.analyses}</b>
              </div>
            ))}
          </div>

          <div className="ins-card ins-wide">
            <h3>Recent analyses</h3>
            {s.recent.map((a) => (
              <Link className="ins-row ins-link" key={a.id} to={`/analysis/${a.id}`}>
                <span>{a.project} <small>· {a.changes} change(s)</small></span>
                <span className={`ins-chip ${a.risk}`}>{a.risk}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}