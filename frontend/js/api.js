/**
 * API client module for interacting with the FastAPI backend.
 */

const API_BASE = ""; // Relative to server root

function getAuthHeaders(extra = {}) {
  const headers = { ...extra };
  if (window.__AUTH_TOKEN__) {
    headers["X-Auth-Token"] = window.__AUTH_TOKEN__;
  }
  return headers;
}

export async function fetchMediaInfo(url, cookieBrowser = null) {
  const response = await fetch(`${API_BASE}/api/info`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      url,
      cookie_browser: cookieBrowser === "none" ? "none" : (cookieBrowser || "none"),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let msg = errorData.message || errorData.detail || `Server error (${response.status})`;
    if (errorData.hint) {
      msg = `${msg} (Hint: ${errorData.hint})`;
    }
    throw new Error(msg);
  }

  return await response.json();
}

export async function startDownload({ url, isPlaylist, selectedVideoIds, quality, cookieBrowser = null }) {
  const response = await fetch(`${API_BASE}/api/download`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      url,
      is_playlist: isPlaylist,
      selected_video_ids: selectedVideoIds,
      quality,
      cookie_browser: cookieBrowser === "none" ? "none" : (cookieBrowser || "none"),
      save_to_local_folder: true,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let msg = errorData.message || errorData.detail || `Download request failed (${response.status})`;
    if (errorData.hint) {
      msg = `${msg} (Hint: ${errorData.hint})`;
    }
    throw new Error(msg);
  }

  return await response.json();
}

export async function cancelTask(taskId) {
  const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.detail || "Failed to cancel task");
  }
  return await response.json();
}

export async function openDownloadsFolder(taskId = null) {
  const url = taskId 
    ? `${API_BASE}/api/open-folder?task_id=${encodeURIComponent(taskId)}`
    : `${API_BASE}/api/open-folder`;

  const response = await fetch(url, { 
    method: "POST",
    headers: getAuthHeaders(),
  });
  return await response.json();
}

export function getDownloadFileUrl(taskId) {
  const token = window.__AUTH_TOKEN__ ? `?token=${encodeURIComponent(window.__AUTH_TOKEN__)}` : "";
  return `${API_BASE}/api/file/${taskId}${token}`;
}

export async function checkCookiesStatus() {
  const response = await fetch(`${API_BASE}/api/cookies-status`, {
    headers: getAuthHeaders(),
  });
  return await response.json();
}

export async function uploadCookiesFile(file) {
  const response = await fetch(`${API_BASE}/api/upload-cookies`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "text/plain",
    }),
    body: file,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.detail || "Failed to upload cookies file");
  }
  return await response.json();
}

export async function deleteCookiesFile() {
  const response = await fetch(`${API_BASE}/api/cookies`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return await response.json();
}

