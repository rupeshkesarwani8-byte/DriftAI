import { Suspense, lazy, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Braces, Download, Network } from "lucide-react";
import MatchList from "./MatchList";
import "../functions.css";

// React Flow is loaded only when an analysis page is opened, so the other pages stay light.
const ImpactGraph = lazy(() => import("./ImpactGraph"));

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Section shown under a saved analysis: the exact functions and constants to change. */
export default function FunctionMatches() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    setError("");
    fetch(`${BASE}/analyses/${id}/functions`)
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).detail || `Error ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id]);

  return (
    <div className="fm-section">
      <div className="fm-section-head">
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <Braces size={20} /> Functions to change
        </h2>
        <a className="fm-btn fm-btn-small" href={`${BASE}/analyses/${id}/full-report.md`} download>
          <Download size={14} style={{ verticalAlign: "-2px", marginRight: 6 }} />
          Download full report (.md)
        </a>
      </div>

      {error && <div className="fm-err">{error}</div>}
      {!data && !error && <p className="fm-meta">Reading your code...</p>}

      {data && (
        <>
          <p className="fm-meta">
            {data.units_indexed === 0
              ? "No Python or JavaScript functions were found in this project."
              : `${data.units_indexed} functions and constants were checked.`}
          </p>
          {data.changes.length > 0 && data.units_indexed > 0 && (
            <>
              <h3 className="fm-graph-title"><Network size={16} /> Impact graph</h3>
              <Suspense fallback={<p className="fm-meta">Drawing the graph...</p>}>
                <ImpactGraph changes={data.changes} />
              </Suspense>
            </>
          )}
          {data.changes.map((c, i) => (
            <MatchList key={i} change={c} />
          ))}
        </>
      )}
    </div>
  );
}