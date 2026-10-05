import { 
  fetchMediaInfo, 
  startDownload, 
  cancelTask,
  openDownloadsFolder, 
  openFile,
  getDownloadDir,
  setDownloadDir,
  chooseFolder,
  syncAuthToken,
  getSystemStatus,
  installFfmpeg
} from "./api.js";
import { ProgressTracker } from "./progress.js";

// DOM Elements
const urlForm = document.getElementById("url-form");
const urlInput = document.getElementById("url-input");
const btnClear = document.getElementById("btn-clear");
const btnPaste = document.getElementById("btn-paste");
const btnSubmit = document.getElementById("btn-submit");
const btnSubmitText = document.getElementById("btn-submit-text");
const btnSpinner = document.getElementById("btn-spinner");
const platformPills = document.querySelectorAll(".platform-pill");
const cookieSelect = document.getElementById("cookie-select");
const toastContainer = document.getElementById("toast-container");

const errorAlert = document.getElementById("error-alert");
const errorMessage = document.getElementById("error-message");

const prerequisitesBanner = document.getElementById("prerequisites-banner");
const btnInstallFfmpeg = document.getElementById("btn-install-ffmpeg");
const btnInstallFfmpegText = document.getElementById("btn-install-ffmpeg-text");
const btnCopyWinget = document.getElementById("btn-copy-winget");
const btnDismissPrereq = document.getElementById("btn-dismiss-prereq");

const mediaCard = document.getElementById("media-card");
const mediaThumb = document.getElementById("media-thumb");
const mediaDuration = document.getElementById("media-duration");
const mediaBadge = document.getElementById("media-badge");
const platformBadge = document.getElementById("platform-badge");
const mediaTitle = document.getElementById("media-title");
const channelName = document.getElementById("channel-name");

const playlistSection = document.getElementById("playlist-section");
const playlistCount = document.getElementById("playlist-count");
const playlistToggleBtn = document.getElementById("btn-toggle-playlist");
const playlistItemsList = document.getElementById("playlist-items-list");

const qualitySelect = document.getElementById("quality-select");
const qualitySizeBadge = document.getElementById("quality-size-badge");
const folderPathInput = document.getElementById("folder-path-input");
const btnBrowseFolder = document.getElementById("btn-browse-folder");
const btnDownload = document.getElementById("btn-download");
const btnDownloadText = document.getElementById("btn-download-text");

const progressCard = document.getElementById("progress-card");
const progressItemTitle = document.getElementById("progress-item-title");
const progressPercentage = document.getElementById("progress-percentage");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressSpeed = document.getElementById("progress-speed");
const progressEta = document.getElementById("progress-eta");
const progressSize = document.getElementById("progress-size");
const btnCancelDownload = document.getElementById("btn-cancel-download");
const progressActions = document.getElementById("progress-actions");
const btnOpenFolder = document.getElementById("btn-open-folder");
const btnPlayFile = document.getElementById("btn-play-file");
const btnDownloadAgain = document.getElementById("btn-download-again");

// Application State
let currentMedia = null;
let currentTracker = null;
let currentTaskId = null;
let allPlaylistSelected = true;
let isCurrentMediaDownloaded = false;

