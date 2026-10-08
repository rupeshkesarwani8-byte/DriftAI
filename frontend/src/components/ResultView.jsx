import { useState } from "react";
import { FileCode2, GitCompare, ListChecks, ThumbsDown, ThumbsUp } from "lucide-react";
import { sendFeedback } from "../api";
import Stat from "./Stat";
import "../result.css";

const TYPE_LABELS = {
  value_change: "value change",
  added: "added",
  removed: "removed",
  modified: "modified",
};

function changeSummary(c) {
  if (c.type === "value_change") return `${c.old_value ?? "-"} → ${c.new_value ?? "-"}`;
  if (c.type === "added") return c.new_sentence;
  if (c.type === "removed") return c.old_sentence;
  return `${c.old_sentence} → ${c.new_sentence}`;
}

export default function ResultView({ result, analysisId, initialFeedback = {} }) {
  const [done, setDone] = useState({});
  const [feedback, setFeedback] = useState(initialFeedback);
  const [feedbackError, setFeedbackError] = useState("");

  const risk = result.risk;
  const total = result.action_plan.length;
  const completed = result.action_plan.filter((i) => done[i.order]).length;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  async function vote(item, verdict) {
    if (!analysisId || !item.key) return;
    const next = feedback[item.key] === verdict ? "none" : verdict;
    const previous = feedback;
    setFeedback({ ...feedback, [item.key]: next });
    try {
      await sendFeedback(analysisId, item.key, next);
      setFeedbackError("");
    } catch (e) {
      setFeedback(previous);
      setFeedbackError(e.message);
    }
  }

  return (
    <div className="result">
      <div className="grid-stats three">
        <Stat icon={GitCompare} value={result.changes.length} label="Requirement changes" />
        <Stat icon={FileCode2} value={result.total_files} label="Files affected" />
        <Stat icon={ListChecks} value={total} label="Action items" />
      </div>

      {risk && (
        <section className="card risk-card">
          <div className={`risk-ring ${risk.level}`} style={{ "--pct": `${risk.score}%` }}>
            <div className="risk-inner">
              <strong>{risk.score}</strong>
              <span>/ 100</span>
            </div>
          </div>
          <div>
            <h2>
              Risk: <span className={`risk-level ${risk.level}`}>{risk.level}</span>
            </h2>
            <ul className="reasons">
              {risk.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            <p className="muted small">
              Risk shows how serious this change could be. Confidence on each action shows how sure DriftAI is
              about the match.
            </p>
          </div>
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h2>What changed</h2>
        </div>
        {result.changes.length === 0 ? (
          <p className="muted">No requirement changes found.</p>
        ) : (
          <ul className="list">
            {result.changes.map((r, i) => (
              <li key={i}>
                <span className={`badge ${r.change.type}`}>{TYPE_LABELS[r.change.type] ?? r.change.type}</span>
                <strong>{r.change.entity}</strong>
                <span className="muted">· {r.change.property}</span>
                <span className="change-value">{changeSummary(r.change)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Action plan</h2>
          <span className="muted">
            {completed}/{total} done
          </span>
        </div>
        {total > 0 && (
          <div className="progress">
            <div className="progress-bar" style={{ width: `${percent}%` }} />
          </div>
        )}
        {feedbackError && <p className="error">{feedbackError}</p>}
        {total === 0 ? (
          <p className="muted">No actions needed.</p>
        ) : (
          <ul className="plan">
            {result.action_plan.map((item) => (
              <li key={item.order} className={done[item.order] ? "done" : ""}>
                <div className="plan-row">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={!!done[item.order]}
                      onChange={() => setDone({ ...done, [item.order]: !done[item.order] })}
                    />
                    <span>
                      {item.text}
                      {item.confidence && <em className={`conf ${item.confidence}`}>{item.confidence}</em>}
                    </span>
                  </label>
                  {item.key && analysisId && (
                    <div className="feedback">
                      <button
                        className={`fb-btn good ${feedback[item.key] === "relevant" ? "active" : ""}`}
                        onClick={() => vote(item, "relevant")}
                        aria-label="Mark as relevant"
                        title="Relevant"
                      >
                        <ThumbsUp size={14} />
                      </button>
                      <button
                        className={`fb-btn bad ${feedback[item.key] === "not_relevant" ? "active" : ""}`}
                        onClick={() => vote(item, "not_relevant")}
                        aria-label="Mark as not relevant"
                        title="Not relevant"
                      >
                        <ThumbsDown size={14} />
                      </button>
                    </div>
                  )}
                </div>
                {item.reason && <div className="reason">{item.reason}</div>}
                {item.evidence && <code className="evidence">{item.evidence}</code>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Affected files and evidence</h2>
        </div>
        {result.total_files === 0 && <p className="muted">No matching files found.</p>}
        {result.changes.map(
          (r, i) =>
            r.files.length > 0 && (
              <div key={i}>
                <h3 className="sub-head">
                  {r.change.entity} · {r.change.property}
                </h3>
                {r.files.map((f) => (
                  <details key={f.path}>
                    <summary>
                      {f.path} <span className="tag">{f.kind}</span>
                      <span className="muted"> score {f.score}</span>
                    </summary>
                    <ul>
                      {f.evidence.map((e) => (
                        <li key={e.line}>
                          line {e.line}
                          {e.function && ` · ${e.function}()`}: <code>{e.text}</code>
                          {e.literal && <em> · found: {e.literal}</em>}
                        </li>
                      ))}
                    </ul>
                  </details>
                ))}
              </div>
            )
        )}
      </section>
    </div>
  );
}