import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, Copy, Download, Trash2 } from "lucide-react";
import { deleteAnalysis, exportMarkdown, exportUrl, getAnalysis } from "../api";
import ResultView from "../components/ResultView";
import "../analysis.css";

export default function AnalysisDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getAnalysis(id)
      .then(setAnalysis)
      .catch((e) => setError(e.message));
  }, [id]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(await exportMarkdown(id));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this analysis?")) return;
    try {
      await deleteAnalysis(id);
      navigate("/");
    } catch (e) {
      setError(e.message);
    }
  }

  if (!analysis) {
    return (
      <div className="page">
        <div className="page-head">
          <h1>Analysis #{id}</h1>
          <p>{error ? "" : "Loading..."}</p>
        </div>
        {error && (
          <>
            <p className="error">{error}</p>
            <Link className="btn btn-ghost btn-sm" to="/">
              Back to dashboard
            </Link>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Analysis #{analysis.id}</h1>
        <p>
          {analysis.project_name} · {new Date(analysis.created_at).toLocaleString()}
        </p>
      </div>

      <div className="actions">
        <a className="btn btn-ghost btn-sm" href={exportUrl(analysis.id)}>
          <Download size={14} /> Download .md
        </a>
        <button className="btn btn-ghost btn-sm" onClick={handleCopy}>
          {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy checklist"}
        </button>
        <button className="btn btn-danger btn-sm" onClick={handleDelete}>
          <Trash2 size={14} /> Delete
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <section className="card">
        <div className="card-head">
          <h2>Requirements compared</h2>
        </div>
        <div className="req-grid">
          <div>
            <span className="req-label">Old</span>
            <pre className="req-text">{analysis.old_text}</pre>
          </div>
          <div>
            <span className="req-label">New</span>
            <pre className="req-text">{analysis.new_text}</pre>
          </div>
        </div>
      </section>

      <ResultView
        key={analysis.id}
        result={analysis}
        analysisId={analysis.id}
        initialFeedback={analysis.feedback}
      />
    </div>
  );
}