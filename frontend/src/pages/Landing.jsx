import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Braces, GitBranch, ListChecks, ShieldAlert, Target, Zap } from "lucide-react";
import { useAuth } from "../AuthContext";
import "../landing.css";

/** Adds the class "in" to an element when it scrolls into view (CSS does the animation). */
function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const items = root.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      items.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        }),
      { threshold: 0.15, root }
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return ref;
}

const FEATURES = [
  {
    icon: ShieldAlert,
    title: "Drift detection",
    text: "Compare the old and new version of a requirement. DriftAI finds what really changed: numbers, units, rules and removed or added conditions.",
  },
  {
    icon: Target,
    title: "Impact analysis",
    text: "See which files and which exact functions or constants in your code are affected, ranked by confidence, with the evidence shown.",
  },
  {
    icon: ListChecks,
    title: "Evidence-backed action plan",
    text: "Get a prioritised to-do list with a risk score. Every step points to the line of code that justifies it. Export it as Markdown.",
  },
];

const STEPS = [
  ["Add your code", "Upload files or paste a GitHub repository link."],
  ["Paste the requirements", "The old and the new version of the document or sentence."],
  ["Run the analysis", "Changes, impact, risk and a plan appear in seconds."],
  ["Fix with confidence", "Open the listed functions, then give feedback to improve results."],
];

export default function Landing() {
  const { user } = useAuth();
  const ref = useReveal();
  const cta = user ? { to: "/", label: "Open dashboard" } : { to: "/signup", label: "Get started free" };

  return (
    <div className="lp" ref={ref}>
      <div className="lp-grid" />
      <div className="lp-orb lp-orb-a" />
      <div className="lp-orb lp-orb-b" />

      <header className="lp-nav">
        <div className="lp-brand">
          <span className="lp-mark" />
          <span className="lp-word">Drift<b>AI</b></span>
        </div>
        <nav>
          {user ? (
            <Link className="lp-link" to="/">Dashboard</Link>
          ) : (
            <>
              <Link className="lp-link" to="/login">Log in</Link>
              <Link className="lp-pill" to="/signup">Sign up</Link>
            </>
          )}
        </nav>
      </header>

      <section className="lp-hero">
        <div className="lp-hero-text">
          <span className="lp-badge"><Zap size={14} /> Requirement drift, caught early</span>
          <h1>
            Requirements change.
            <br />
            <em>Know exactly what breaks.</em>
          </h1>
          <p>
            DriftAI compares two versions of a requirement, finds what changed, and points to the exact functions in
            your codebase that must change, with a risk score and an action plan.
          </p>
          <div className="lp-cta">
            <Link className="lp-btn" to={cta.to}>
              {cta.label} <ArrowRight size={16} />
            </Link>
            {!user && (
              <Link className="lp-btn lp-btn-ghost" to="/login">
                I already have an account
              </Link>
            )}
          </div>
        </div>

        <div className="lp-demo" aria-hidden="true">
          <div className="lp-demo-head"><span /><span /><span /> analysis #12</div>
          <div className="lp-demo-body">
            <div className="lp-diff">
              <div className="lp-old">The maximum number of redirects is <b>30</b>.</div>
              <div className="lp-new">The maximum number of redirects is <b>10</b>.</div>
            </div>
            <div className="lp-demo-title"><Braces size={14} /> Functions to change</div>
            <div className="lp-match" style={{ "--d": "0.5s" }}>
              <code>models.py::DEFAULT_REDIRECT_LIMIT</code>
              <span className="chip chip-high">HIGH</span>
            </div>
            <div className="lp-match" style={{ "--d": "0.9s" }}>
              <code>sessions.py::resolve_redirects</code>
              <span className="chip chip-med">MEDIUM</span>
            </div>
            <div className="lp-match" style={{ "--d": "1.3s" }}>
              <code>sessions.py::Session.__init__</code>
              <span className="chip chip-low">LOW</span>
            </div>
            <div className="lp-risk"><span>Risk</span><div><i /></div><b>72</b></div>
          </div>
        </div>
      </section>

      <section className="lp-section">
        <h2 className="reveal">Three things, done properly</h2>
        <div className="lp-cards">
          {FEATURES.map(({ icon: Icon, title, text }, i) => (
            <div key={title} className="lp-card reveal" style={{ "--d": `${i * 0.12}s` }}>
              <div className="lp-ico"><Icon size={22} /></div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section">
        <h2 className="reveal">How it works</h2>
        <div className="lp-steps">
          {STEPS.map(([title, text], i) => (
            <div key={title} className="lp-step reveal" style={{ "--d": `${i * 0.1}s` }}>
              <span className="lp-num">{i + 1}</span>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section lp-honest reveal">
        <GitBranch size={20} />
        <p>
          Built with a React front end and a FastAPI back end. Function matching is based on Python's AST and is
          checked by an included benchmark on a real open-source repository.
        </p>
      </section>

      <section className="lp-final reveal">
        <h2>Stop discovering drift in production.</h2>
        <Link className="lp-btn" to={cta.to}>
          {cta.label} <ArrowRight size={16} />
        </Link>
      </section>

      <footer className="lp-foot">DriftAI · requirement drift detection · v0.4</footer>
    </div>
  );
}