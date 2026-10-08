const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const KEY = "driftai_token";

export function getToken() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(KEY, token);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage blocked: the user simply has to log in again next time */
  }
}

/* ------------------------------------------------------------------------------------------------
   Build 5c: send the login token with every request to our own API, so no page has to do it.
   - fetch(...)            : the Authorization header is added automatically
   - download links (<a>)  : links that point to our API (e.g. the .md reports) are fetched with the
                             token and saved as a file, because a plain link cannot send a header
   - 401 from the API      : an event is fired and AuthContext logs the user out
   /auth/* (login, signup) and /health stay untouched.
------------------------------------------------------------------------------------------------ */
export const UNAUTHORIZED_EVENT = "driftai:unauthorized";
const isPublic = (url) => url.startsWith(`${BASE}/auth/`) || url === `${BASE}/health`;

function urlOf(input) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input && input.url ? input.url : "";
}

export function installApiAuth() {
  if (typeof window === "undefined" || window.__driftaiAuthInstalled) return;
  window.__driftaiAuthInstalled = true;

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = urlOf(input);
    const token = getToken();
    if (!token || !url.startsWith(`${BASE}/`) || isPublic(url)) return realFetch(input, init);

    const headers = new Headers(init.headers || (typeof input === "object" && input.headers) || undefined);
    if (!headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
    const res = await realFetch(input, { ...init, headers });
    if (res.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    return res;
  };

  document.addEventListener("click", async (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || !a.href.startsWith(`${BASE}/`) || isPublic(a.href) || !getToken()) return;
    e.preventDefault();
    try {
      const res = await window.fetch(a.href);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const blob = await res.blob();
      const header = res.headers.get("Content-Disposition") || "";
      const match = /filename="?([^";]+)"?/.exec(header);
      const fallback = a.href.split("?")[0].split("/").filter(Boolean).slice(-2).join("-");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = match ? match[1] : fallback || "driftai-download";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 3000);
    } catch (err) {
      window.alert(`Download failed: ${err.message}`);
    }
  });
}

installApiAuth();

async function call(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = data && data.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail;
    const err = new Error(message || `Error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const apiSignup = (name, email, password) => call("/auth/signup", json({ name, email, password }));
export const apiLogin = (email, password) => call("/auth/login", json({ email, password }));
export const apiMe = (token) => call("/auth/me", { headers: { Authorization: `Bearer ${token}` } });