// Helper: Format Bytes to human readable string
function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i >= 2 ? 1 : 0)} ${units[i]}`;
}

// Helper: Show Error Alert
function showError(msg) {
  errorMessage.textContent = msg;
  errorAlert.style.display = "flex";

  const botHelpers = document.getElementById("bot-auth-helpers");
  if (botHelpers) {
    const isBot = (msg || "").toLowerCase().includes("bot") || 
                  (msg || "").toLowerCase().includes("sign in to confirm") || 
                  (msg || "").toLowerCase().includes("verification") ||
                  (msg || "").toLowerCase().includes("cookies");
    botHelpers.style.display = isBot ? "block" : "none";
  }

  errorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Helper: Toast Notifications
export function showToast(msg, type = "info") {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px) scale(0.95)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

// Helper: Clear Error Alert
function clearError() {
  errorAlert.style.display = "none";
  errorMessage.textContent = "";
  const botHelpers = document.getElementById("bot-auth-helpers");
  if (botHelpers) botHelpers.style.display = "none";
}

// Quick Local Browser Auth Button Handlers
document.querySelectorAll(".btn-quick-browser").forEach((btn) => {
  btn.addEventListener("click", () => {
    const browser = btn.dataset.browser;
    if (cookieSelect) {
      cookieSelect.value = browser;
      showToast(`Selected ${browser === 'edge' ? 'Microsoft Edge' : 'Google Chrome'} session. Re-trying on PC...`, "info");
      clearError();
      urlForm.dispatchEvent(new Event("submit"));
    }
  });
});

// Helper: Manage Download Button State
function setDownloadButtonState(state, customText = null) {
  if (!btnDownload) return;

  if (state === "ready") {
    isCurrentMediaDownloaded = false;
    btnDownload.disabled = false;
    const isPlaylist = currentMedia && currentMedia.is_playlist;
    const selectedCount = document.querySelectorAll(".playlist-checkbox:checked").length;
    const defaultText = isPlaylist ? `Download Playlist (${selectedCount} Selected)` : "Download Now";
    const text = customText || defaultText;
    btnDownload.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      <span id="btn-download-text">${text}</span>
    `;
  } else if (state === "downloading") {
    isCurrentMediaDownloaded = false;
    btnDownload.disabled = true;
    const text = customText || "Downloading...";
    btnDownload.innerHTML = `
      <span class="fetch-spinner" style="width: 14px; height: 14px; border-width: 2px; border-color: var(--text-on-accent); border-right-color: transparent;"></span>
      <span id="btn-download-text">${text}</span>
    `;
  } else if (state === "completed") {
    isCurrentMediaDownloaded = true;
    btnDownload.disabled = false;
    const isPlaylist = currentMedia && currentMedia.is_playlist;
    if (isPlaylist) {
      btnDownload.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        <span id="btn-download-text">Show in Windows Explorer</span>
      `;
    } else {
      btnDownload.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span id="btn-download-text">Open / Play File</span>
      `;
    }
  }
}

// Input clear button toggle
urlInput.addEventListener("input", () => {
  if (btnClear) {
    btnClear.style.display = urlInput.value ? "flex" : "none";
  }
});

if (btnClear) {
  btnClear.addEventListener("click", () => {
    urlInput.value = "";
    btnClear.style.display = "none";
    updatePlatformHighlights("");
    urlInput.focus();
  });
}

// Global keyboard shortcuts
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (urlInput.value) {
      urlInput.value = "";
      if (btnClear) btnClear.style.display = "none";
      updatePlatformHighlights("");
    }
    clearError();
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    urlInput.focus();
    urlInput.select();
  }
});

// Helper: Toggle Button Loading State
function setLoading(isLoading) {
  btnSubmit.disabled = isLoading;
  btnSubmitText.textContent = isLoading ? "Fetching..." : "Fetch Info";
  btnSpinner.style.display = isLoading ? "inline-block" : "none";
}

// Platform detection highlighter
function updatePlatformHighlights(url) {
  const u = (url || "").toLowerCase();
  let detected = null;
  if (u.includes("youtube.com") || u.includes("youtu.be")) detected = "youtube";
  else if (u.includes("instagram.com")) detected = "instagram";
  else if (u.includes("tiktok.com")) detected = "tiktok";
  else if (u.includes("twitter.com") || u.includes("x.com")) detected = "twitter";
  else if (u.includes("bilibili.com") || u.includes("b23.tv")) detected = "bilibili";
  else if (u.includes("facebook.com") || u.includes("fb.watch")) detected = "facebook";
  else if (u.includes("reddit.com")) detected = "reddit";

  platformPills.forEach((pill) => {
    if (detected && pill.dataset.platform === detected) {
      pill.classList.add("active");
    } else {
      pill.classList.remove("active");
    }
  });
  return detected;
}

urlInput.addEventListener("input", (e) => {
  updatePlatformHighlights(e.target.value);
});

// Paste button handler
btnPaste.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text.trim();
      updatePlatformHighlights(urlInput.value);
      urlInput.focus();
    }
  } catch (err) {
    console.warn("Clipboard access denied or unavailable:", err);
  }
});

