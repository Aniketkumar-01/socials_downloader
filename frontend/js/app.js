import { 
  fetchMediaInfo, 
  startDownload, 
  openDownloadsFolder, 
  getDownloadFileUrl,
  checkCookiesStatus,
  uploadCookiesFile,
  deleteCookiesFile
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
const engineBadgeText = document.getElementById("engine-badge-text");
const toastContainer = document.getElementById("toast-container");

const btnUploadCookies = document.getElementById("btn-upload-cookies");
const cookieFileInput = document.getElementById("cookie-file-input");
const cookieActiveBadge = document.getElementById("cookie-active-badge");
const btnRemoveCookies = document.getElementById("btn-remove-cookies");
const btnCookieHelp = document.getElementById("btn-cookie-help");
const cookieModal = document.getElementById("cookie-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnModalDone = document.getElementById("btn-modal-done");
const btnModalUpload = document.getElementById("btn-modal-upload");

const errorAlert = document.getElementById("error-alert");
const errorMessage = document.getElementById("error-message");

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
const btnDownload = document.getElementById("btn-download");
const btnDownloadText = document.getElementById("btn-download-text");

const progressCard = document.getElementById("progress-card");
const progressItemTitle = document.getElementById("progress-item-title");
const progressPercentage = document.getElementById("progress-percentage");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressSpeed = document.getElementById("progress-speed");
const progressEta = document.getElementById("progress-eta");
const progressActions = document.getElementById("progress-actions");
const btnOpenFolder = document.getElementById("btn-open-folder");
const btnBrowserDownload = document.getElementById("btn-browser-download");

// Application State
let currentMedia = null;
let currentTracker = null;
let currentTaskId = null;
let allPlaylistSelected = true;

// Helper: Show Error Alert
function showError(msg) {
  errorMessage.textContent = msg;
  errorAlert.style.display = "flex";
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

  // Populate quality options
  qualitySelect.innerHTML = "";
  if (info.available_qualities && info.available_qualities.length > 0) {
    info.available_qualities.forEach((q) => {
      const opt = document.createElement("option");
      opt.value = q;
      if (q === "best") opt.textContent = "Best Quality (MP4)";
      else if (q === "1080p") opt.textContent = "Full HD 1080p (MP4)";
      else if (q === "720p") opt.textContent = "HD 720p (MP4)";
      else if (q === "480p") opt.textContent = "SD 480p (MP4)";
      else if (q === "audio_mp3") opt.textContent = "Audio Only (MP3)";
      else opt.textContent = q.toUpperCase();
      qualitySelect.appendChild(opt);
    });
  } else {
    qualitySelect.innerHTML = `<option value="best" selected>Best Quality (MP4)</option><option value="audio_mp3">Audio Only (MP3)</option>`;
  }

  if (info.is_playlist) {
    mediaBadge.textContent = "PLAYLIST";
    mediaBadge.style.color = "#7928ca";
    mediaBadge.style.borderColor = "rgba(121, 40, 202, 0.4)";
    mediaBadge.style.background = "rgba(121, 40, 202, 0.15)";
    mediaDuration.textContent = `${info.item_count} Items`;

    // Render playlist items
    playlistCount.textContent = `Playlist Items (${info.item_count})`;
    playlistItemsList.innerHTML = "";

    info.items.forEach((item, index) => {
      const row = document.createElement("label");
      row.className = "playlist-item";
      row.innerHTML = `
        <input type="checkbox" class="playlist-checkbox" value="${item.id}" checked>
        <span class="playlist-item-title">${index + 1}. ${escapeHtml(item.title)}</span>
        <span class="playlist-item-duration">${item.duration_string || ""}</span>
      `;
      playlistItemsList.appendChild(row);
    });

    playlistSection.style.display = "block";
    btnDownloadText.textContent = `Download Playlist (${info.item_count} Items)`;
  } else {
    // Single video
    mediaBadge.textContent = "VIDEO";
    mediaBadge.style.color = "var(--accent-cyan)";
    mediaBadge.style.borderColor = "rgba(0, 242, 254, 0.25)";
    mediaBadge.style.background = "rgba(0, 242, 254, 0.1)";

    const single = info.items && info.items[0];
    mediaDuration.textContent = single?.duration_string || "00:00";

    playlistSection.style.display = "none";
    btnDownloadText.textContent = "Download Now";
  }

  mediaCard.style.display = "block";
  mediaCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Toggle all checkboxes in playlist
playlistToggleBtn.addEventListener("click", () => {
  allPlaylistSelected = !allPlaylistSelected;
  const checkboxes = document.querySelectorAll(".playlist-checkbox");
  checkboxes.forEach((cb) => (cb.checked = allPlaylistSelected));
  playlistToggleBtn.textContent = allPlaylistSelected ? "Deselect All" : "Select All";
  updatePlaylistDownloadButtonCount();
});

// Update download button count on checkbox change
playlistItemsList.addEventListener("change", (e) => {
  if (e.target.classList.contains("playlist-checkbox")) {
    updatePlaylistDownloadButtonCount();
  }
});

function updatePlaylistDownloadButtonCount() {
  const selectedCount = document.querySelectorAll(".playlist-checkbox:checked").length;
  btnDownloadText.textContent = `Download Playlist (${selectedCount} Selected)`;
  btnDownload.disabled = selectedCount === 0;
}

// Download Button Click Handler
btnDownload.addEventListener("click", async () => {
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
  btnDownload.disabled = true;
  btnDownloadText.textContent = "Starting download...";

  try {
    const cookieBrowser = cookieSelect ? cookieSelect.value : null;
    const res = await startDownload({
      url: currentMedia.url,
      isPlaylist: currentMedia.is_playlist,
      selectedVideoIds,
      quality,
      cookieBrowser,
    });

    currentTaskId = res.task_id;
    showProgressView(currentTaskId);
  } catch (err) {
    showError(err.message || "Failed to start download.");
    btnDownload.disabled = false;
    btnDownloadText.textContent = currentMedia.is_playlist ? "Download Playlist" : "Download Now";
  }
});

// Show & bind real-time progress view
function showProgressView(taskId) {
  progressCard.style.display = "block";
  progressActions.style.display = "none";
  progressPercentage.textContent = "0%";
  progressBarFill.style.width = "0%";
  progressSpeed.textContent = "Speed: Calculating...";
  progressEta.textContent = "ETA: --";
  progressItemTitle.textContent = "Initializing download...";
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

      if (data.current_item) {
        progressItemTitle.textContent = data.current_item;
      }

      btnDownloadText.textContent = `Downloading (${pct.toFixed(0)}%)...`;
    },
    onComplete: (data) => {
      progressBarFill.style.width = "100%";
      progressPercentage.textContent = "100%";
      progressSpeed.textContent = "Speed: Complete";
      progressEta.textContent = "ETA: Done";
      progressItemTitle.textContent = "Download completed successfully!";

      // Show action buttons
      progressActions.style.display = "flex";
      btnBrowserDownload.href = getDownloadFileUrl(taskId);

      // Re-enable download button
      btnDownload.disabled = false;
      btnDownloadText.textContent = "Download Complete!";
    },
    onError: (errMsg) => {
      showError(`Download interrupted: ${errMsg}`);
      progressItemTitle.textContent = "Download failed.";
      btnDownload.disabled = false;
      btnDownloadText.textContent = currentMedia.is_playlist ? "Download Playlist" : "Download Now";
    },
  });

  currentTracker.start();
}

