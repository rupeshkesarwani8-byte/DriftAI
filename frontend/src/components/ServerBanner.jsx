import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** Shows a red bar when the backend cannot be reached (checks /health every 15 seconds). */
export default function ServerBanner() {
  const [down, setDown] = useState(false);

  useEffect(() => {
    let alive = true;
    const ping = async () => {
      try {
        const r = await fetch(`${BASE}/health`);
        if (alive) setDown(!r.ok);
      } catch {
        if (alive) setDown(true);
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (!down) return null;
  return (
    <div className="pl-banner" role="alert">
      <WifiOff size={16} /> Cannot reach the server. Please check that the backend is running.
    </div>
  );
}