// URL Form Submission
urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const url = urlInput.value.trim();
  if (!url) {
    showError("Please enter a valid video or playlist URL.");
    return;
  }

  updatePlatformHighlights(url);
  setLoading(true);
  mediaCard.style.display = "none";
  progressCard.style.display = "none";

  try {
    const cookieBrowser = cookieSelect ? cookieSelect.value : null;
    const info = await fetchMediaInfo(url, cookieBrowser);
    currentMedia = info;
    renderMediaInfo(info);
  } catch (err) {
    showError(err.message || "Failed to load media details. Please verify the URL.");
  } finally {
    setLoading(false);
  }
});

// Update dynamic quality size badge based on selected option
function updateQualityBadge() {
  if (!qualitySizeBadge || !currentMedia) return;
  const q = qualitySelect ? qualitySelect.value : "best";
  const sizes = currentMedia.quality_sizes_formatted || {};
  const formatted = sizes[q] || currentMedia.filesize_formatted;
  if (formatted) {
    qualitySizeBadge.textContent = formatted;
    qualitySizeBadge.style.display = "inline-flex";
  } else {
    qualitySizeBadge.style.display = "none";
  }
}

if (qualitySelect) {
  qualitySelect.addEventListener("change", () => {
    updateQualityBadge();
    if (isCurrentMediaDownloaded) {
      setDownloadButtonState("ready");
    }
  });
}

