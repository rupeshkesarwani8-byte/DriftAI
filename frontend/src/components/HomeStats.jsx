import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { apiStats } from "../api6";

/** A small strip of numbers shown above the Dashboard. Stays hidden if the stats cannot be loaded. */
export default function HomeStats() {
  const [s, setS] = useState(null);

  useEffect(() => {
    apiStats().then(setS).catch(() => {});
  }, []);

  if (!s) return null;
  const items = [
    ["Projects", s.projects],
    ["Analyses", s.analyses],
    ["Changes found", s.changes_found],
    ["High risk", s.risk_levels.high],
  ];
  return (
    <div className="pl-strip">
      {items.map(([label, n]) => (
        <div className="pl-chip" key={label}>
          <b>{n}</b>
          <span>{label}</span>
        </div>
      ))}
      <Link className="pl-more" to="/insights">
        Full insights <ArrowRight size={14} />
      </Link>
    </div>
  );
}