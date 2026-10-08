// Build 6 API calls. For normal routes the token is added automatically by installApiAuth() (auth.js).
// /auth/* is skipped by that patch (login/signup must not send a token), so /auth/password adds it itself.
import { getToken } from "./auth";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options) {
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
    const d = data && data.detail;
    throw new Error((Array.isArray(d) ? d.map((x) => x.msg).join(", ") : d) || `Error ${res.status}`);
  }
  return data;
}

export const apiStats = () => request("/stats");

export const apiChangePassword = (current_password, new_password) =>
  request("/auth/password", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() || ""}` },
    body: JSON.stringify({ current_password, new_password }),
  });