// "Show in Folder" button action
btnOpenFolder.addEventListener("click", async () => {
  try {
    await openDownloadsFolder(currentTaskId);
  } catch (err) {
    console.error("Failed to open folder:", err);
  }
});

// Utility to escape HTML strings safely
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// Cookie Status Management
async function initCookieStatus() {
  try {
    const status = await checkCookiesStatus();
    if (status.has_cookies_file) {
      if (cookieActiveBadge) cookieActiveBadge.style.display = "inline-flex";
      if (cookieSelect) {
        let opt = cookieSelect.querySelector('option[value="cookies_file"]');
        if (!opt) {
          opt = document.createElement("option");
          opt.value = "cookies_file";
          cookieSelect.insertBefore(opt, cookieSelect.firstChild);
        }
        opt.textContent = "✔ Using cookies.txt (Active)";
        opt.selected = true;
      }
    } else {
      if (cookieActiveBadge) cookieActiveBadge.style.display = "none";
      if (cookieSelect) {
        const opt = cookieSelect.querySelector('option[value="cookies_file"]');
        if (opt) opt.remove();
      }
    }
  } catch (err) {
    console.warn("Could not check cookies status:", err);
  }
}

// Cookie Upload & Management Events
if (btnUploadCookies && cookieFileInput) {
  btnUploadCookies.addEventListener("click", () => {
    cookieFileInput.click();
  });

  cookieFileInput.addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    try {
      clearError();
      btnUploadCookies.textContent = "Uploading...";
      await uploadCookiesFile(file);
      btnUploadCookies.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        Upload cookies.txt
      `;
      if (cookieModal) cookieModal.style.display = "none";
      await initCookieStatus();
      // Show confirmation
      showError("✔ cookies.txt uploaded and active! You can now fetch YouTube videos without bot blocks.");
      errorAlert.className = "alert-error";
      errorAlert.style.borderColor = "rgba(16, 185, 129, 0.4)";
      errorAlert.style.background = "rgba(16, 185, 129, 0.1)";
      errorAlert.style.color = "var(--accent-green)";
    } catch (err) {
      showError(`Failed to upload cookies: ${err.message}`);
    } finally {
      cookieFileInput.value = "";
    }
  });
}

// Cookie Removal Event
if (btnRemoveCookies) {
  btnRemoveCookies.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await deleteCookiesFile();
      await initCookieStatus();
      clearError();
    } catch (err) {
      console.error("Failed to remove cookies:", err);
    }
  });
}

// Cookie Help Modal Events
if (btnCookieHelp && cookieModal) {
  btnCookieHelp.addEventListener("click", () => {
    cookieModal.style.display = "flex";
  });
}

if (btnCloseModal && cookieModal) {
  btnCloseModal.addEventListener("click", () => {
    cookieModal.style.display = "none";
  });
}

if (btnModalDone && cookieModal) {
  btnModalDone.addEventListener("click", () => {
    cookieModal.style.display = "none";
  });
}

if (btnModalUpload && cookieModal && cookieFileInput) {
  btnModalUpload.addEventListener("click", () => {
    cookieModal.style.display = "none";
    cookieFileInput.click();
  });
}

if (cookieModal) {
  cookieModal.addEventListener("click", (e) => {
    if (e.target === cookieModal) {
      cookieModal.style.display = "none";
    }
  });
}

// Initialize on load
initCookieStatus();