// Render Media Details & Playlist Items
function renderMediaInfo(info) {
  mediaTitle.textContent = info.title;
  channelName.textContent = info.channel || "Creator";

  if (info.thumbnail) {
    mediaThumb.src = info.thumbnail;
    mediaThumb.style.display = "block";
  } else {
    mediaThumb.style.display = "none";
  }

  // Set platform badge
  const platformName = (info.platform || "universal").toUpperCase();
  platformBadge.textContent = platformName;
  if (platformName === "YOUTUBE") {
    platformBadge.style.color = "#ff4b4b";
    platformBadge.style.borderColor = "rgba(255, 75, 75, 0.3)";
    platformBadge.style.background = "rgba(255, 75, 75, 0.1)";
  } else if (platformName === "INSTAGRAM") {
    platformBadge.style.color = "#e1306c";
    platformBadge.style.borderColor = "rgba(225, 48, 108, 0.3)";
    platformBadge.style.background = "rgba(225, 48, 108, 0.1)";
  } else if (platformName === "TIKTOK") {
    platformBadge.style.color = "#00f2fe";
    platformBadge.style.borderColor = "rgba(0, 242, 254, 0.3)";
    platformBadge.style.background = "rgba(0, 242, 254, 0.1)";
  } else {
    platformBadge.style.color = "var(--accent-blue)";
    platformBadge.style.borderColor = "rgba(79, 172, 254, 0.3)";
    platformBadge.style.background = "rgba(79, 172, 254, 0.1)";
  }

  // Populate quality options with estimated file sizes
  qualitySelect.innerHTML = "";
  const sizes = info.quality_sizes_formatted || {};
  if (info.available_qualities && info.available_qualities.length > 0) {
    info.available_qualities.forEach((q) => {
      const opt = document.createElement("option");
      opt.value = q;
      const sizeTag = sizes[q] ? ` (${sizes[q]})` : "";
      if (q === "best") opt.textContent = `Best Quality (MP4)${sizeTag}`;
      else if (q === "2160p" || q === "4k") opt.textContent = `4K 2160p (MP4)${sizeTag}`;
      else if (q === "1440p" || q === "2k") opt.textContent = `2K 1440p (MP4)${sizeTag}`;
      else if (q === "1080p") opt.textContent = `Full HD 1080p (MP4)${sizeTag}`;
      else if (q === "720p") opt.textContent = `HD 720p (MP4)${sizeTag}`;
      else if (q === "480p") opt.textContent = `SD 480p (MP4)${sizeTag}`;
      else if (q === "360p") opt.textContent = `SD 360p (MP4)${sizeTag}`;
      else if (q === "audio_mp3") opt.textContent = `Audio Only (MP3)${sizeTag}`;
      else opt.textContent = `${q.toUpperCase()}${sizeTag}`;
      qualitySelect.appendChild(opt);
    });
  } else {
    const bestTag = sizes["best"] ? ` (${sizes["best"]})` : "";
    const mp3Tag = sizes["audio_mp3"] ? ` (${sizes["audio_mp3"]})` : "";
    qualitySelect.innerHTML = `<option value="best" selected>Best Quality (MP4)${bestTag}</option><option value="audio_mp3">Audio Only (MP3)${mp3Tag}</option>`;
  }

  updateQualityBadge();

  if (info.is_playlist) {
    mediaBadge.textContent = "PLAYLIST";
    mediaBadge.style.color = "#7928ca";
    mediaBadge.style.borderColor = "rgba(121, 40, 202, 0.4)";
    mediaBadge.style.background = "rgba(121, 40, 202, 0.15)";
    mediaDuration.textContent = `${info.item_count} Items`;

    // Render playlist items with item-level size badge
    playlistCount.textContent = `Playlist Items (${info.item_count})`;
    playlistItemsList.innerHTML = "";

    info.items.forEach((item, index) => {
      const row = document.createElement("label");
      row.className = "playlist-item";
      const sizeTag = item.filesize_formatted ? `<span class="playlist-item-size">${item.filesize_formatted}</span>` : "";
      row.innerHTML = `
        <input type="checkbox" class="playlist-checkbox" value="${item.id}" checked>
        <span class="playlist-item-title">${index + 1}. ${escapeHtml(item.title)}</span>
        <div class="playlist-item-meta">
          ${sizeTag}
          <span class="playlist-item-duration">${item.duration_string || ""}</span>
        </div>
      `;
      playlistItemsList.appendChild(row);
    });

    playlistSection.style.display = "block";
    updatePlaylistDownloadButtonCount();
  } else {
    // Single video
    mediaBadge.textContent = "VIDEO";
    mediaBadge.style.color = "var(--accent-cyan)";
    mediaBadge.style.borderColor = "rgba(0, 242, 254, 0.25)";
    mediaBadge.style.background = "rgba(0, 242, 254, 0.1)";

    const single = info.items && info.items[0];
    mediaDuration.textContent = single?.duration_string || "00:00";

    playlistSection.style.display = "none";
    setDownloadButtonState("ready", "Download Now");
  }

  // Ensure save location is populated with current download folder
  if (folderPathInput && !folderPathInput.value) {
    initDownloadDir();
  }

  mediaCard.style.display = "block";
  mediaCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Toggle all checkboxes in playlist
if (playlistToggleBtn) {
  playlistToggleBtn.addEventListener("click", () => {
    allPlaylistSelected = !allPlaylistSelected;
    const checkboxes = document.querySelectorAll(".playlist-checkbox");
    checkboxes.forEach((cb) => (cb.checked = allPlaylistSelected));
    playlistToggleBtn.textContent = allPlaylistSelected ? "Deselect All" : "Select All";
    updatePlaylistDownloadButtonCount();
    if (isCurrentMediaDownloaded) {
      setDownloadButtonState("ready");
    }
  });
}

// Update download button count & estimated total size on checkbox change
if (playlistItemsList) {
  playlistItemsList.addEventListener("change", (e) => {
    if (e.target.classList.contains("playlist-checkbox")) {
      updatePlaylistDownloadButtonCount();
      if (isCurrentMediaDownloaded) {
        setDownloadButtonState("ready");
      }
    }
  });
}

function updatePlaylistDownloadButtonCount() {
  const selectedBoxes = Array.from(document.querySelectorAll(".playlist-checkbox:checked"));
  const selectedCount = selectedBoxes.length;

  let totalBytes = 0;
  if (currentMedia && currentMedia.items) {
    const selectedIds = new Set(selectedBoxes.map(cb => cb.value));
    currentMedia.items.forEach(item => {
      if (selectedIds.has(item.id) && item.filesize) {
        totalBytes += item.filesize;
      }
    });
  }

  const sizeText = totalBytes > 0 ? ` • ~${formatBytes(totalBytes)}` : "";
  const label = `Download Playlist (${selectedCount} Selected${sizeText})`;
  setDownloadButtonState("ready", label);
  btnDownload.disabled = selectedCount === 0;
}

// Unified Download Execution function
async function executeDownload() {
  if (!currentMedia) return;
  clearError();

  let selectedVideoIds = null;
  if (currentMedia.is_playlist) {
    const checked = Array.from(document.querySelectorAll(".playlist-checkbox:checked"));
    selectedVideoIds = checked.map((cb) => cb.value);
    if (selectedVideoIds.length === 0) {
      showError("Please select at least one item to download.");
      return;
    }
  }

  const quality = qualitySelect.value;
  setDownloadButtonState("downloading", "Starting download...");

  try {
    const cookieBrowser = cookieSelect ? cookieSelect.value : null;
    let downloadDir = folderPathInput ? folderPathInput.value.trim() : null;
    if (downloadDir) {
      downloadDir = downloadDir.replace(/^["']+|["']+$/g, '').trim();
    }

    const res = await startDownload({
      url: currentMedia.url,
      isPlaylist: currentMedia.is_playlist,
      selectedVideoIds,
      quality,
      cookieBrowser,
      downloadDir: downloadDir || null,
    });

    currentTaskId = res.task_id;
    showProgressView(currentTaskId);
  } catch (err) {
    showError(err.message || "Failed to start download.");
    setDownloadButtonState("ready");
  }
}

// Download Button Click Handler
btnDownload.addEventListener("click", async () => {
  if (!currentMedia) return;

  // If already downloaded, clicking the button opens the media file or folder!
  if (isCurrentMediaDownloaded && currentTaskId) {
    if (currentMedia.is_playlist) {
      showToast("Opening folder in Windows Explorer...", "info");
      try {
        await openDownloadsFolder(currentTaskId);
      } catch (err) {
        showError(err.message || "Could not open folder in Explorer.");
      }
    } else {
      showToast("Launching media player...", "info");
      try {
        await openFile(currentTaskId);
      } catch (err) {
        console.error("Failed to open file:", err);
        showError(err.message || "Could not launch media player.");
      }
    }
    return;
  }

  executeDownload();
});

// "Download Again" button in completed actions
if (btnDownloadAgain) {
  btnDownloadAgain.addEventListener("click", () => {
    if (!currentMedia) return;
    isCurrentMediaDownloaded = false;
    setDownloadButtonState("ready");
    showToast("Restarting download...", "info");
    executeDownload();
  });
}

// Show & bind real-time progress view with cancel and size telemetry
function showProgressView(taskId) {
  progressCard.style.display = "block";
  progressActions.style.display = "none";
  progressPercentage.textContent = "0%";
  progressBarFill.style.width = "0%";
  progressBarFill.style.background = "linear-gradient(90deg, #00d2ff, #00f0b5)";
  progressSpeed.textContent = "Speed: Calculating...";
  progressEta.textContent = "ETA: --";
  progressItemTitle.textContent = "Initializing download...";

  // Set initial estimated size
  if (progressSize) {
    const q = qualitySelect ? qualitySelect.value : "best";
    const est = (currentMedia && currentMedia.quality_sizes_formatted && currentMedia.quality_sizes_formatted[q]) || (currentMedia && currentMedia.filesize_formatted);
    progressSize.textContent = est ? `Size: ${est}` : "Size: Calculating...";
  }

  // Display and reset Cancel button
  if (btnCancelDownload) {
    btnCancelDownload.style.display = "inline-flex";
    btnCancelDownload.disabled = false;
    btnCancelDownload.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
      <span>Cancel</span>
    `;
  }

  progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  if (currentTracker) {
    currentTracker.close();
  }

  currentTracker = new ProgressTracker(taskId, {
    onProgress: (data) => {
      const pct = Math.min(100, Math.max(0, data.progress || 0));
      progressBarFill.style.width = `${pct}%`;
      progressPercentage.textContent = `${pct.toFixed(1)}%`;
      progressSpeed.textContent = `Speed: ${data.speed_str || "--"}`;
      progressEta.textContent = `ETA: ${data.eta_str || "--"}`;

      // Update real-time downloaded vs total size
      if (progressSize) {
        if (data.downloaded_bytes && data.total_bytes && data.total_bytes > 0) {
          progressSize.textContent = `Size: ${formatBytes(data.downloaded_bytes)} / ${formatBytes(data.total_bytes)}`;
        } else if (data.downloaded_bytes && data.downloaded_bytes > 0) {
          progressSize.textContent = `Size: ${formatBytes(data.downloaded_bytes)}`;
        }
      }

      if (data.current_item) {
        progressItemTitle.textContent = data.current_item;
      }

      // Hide cancel button if completed or 100%
      if (data.status === "completed" || pct >= 100) {
        if (btnCancelDownload) {
          btnCancelDownload.style.display = "none";
        }
      }

      setDownloadButtonState("downloading", `Downloading (${pct.toFixed(0)}%)...`);
    },
    onComplete: (data) => {
      if (btnCancelDownload) {
        btnCancelDownload.style.display = "none";
      }
      progressBarFill.style.width = "100%";
      progressPercentage.textContent = "100%";
      progressSpeed.textContent = "Speed: Complete";
      progressEta.textContent = "ETA: Done";
      progressItemTitle.textContent = "Download completed successfully!";

      if (progressSize && data.total_bytes) {
        progressSize.textContent = `Total: ${formatBytes(data.total_bytes)}`;
      }

      // Reveal post-download actions
      progressActions.style.display = "flex";

      // Transform button to Open / Play File
      setDownloadButtonState("completed");
    },
    onCancel: (data) => {
      if (btnCancelDownload) {
        btnCancelDownload.style.display = "none";
      }
      progressBarFill.style.width = "100%";
      progressBarFill.style.background = "#f59e0b";
      progressPercentage.textContent = "Cancelled";
      progressSpeed.textContent = "Speed: --";
      progressEta.textContent = "ETA: --";
      progressItemTitle.textContent = "Download was cancelled.";
      setDownloadButtonState("ready");
      showToast("Download was cancelled.", "info");
    },
    onError: (errMsg) => {
      if (btnCancelDownload) {
        btnCancelDownload.style.display = "none";
      }
      showError(`Download interrupted: ${errMsg}`);
      progressItemTitle.textContent = "Download failed.";
      setDownloadButtonState("ready");
    },
  });

  currentTracker.start();
}

// Cancel Download Click Handler - Instant 0ms Feedback
if (btnCancelDownload) {
  btnCancelDownload.addEventListener("click", async () => {
    if (!currentTaskId) return;

    // 1. Immediately abort active client tracker so UI stops spinning
    if (currentTracker) {
      currentTracker.close();
    }

    // 2. Immediate visual update to Cancelled state
    btnCancelDownload.style.display = "none";
    progressBarFill.style.width = "100%";
    progressBarFill.style.background = "#f59e0b";
    progressPercentage.textContent = "Cancelled";
    progressSpeed.textContent = "Speed: --";
    progressEta.textContent = "ETA: --";
    progressItemTitle.textContent = "Download was cancelled.";
    setDownloadButtonState("ready");
    showToast("Download cancelled.", "info");

    // 3. Dispatch server cancel non-blockingly
    try {
      await cancelTask(currentTaskId);
    } catch (err) {
      console.warn("Cancel request notice:", err);
    }
  });
}

// "Show in Windows Explorer" action
if (btnOpenFolder) {
  btnOpenFolder.addEventListener("click", async () => {
    try {
      showToast("Opening folder in Windows Explorer...", "info");
      await openDownloadsFolder(currentTaskId);
    } catch (err) {
      console.error("Failed to open folder:", err);
      showError("Could not reveal file in Windows Explorer.");
    }
  });
}

// "Open / Play File" action
if (btnPlayFile) {
  btnPlayFile.addEventListener("click", async () => {
    if (!currentTaskId) return;
    try {
      btnPlayFile.disabled = true;
      showToast("Launching media player...", "info");
      await openFile(currentTaskId);
    } catch (err) {
      console.error("Failed to open file:", err);
      showError(err.message || "Could not launch media player.");
    } finally {
      setTimeout(() => {
        if (btnPlayFile) btnPlayFile.disabled = false;
      }, 600);
    }
  });
}

// Initialize and manage Download Directory
async function initDownloadDir() {
  if (!folderPathInput) return;
  try {
    await syncAuthToken();
    const res = await getDownloadDir();
    if (res && res.download_dir) {
      folderPathInput.value = res.download_dir;
      folderPathInput.placeholder = res.download_dir;
    }
  } catch (err) {
    console.warn("Could not retrieve download directory:", err);
  }
}

// Browse folder action with visual feedback
if (btnBrowseFolder) {
  btnBrowseFolder.addEventListener("click", async () => {
    try {
      btnBrowseFolder.disabled = true;
      const originalHtml = btnBrowseFolder.innerHTML;
      btnBrowseFolder.innerHTML = `
        <span class="fetch-spinner" style="width: 12px; height: 12px; border-width: 1.5px; border-color: var(--accent-primary); border-right-color: transparent;"></span>
        <span>Selecting...</span>
      `;
      showToast("Opening folder picker dialog...", "info");

      const res = await chooseFolder();
      btnBrowseFolder.innerHTML = originalHtml;
      btnBrowseFolder.disabled = false;

      if (res && res.status === "success" && (res.path || res.download_dir)) {
        const chosen = res.path || res.download_dir;
        if (folderPathInput) {
          folderPathInput.value = chosen;
          folderPathInput.placeholder = chosen;
        }
        showToast(`Save location set: ${chosen}`, "info");
        clearError();
        if (isCurrentMediaDownloaded) {
          setDownloadButtonState("ready");
        }
      } else if (res && res.status === "cancelled") {
        showToast("Folder selection was cancelled.", "info");
      } else if (res && res.status === "error") {
        showError(res.message || "Failed to open folder picker.");
      }
    } catch (err) {
      console.error("Browse folder error:", err);
      showError(err.message || "Failed to launch folder picker.");
      if (btnBrowseFolder) {
        btnBrowseFolder.disabled = false;
        btnBrowseFolder.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>Browse</span>
        `;
      }
    }
  });
}

