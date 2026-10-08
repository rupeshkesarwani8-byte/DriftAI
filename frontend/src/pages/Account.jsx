import { useState } from "react";
import { CheckCircle2, KeyRound } from "lucide-react";
import { useAuth } from "../AuthContext";
import { apiChangePassword } from "../api6";
import "../insights.css";

export default function Account() {
  const { user, logout } = useAuth();
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setDone(false);
    if (next.length < 8) return setError("New password must be at least 8 characters.");
    if (next !== again) return setError("The two new passwords do not match.");
    setBusy(true);
    try {
      await apiChangePassword(cur, next);
      setDone(true);
      setCur("");
      setNext("");
      setAgain("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ins">
      <h1><KeyRound size={22} /> Account</h1>
      <div className="ins-card">
        <div className="ins-row"><span>Name</span><b>{user?.name}</b></div>
        <div className="ins-row"><span>Email</span><b>{user?.email}</b></div>
      </div>

      <form className="ins-card ins-form" onSubmit={submit}>
        <h3>Change password</h3>
        {error && <div className="ins-error">{error}</div>}
        {done && <div className="ins-ok"><CheckCircle2 size={16} /> Password changed.</div>}
        <label>Current password
          <input type="password" value={cur} onChange={(e) => setCur(e.target.value)} autoComplete="current-password" required />
        </label>
        <label>New password
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required />
        </label>
        <label>Repeat new password
          <input type="password" value={again} onChange={(e) => setAgain(e.target.value)} autoComplete="new-password" required />
        </label>
        <button className="ins-btn" disabled={busy}>{busy ? "Saving..." : "Change password"}</button>
      </form>

      <button className="ins-btn ins-ghost" onClick={logout}>Log out</button>
    </div>
  );
}