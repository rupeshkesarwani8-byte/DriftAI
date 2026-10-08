import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="pl-fallback">
      <h2>Page not found</h2>
      <p>This address does not exist in DriftAI.</p>
      <div className="pl-actions">
        <Link className="pl-btn" to="/">Go to dashboard</Link>
      </div>
    </div>
  );
}