// Manual Save Location input handling (strips quotes, handles Enter key & blur)
if (folderPathInput) {
  const commitPathChange = async () => {
    let raw = folderPathInput.value.trim();
    // Strip surrounding quotes (e.g. from Explorer "Copy as Path")
    raw = raw.replace(/^["']+|["']+$/g, '').trim();

    if (!raw) {
      // If empty, restore current configured default
      await initDownloadDir();
      return;
    }

    folderPathInput.value = raw;
    try {
      const res = await setDownloadDir(raw);
      if (res && res.download_dir) {
        folderPathInput.value = res.download_dir;
        folderPathInput.placeholder = res.download_dir;
      }
      showToast("Save location updated", "info");
      clearError();
      if (isCurrentMediaDownloaded) {
        setDownloadButtonState("ready");
      }
    } catch (err) {
      console.warn("Failed to set download directory:", err);
      showError(err.message || "Invalid save directory path");
    }
  };

  folderPathInput.addEventListener("change", commitPathChange);
  folderPathInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      folderPathInput.blur(); // triggers change and commits path
    }
  });
}

// Utility to escape HTML strings safely
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// Prerequisites & FFmpeg Readiness Checker
async function checkPrerequisites() {
  if (!prerequisitesBanner) return;
  try {
    const status = await getSystemStatus();
    if (status && status.ffmpeg_installed) {
      prerequisitesBanner.style.display = "none";
    } else {
      prerequisitesBanner.style.display = "flex";
    }
  } catch (err) {
    console.debug("Prerequisites check notice:", err);
  }
}

