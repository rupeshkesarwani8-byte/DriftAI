import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { useAuth } from "../AuthContext";
import "../auth.css";

/** One component for both screens: mode="login" or mode="signup". */
export default function Auth({ mode }) {
  const isSignup = mode === "signup";
  const { user, login, signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      if (isSignup) await signup(name.trim(), email.trim(), password);
      else await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="au">
      <div className="au-orb au-orb-a" />
      <div className="au-orb au-orb-b" />
      <div className="au-card">
        <Link to="/welcome" className="au-brand">
          <span className="au-mark" />
          <span>Drift<b>AI</b></span>
        </Link>
        <h1>{isSignup ? "Create your account" : "Welcome back"}</h1>
        <p className="au-sub">
          {isSignup ? "Start catching requirement drift in minutes." : "Log in to continue to your projects."}
        </p>

        <form onSubmit={submit} noValidate>
          {isSignup && (
            <label className="au-field">
              <span>Name</span>
              <div className="au-input">
                <User size={16} />
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoComplete="name" required />
              </div>
            </label>
          )}
          <label className="au-field">
            <span>Email</span>
            <div className="au-input">
              <Mail size={16} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>
          </label>
          <label className="au-field">
            <span>Password</span>
            <div className="au-input">
              <Lock size={16} />
              <input
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isSignup ? "At least 8 characters" : "Your password"}
                autoComplete={isSignup ? "new-password" : "current-password"}
                required
              />
              <button type="button" className="au-eye" onClick={() => setShow(!show)} aria-label="Show or hide password">
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          {error && <div className="au-error">{error}</div>}

          <button className="au-btn" disabled={busy || !email || !password || (isSignup && !name)}>
            {busy ? "Please wait..." : isSignup ? "Create account" : "Log in"}
          </button>
        </form>

        <p className="au-switch">
          {isSignup ? (
            <>
              Already have an account? <Link to="/login">Log in</Link>
            </>
          ) : (
            <>
              New to DriftAI? <Link to="/signup">Create an account</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}