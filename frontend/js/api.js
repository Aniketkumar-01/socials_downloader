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
  await syncAuthToken();
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
    const err = new Error(msg);
    err.code = errorData.code || "UNKNOWN";
    err.hint = errorData.hint || "";
    err.source = errorData.source || "platform";
    err.raw = errorData;
    throw err;
  }

  return await response.json();
}

export async function fetchBatchMediaInfo(urls, cookieBrowser = null) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/batch/info`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      urls,
      cookie_browser: cookieBrowser === "none" ? "none" : (cookieBrowser || "none"),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let msg = errorData.message || errorData.detail || `Batch request failed (${response.status})`;
    const err = new Error(msg);
    err.code = errorData.code || "UNKNOWN";
    err.hint = errorData.hint || "";
    err.source = errorData.source || "platform";
    err.raw = errorData;
    throw err;
  }

  return await response.json();
}

export async function startDownload({ url, urls = null, isPlaylist, selectedVideoIds, batchItems = null, playlistTitle = null, quality, cookieBrowser = null, downloadDir = null }) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/download`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      url,
      urls: urls || undefined,
      is_playlist: isPlaylist,
      selected_video_ids: selectedVideoIds,
      batch_items: batchItems || undefined,
      playlist_title: playlistTitle || undefined,
      quality,
      cookie_browser: cookieBrowser === "none" ? "none" : (cookieBrowser || "none"),
      save_to_local_folder: true,
      download_dir: downloadDir || undefined,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let msg = errorData.message || errorData.detail || `Download request failed (${response.status})`;
    const err = new Error(msg);
    err.code = errorData.code || "UNKNOWN";
    err.hint = errorData.hint || "";
    err.source = errorData.source || "platform";
    err.raw = errorData;
    throw err;
  }

  return await response.json();
}

export async function cancelTask(taskId) {
  await syncAuthToken();
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

export async function pauseTask(taskId) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}/pause`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.detail || "Failed to pause task");
  }
  return await response.json();
}

export async function resumeTask(taskId) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/tasks/${encodeURIComponent(taskId)}/resume`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.detail || "Failed to resume task");
  }
  return await response.json();
}

export async function getAppVersion() {
  await syncAuthToken();
  try {
    const response = await fetch(`${API_BASE}/api/app/version`, {
      headers: getAuthHeaders(),
    });
    if (response.ok) {
      return await response.json();
    }
  } catch (_) {}
  return { version: "1.2.9" };
}

export async function openDownloadsFolder(taskId = null) {
  await syncAuthToken();
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

export async function getSystemStatus() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/system-status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to retrieve system status");
  }
  return await response.json();
}

export async function installFfmpeg() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/install-ffmpeg`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Automated installation failed");
  }
  return await response.json();
}

export async function getAppVersion() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/version`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to retrieve app version");
  }
  return await response.json();
}

export async function checkAppUpdates(force = false) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/update/check?force=${encodeURIComponent(force)}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to check for updates");
  }
  return await response.json();
}

export async function startAppUpdateDownload(downloadUrl, expectedSize = 0, versionTag = "latest") {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/update/download`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      download_url: downloadUrl,
      expected_size: expectedSize,
      version_tag: versionTag,
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to initiate update download");
  }
  return await response.json();
}

export async function getAppUpdateProgress() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/update/download-progress`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to get update progress");
  }
  return await response.json();
}

export async function cancelAppUpdate() {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/update/cancel`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return await response.json();
}

export async function applyAppUpdate(installerPath = null, silent = true) {
  await syncAuthToken();
  const response = await fetch(`${API_BASE}/api/app/update/apply`, {
    method: "POST",
    headers: getAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      installer_path: installerPath,
      silent: silent,
    }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.message || err.detail || "Failed to execute installer");
  }
  return await response.json();
}

