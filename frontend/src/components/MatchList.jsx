import { useState } from "react";

/** One change with its function-level matches. Weak matches stay hidden until asked for. */
export default function MatchList({ change }) {
  const [showWeak, setShowWeak] = useState(false);
  const weak = change.weak_matches || [];

  return (
    <div className="fm-card">
      <div className="fm-change-head">
        <h3>
          {change.entity} · {change.property}
        </h3>
        <span className="fm-pill">
          {change.old_value} → {change.new_value}
        </span>
      </div>

      {change.matches.length === 0 && (
        <div className="fm-empty">
          No strong match found. This requirement may not be implemented in the code yet.
        </div>
      )}

      {change.matches.map((m, j) => (
        <Match key={`s${j}`} m={m} delay={j * 60} />
      ))}

      {weak.length > 0 && (
        <button type="button" className="fm-link" onClick={() => setShowWeak((v) => !v)}>
          {showWeak ? "Hide" : "Show"} {weak.length} weak match{weak.length > 1 ? "es" : ""}
        </button>
      )}
      {showWeak && weak.map((m, j) => <Match key={`w${j}`} m={m} delay={j * 40} />)}
    </div>
  );
}

function Match({ m, delay }) {
  return (
    <div className="fm-match" style={{ animationDelay: `${delay}ms` }}>
      <div className="fm-row">
        <span className="fm-name">{m.qualname}</span>
        <span className="fm-badge fm-kind">{m.kind}</span>
        <span className={`fm-badge fm-${m.confidence}`}>{m.confidence}</span>
        <span className="fm-loc">
          {m.path}:{m.start_line}-{m.end_line}
        </span>
        <span className="fm-score">score {m.score}</span>
      </div>
      <ul className="fm-why">
        {m.reasons.map((r, k) => (
          <li key={k}>{r}</li>
        ))}
      </ul>
      <pre className="fm-code">{m.snippet}</pre>
    </div>
  );
}