// System Command Permission & Choice Modal Handlers
const cmdPermissionModal = document.getElementById("cmd-permission-modal");
const btnCloseCmdModal = document.getElementById("btn-close-cmd-modal");
const btnModalCopyCmd = document.getElementById("btn-modal-copy-cmd");
const btnDiyCmd = document.getElementById("btn-diy-cmd");
const btnGrantPermissionCmd = document.getElementById("btn-grant-permission-cmd");
const btnGrantPermissionText = document.getElementById("btn-grant-permission-text");
const cmdToRun = document.getElementById("cmd-to-run");

function openCmdModal() {
  if (cmdPermissionModal) {
    cmdPermissionModal.style.display = "flex";
  }
}

function closeCmdModal() {
  if (cmdPermissionModal) {
    cmdPermissionModal.style.display = "none";
  }
}

if (btnCloseCmdModal) {
  btnCloseCmdModal.addEventListener("click", closeCmdModal);
}

if (cmdPermissionModal) {
  cmdPermissionModal.addEventListener("click", (e) => {
    if (e.target === cmdPermissionModal) closeCmdModal();
  });
}

async function copyWingetCommand() {
  const cmd = (cmdToRun && cmdToRun.textContent) || "winget install Gyan.FFmpeg";
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(cmd);
    } else {
      const ta = document.createElement("textarea");
      ta.value = cmd;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    showToast(`Copied to clipboard: '${cmd}'`, "info");
  } catch (err) {
    showToast(`Command: ${cmd}`, "info");
  }
}

