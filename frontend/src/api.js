const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

// ---- Projects ----
export const listProjects = () => request("/projects");

export const getProject = (id) => request(`/projects/${id}`);

export const deleteProject = (id) => request(`/projects/${id}`, { method: "DELETE" });

export function createProject(name) {
  return request("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function uploadFiles(projectId, fileList) {
  const form = new FormData();
  for (const file of fileList) {
    form.append("files", file);
  }
  return request(`/projects/${projectId}/files`, { method: "POST", body: form });
}

// ---- Analyses ----
export function analyze(projectId, oldText, newText) {
  return request(`/projects/${projectId}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_text: oldText, new_text: newText }),
  });
}

export const listAnalyses = (limit = 20) => request(`/analyses?limit=${limit}`);

export const getAnalysis = (id) => request(`/analyses/${id}`);

export const deleteAnalysis = (id) => request(`/analyses/${id}`, { method: "DELETE" });

export const exportUrl = (id) => `${API}/analyses/${id}/export.md`;

export async function exportMarkdown(id) {
  const res = await fetch(exportUrl(id));
  if (!res.ok) throw new Error(`Error ${res.status}`);
  return res.text();
}

export function sendFeedback(analysisId, itemKey, verdict) {
  return request(`/analyses/${analysisId}/feedback`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_key: itemKey, verdict }),
  });
}