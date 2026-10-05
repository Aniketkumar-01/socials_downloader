/**
 * API client module for interacting with the FastAPI backend.
 */

const API_BASE = ""; // Relative to server root

export async function syncAuthToken() {
  if (window.__AUTH_TOKEN__) return window.__AUTH_TOKEN__;
  try {
    const res = await fetch(`${API_BASE}/api/token`);
    if (res.ok) {
      const data = await res.json();
      if (data && data.token) {
        window.__AUTH_TOKEN__ = data.token;
        return data.token;
      }
    }
  } catch (err) {
    console.warn("Could not sync auth token:", err);
  }
  return "";
}

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

export async function startDownload({ url, isPlaylist, selectedVideoIds, quality, cookieBrowser = null, downloadDir = null }) {
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
      download_dir: downloadDir || undefined,
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

export async function openFile(taskId) {
  const response = await fetch(`${API_BASE}/api/open-file?task_id=${encodeURIComponent(taskId)}`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to open file");
  }
  return await response.json();
}

export async function getDownloadDir() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/download-dir`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to retrieve download directory");
  }
  return await response.json();
}

export async function setDownloadDir(dirPath) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/download-dir`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ download_dir: dirPath }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to update download directory");
  }
  return await response.json();
}

export async function chooseFolder() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/choose-folder`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to launch folder picker");
  }
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

