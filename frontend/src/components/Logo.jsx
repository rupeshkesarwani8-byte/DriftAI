import { useId } from "react";

/** DriftAI mark: a "D" with speed lines and a drift arrow. Pure SVG, so it stays sharp at any size. */
export function LogoMark({ size = 32 }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="DriftAI" className="logo-mark">
      <defs>
        <linearGradient id={`g${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff4d5a" />
          <stop offset="1" stopColor="#c8101f" />
        </linearGradient>
      </defs>
      {/* speed lines */}
      <rect x="1" y="17" width="10" height="3" rx="1.5" fill="#ff4d5a" opacity=".95" />
      <rect x="4" y="23" width="9" height="3" rx="1.5" fill="#ff4d5a" opacity=".7" />
      <rect x="2" y="29" width="7" height="3" rx="1.5" fill="#ff4d5a" opacity=".45" />
      {/* the D */}
      <path d="M14 8h13c9 0 15 6 15 16s-6 16-15 16H14l5-8h7c4.5 0 7-3 7-8s-2.5-8-7-8h-7z" fill={`url(#g${id})`} />
      {/* drift arrow inside the D */}
      <path d="M20 24l13-7-4 7 4 7z" fill="#ffe3e5" />
    </svg>
  );
}

export default function Logo({ size = 44, tagline = true }) {
  return (
    <span className="logo">
      <LogoMark size={size} />
      <span className="logo-words">
        <span className="logo-text">
          Drift<b>AI</b>
        </span>
        {tagline && <span className="logo-tag">Detect · Analyse · Act</span>}
      </span>
    </span>
  );
}