if (btnModalCopyCmd) {
  btnModalCopyCmd.addEventListener("click", copyWingetCommand);
}

if (btnDiyCmd) {
  btnDiyCmd.addEventListener("click", async () => {
    await copyWingetCommand();
    showToast("Command copied! Open your PowerShell or CMD terminal and run it whenever you want.", "success");
    closeCmdModal();
  });
}

// Clicking 1-Click Install opens the permission & explanation modal first!
if (btnInstallFfmpeg) {
  btnInstallFfmpeg.addEventListener("click", () => {
    openCmdModal();
  });
}

// User grants explicit permission to install in background
if (btnGrantPermissionCmd) {
  btnGrantPermissionCmd.addEventListener("click", async () => {
    try {
      btnGrantPermissionCmd.disabled = true;
      if (btnGrantPermissionText) {
        btnGrantPermissionText.textContent = "Installing on your PC (silent background)...";
      }
      showToast("Installing FFmpeg locally on your PC (no windows will pop up)...", "info");

      const res = await installFfmpeg();
      showToast(res.message || "FFmpeg installed successfully!", "success");

      // Visual success confirmation in banner
      if (prerequisitesBanner) {
        prerequisitesBanner.classList.add("prereq-ready");
        const titleEl = prerequisitesBanner.querySelector(".prereq-title");
        const descEl = document.getElementById("prereq-desc");
        if (titleEl) titleEl.textContent = "✓ FFmpeg Ready";
        if (descEl) descEl.textContent = "High-resolution stream merging (1080p, 4K) and MP3 conversion are now active.";
        if (btnInstallFfmpeg) btnInstallFfmpeg.style.display = "none";
      }

      closeCmdModal();

      setTimeout(() => {
        if (prerequisitesBanner) {
          prerequisitesBanner.style.transition = "all 0.5s ease";
          prerequisitesBanner.style.opacity = "0";
          setTimeout(() => {
            prerequisitesBanner.style.display = "none";
          }, 500);
        }
      }, 4000);
    } catch (err) {
      console.error("FFmpeg install error:", err);
      showError(err.message || "Could not install FFmpeg automatically. You can copy the command and run it in terminal.");
      btnGrantPermissionCmd.disabled = false;
      if (btnGrantPermissionText) {
        btnGrantPermissionText.textContent = "Retry Installation";
      }
    }
  });
}

// Copy winget command to clipboard
if (btnCopyWinget) {
  btnCopyWinget.addEventListener("click", async () => {
    const cmd = "winget install Gyan.FFmpeg";
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(cmd);
      } else {
        const ta = document.createElement("textarea");
        ta.value = cmd;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      showToast("Copied command: 'winget install Gyan.FFmpeg'", "info");
    } catch (err) {
      showToast(`Run in terminal: ${cmd}`, "info");
    }
  });
}

// Dismiss prerequisites banner
if (btnDismissPrereq) {
  btnDismissPrereq.addEventListener("click", () => {
    if (prerequisitesBanner) {
      prerequisitesBanner.style.display = "none";
    }
  });
}

// Initialize on load
initDownloadDir();
checkPrerequisites();
