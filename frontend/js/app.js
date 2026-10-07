import { 
  fetchMediaInfo, 
  fetchBatchMediaInfo,
  startDownload, 
  cancelTask,
  pauseTask,
  resumeTask,
  getAppVersion,
  getClipboardText,
  openDownloadsFolder, 
  openFile,
  getDownloadDir,
  setDownloadDir,
  chooseFolder,
  syncAuthToken,
  getSystemStatus,
  installFfmpeg,
  checkAppUpdates,
  startAppUpdateDownload,
  getAppUpdateProgress,
  cancelAppUpdate,
  applyAppUpdate
} from "./api.js";
import { ProgressTracker } from "./progress.js";

// DOM Elements
const urlForm = document.getElementById("url-form");
const urlInput = document.getElementById("url-input");
const batchInput = document.getElementById("batch-input");
const btnBatchToggle = document.getElementById("btn-batch-toggle");
const batchToggleLabel = document.getElementById("batch-toggle-label");
const btnClear = document.getElementById("btn-clear");
const btnPaste = document.getElementById("btn-paste");
const btnSubmit = document.getElementById("btn-submit");
const btnSubmitText = document.getElementById("btn-submit-text");
const btnSpinner = document.getElementById("btn-spinner");
const platformPills = document.querySelectorAll(".platform-pill");
const cookieSelect = document.getElementById("cookie-select");
const toastContainer = document.getElementById("toast-container");

const errorAlert = document.getElementById("error-alert");
const errorSourceBadge = document.getElementById("error-source-badge");
const errorSourceIcon = document.getElementById("error-source-icon");
const errorSourceText = document.getElementById("error-source-text");
const errorCodeChip = document.getElementById("error-code-chip");
const errorTitle = document.getElementById("error-title");
const errorMessage = document.getElementById("error-message");
const errorHintBox = document.getElementById("error-hint-box");
const errorHintText = document.getElementById("error-hint-text");
const errorTechDetails = document.getElementById("error-tech-details");
const errorRawText = document.getElementById("error-raw-text");
const btnDismissError = document.getElementById("btn-dismiss-error");

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
const btnPauseDownload = document.getElementById("btn-pause-download");
const btnPauseText = document.getElementById("btn-pause-text");
const iconPause = document.getElementById("icon-pause");
const iconResume = document.getElementById("icon-resume");
const appVersionIndicator = document.getElementById("app-version-indicator");
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
let isDownloadPaused = false;
let isBatchMode = false;

// Helper: Format Bytes to human readable string
function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i >= 2 ? 1 : 0)} ${units[i]}`;
}

// Micro-Toasts System Helper
function showToast(message, type = "info", duration = 3500) {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px) scale(0.96)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// Convert technical errors to clear, categorized layman explanations
function formatLaymanError(errOrMsg) {
  let rawMsg = typeof errOrMsg === "string" ? errOrMsg : ((errOrMsg && errOrMsg.message) || String(errOrMsg));
  let code = (errOrMsg && errOrMsg.code) || "UNKNOWN";
  let hint = (errOrMsg && errOrMsg.hint) || "";
  let source = (errOrMsg && errOrMsg.source) || "platform";

  // Clean raw ANSI codes or URL dumps if present
  let clean = (rawMsg || "").replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '').trim();
  const lower = clean.toLowerCase();

  let title = "Unable to Process Video";
  let laymanMessage = clean;

  // Platform/YouTube Specific Checks
  if (code === "BOT_CHECK" || lower.includes("not a bot") || lower.includes("bot verification") || lower.includes("sign in to confirm")) {
    source = "platform";
    code = "BOT_CHECK";
    title = "YouTube Human Verification Required";
    laymanMessage = "YouTube is asking to confirm you are a real person and not an automated program.";
    if (!hint) hint = "This video requires platform authentication. Verify the URL is publicly accessible or playable in your web browser.";
  } else if (code === "PRIVATE_VIDEO" || lower.includes("private video") || lower.includes("this video is private")) {
    source = "platform";
    code = "PRIVATE_VIDEO";
    title = "Private Video on YouTube";
    laymanMessage = "The creator has set this video to private. It is only accessible to invited viewers.";
    if (!hint) hint = "If you have permission to view this video, verify you are logged in to YouTube in your browser.";
  } else if (code === "AGE_RESTRICTED" || lower.includes("age-restricted") || lower.includes("confirm your age") || lower.includes("sign in to view")) {
    source = "platform";
    code = "AGE_RESTRICTED";
    title = "Age-Restricted Video";
    laymanMessage = "YouTube requires a signed-in account over 18 to view this content.";
    if (!hint) hint = "This video is age-restricted. Please ensure the link is playable in your default web browser.";
  } else if (code === "GEO_BLOCKED" || lower.includes("available in your country") || lower.includes("geo-restricted") || lower.includes("blocked it in your country")) {
    source = "platform";
    code = "GEO_BLOCKED";
    title = "Regional Restriction (Geo-Blocked)";
    laymanMessage = "The content creator has restricted this video in your geographical location.";
    if (!hint) hint = "Connect through a VPN server in a country where this video is permitted and try again.";
  } else if (code === "MEMBERS_ONLY" || lower.includes("members-only") || lower.includes("members only") || lower.includes("join this channel")) {
    source = "platform";
    code = "MEMBERS_ONLY";
    title = "Channel Members Only";
    laymanMessage = "This video is exclusively available to paid members of the YouTube channel.";
    if (!hint) hint = "This video is for channel members only. Please ensure your account has active membership access.";
  } else if (code === "LIVE_STREAM" || lower.includes("is a live stream") || lower.includes("live event will begin") || lower.includes("premieres in")) {
    source = "platform";
    code = "LIVE_STREAM";
    title = "Live Stream or Upcoming Premiere";
    laymanMessage = "This video is currently streaming live or has not premiered yet.";
    if (!hint) hint = "Live broadcasts cannot be downloaded while streaming. Please wait until the live stream concludes and the full video is published.";
  } 
  // Internet / Network Specific Checks
  else if (code === "RATE_LIMITED" || lower.includes("http error 429") || lower.includes("too many requests") || lower.includes("rate-limit")) {
    source = "network";
    code = "RATE_LIMITED";
    title = "Platform Temporarily Busy (Rate Limited)";
    laymanMessage = "The video platform is temporarily limiting requests from your IP address.";
    if (!hint) hint = "Wait 2 to 3 minutes before trying again, or select your signed-in browser to authenticate.";
  } else if (code === "CONNECTION_TIMEOUT" || lower.includes("timed out") || lower.includes("connection refused") || lower.includes("transporterror")) {
    source = "network";
    code = "CONNECTION_TIMEOUT";
    title = "Internet Connection Problem";
    laymanMessage = "Connection to the video host timed out or was refused.";
    if (!hint) hint = "Check your internet connection. If this platform (e.g. TikTok) is restricted in your region, you may need a VPN.";
  }
  // Local PC / System Specific Checks
  else if (code === "FFMPEG_MISSING" || (lower.includes("ffmpeg") && lower.includes("not found")) || lower.includes("ffprobe")) {
    source = "system";
    code = "FFMPEG_MISSING";
    title = "Video Processing Software Missing (FFmpeg)";
    laymanMessage = "FFmpeg is required on your computer to merge high-resolution video streams (1080p, 4K) and convert MP3s.";
    if (!hint) hint = "Click the '1-Click Install FFmpeg' button at the top banner to install it automatically on your PC.";
  } else if (code === "UNTRUSTED_MOUNT_POINT" || lower.includes("untrusted mount point") || lower.includes("winerror 448")) {
    source = "system";
    code = "UNTRUSTED_MOUNT_POINT";
    title = "Windows Path Junction Issue";
    laymanMessage = "Windows security blocked a path traversal due to an untrusted mount point (commonly from Node.js / NVM).";
    if (!hint) hint = "Reset NVM with 'nvm use <version>' as Administrator or check for broken junction links in your system PATH.";
  }
  // OmniDownloader Application / Engine Checks
  else if (code === "ENGINE_OUTDATED" || lower.includes("unable to extract") || lower.includes("signature extraction failed") || lower.includes("n challenge solving failed")) {
    source = "app";
    code = "ENGINE_OUTDATED";
    title = "Video Layout Changed (Engine Update Available)";
    laymanMessage = "The video platform recently updated its website structure or stream encryption.";
    if (!hint) hint = "The download engine can be refreshed automatically. Check for engine updates in settings.";
  }

  // Source display labels and icons
  const sourceConfig = {
    platform: { icon: "📺", text: "Platform (YouTube / Host) Issue" },
    network: { icon: "🌐", text: "Internet & Connection Issue" },
    system: { icon: "💻", text: "Your Computer (Setup / PC) Issue" },
    app: { icon: "⚙️", text: "OmniDownloader Engine Notice" }
  };

  const sc = sourceConfig[source] || sourceConfig.platform;

  return {
    source,
    sourceIcon: sc.icon,
    sourceText: sc.text,
    code,
    title,
    message: laymanMessage,
    hint,
    raw: clean
  };
}

// Helper: Show Categorized Layman Error Alert
function showError(errOrMsg) {
  const info = formatLaymanError(errOrMsg);

  if (errorSourceBadge) {
    errorSourceBadge.className = `error-source-badge source-${info.source}`;
    if (errorSourceIcon) errorSourceIcon.textContent = info.sourceIcon;
    if (errorSourceText) errorSourceText.textContent = info.sourceText;
  }

  if (errorCodeChip) {
    if (info.code && info.code !== "UNKNOWN") {
      errorCodeChip.textContent = info.code;
      errorCodeChip.style.display = "inline-block";
    } else {
      errorCodeChip.style.display = "none";
    }
  }

  if (errorTitle) errorTitle.textContent = info.title;
  if (errorMessage) errorMessage.textContent = info.message;

  if (errorHintBox && errorHintText) {
    if (info.hint) {
      errorHintText.textContent = info.hint;
      errorHintBox.style.display = "flex";
    } else {
      errorHintBox.style.display = "none";
    }
  }



  if (errorTechDetails && errorRawText) {
    if (info.raw && info.raw !== info.message) {
      errorRawText.textContent = info.raw;
      errorTechDetails.style.display = "block";
    } else {
      errorTechDetails.style.display = "none";
    }
  }

  errorAlert.style.display = "flex";
  errorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
}


// Helper: Clear Error Alert
function clearError() {
  errorAlert.style.display = "none";
  if (errorMessage) errorMessage.textContent = "";
  if (errorHintBox) errorHintBox.style.display = "none";
  if (errorTechDetails) errorTechDetails.style.display = "none";

}

if (btnDismissError) {
  btnDismissError.addEventListener("click", clearError);
}



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
        <span id="btn-download-text">Show in Folder</span>
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

// Batch Mode Toggle Handler
function setBatchMode(active) {
  isBatchMode = active;
  if (isBatchMode) {
    if (btnBatchToggle) btnBatchToggle.classList.add("active");
    if (batchToggleLabel) batchToggleLabel.textContent = "Single";
    if (urlInput) urlInput.style.display = "none";
    if (batchInput) {
      batchInput.style.display = "block";
      if (urlInput && urlInput.value) batchInput.value = urlInput.value;
      const firstUrl = extractUrlsFromText(batchInput.value)[0] || "";
      updatePlatformHighlights(firstUrl);
      batchInput.focus();
    }
    if (btnClear) btnClear.style.display = (batchInput && batchInput.value) ? "flex" : "none";
  } else {
    if (btnBatchToggle) btnBatchToggle.classList.remove("active");
    if (batchToggleLabel) batchToggleLabel.textContent = "Batch";
    if (batchInput) batchInput.style.display = "none";
    if (urlInput) {
      urlInput.style.display = "block";
      if (batchInput && batchInput.value) {
        urlInput.value = batchInput.value.split(/[\r\n]+/)[0].trim() || "";
        updatePlatformHighlights(urlInput.value);
      }
      urlInput.focus();
    }
    if (btnClear) btnClear.style.display = (urlInput && urlInput.value) ? "flex" : "none";
  }
}

if (btnBatchToggle) {
  btnBatchToggle.addEventListener("click", () => {
    setBatchMode(!isBatchMode);
  });
}

// Extract clean URLs from single or multi-line text
function extractUrlsFromText(rawText) {
  if (!rawText) return [];
  const lines = rawText.split(/[\r\n,]+/).map(s => s.trim()).filter(Boolean);
  const urls = [];
  for (const line of lines) {
    const httpMatches = line.match(/https?:\/\/[^\s]+/gi);
    if (httpMatches) {
      urls.push(...httpMatches);
    } else {
      const token = line.trim();
      if (token.includes(".") && !token.includes(" ")) {
        urls.push(`https://${token}`);
      }
    }
  }
  return [...new Set(urls)];
}

// Input clear button toggle
if (urlInput) {
  urlInput.addEventListener("input", () => {
    if (btnClear) {
      btnClear.style.display = urlInput.value ? "flex" : "none";
    }
  });

  urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleUrlSubmission(e);
    }
  });
}

if (batchInput) {
  batchInput.addEventListener("input", () => {
    if (btnClear) {
      btnClear.style.display = batchInput.value ? "flex" : "none";
    }
    const firstUrl = extractUrlsFromText(batchInput.value)[0] || "";
    updatePlatformHighlights(firstUrl);
  });

  batchInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleUrlSubmission(e);
    }
  });
}

if (btnClear) {
  btnClear.addEventListener("click", () => {
    if (urlInput) urlInput.value = "";
    if (batchInput) batchInput.value = "";
    btnClear.style.display = "none";
    updatePlatformHighlights("");
    if (isBatchMode && batchInput) batchInput.focus();
    else if (urlInput) urlInput.focus();
  });
}

// Global keyboard shortcuts
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (urlInput) urlInput.value = "";
    if (batchInput) batchInput.value = "";
    if (btnClear) btnClear.style.display = "none";
    updatePlatformHighlights("");
    clearError();
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    if (isBatchMode && batchInput) {
      batchInput.focus();
      batchInput.select();
    } else if (urlInput) {
      urlInput.focus();
      urlInput.select();
    }
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

if (urlInput) {
  urlInput.addEventListener("input", (e) => {
    updatePlatformHighlights(e.target.value);
  });
}

// Paste button handler with smart batch detection and desktop fallback
if (btnPaste) {
  btnPaste.addEventListener("click", async () => {
    let text = "";

    // 1. Try modern browser clipboard API
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        text = await navigator.clipboard.readText();
      }
    } catch (err) {
      console.warn("Direct clipboard read blocked by browser permissions:", err);
    }

    // 2. Seamless native desktop backend fallback if browser blocked clipboard
    if (!text || !text.trim()) {
      try {
        text = await getClipboardText();
      } catch (err) {
        console.warn("Backend clipboard fallback notice:", err);
      }
    }

    const trimmed = (text || "").trim();
    if (trimmed) {
      const urls = extractUrlsFromText(trimmed);
      if (urls.length > 1) {
        setBatchMode(true);
        if (batchInput) {
          batchInput.value = urls.join("\n");
          updatePlatformHighlights(urls[0]);
        }
        showToast(`Pasted ${urls.length} links into Batch Mode`, "info", 2000);
      } else if (isBatchMode && batchInput) {
        batchInput.value = trimmed;
        updatePlatformHighlights(trimmed);
        showToast("Pasted batch links from clipboard", "info", 1500);
      } else {
        if (urlInput) {
          urlInput.value = trimmed;
          updatePlatformHighlights(trimmed);
        }
        showToast("Pasted from clipboard", "info", 1500);
      }
      if (btnClear) btnClear.style.display = "flex";
      return;
    }

    // 3. Fallback: focus input and inform user
    const target = (isBatchMode && batchInput) ? batchInput : urlInput;
    if (target) {
      target.focus();
      target.select();
    }
    showToast("Clipboard is empty or inaccessible. Press Ctrl+V to paste.", "info", 3000);
  });
}

// Unified URL & Batch Submission Handler
async function handleUrlSubmission(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  clearError();

  const currentText = ((isBatchMode && batchInput) ? batchInput.value : (urlInput ? urlInput.value : "")) || "";
  const extracted = extractUrlsFromText(currentText);

  if (extracted.length === 0) {
    showError("Please enter at least one valid video or playlist URL.");
    if (isBatchMode && batchInput) batchInput.focus();
    else if (urlInput) urlInput.focus();
    return;
  }

  // If multiple URLs entered in single mode, auto-switch to batch mode
  if (!isBatchMode && extracted.length > 1) {
    setBatchMode(true);
    if (batchInput) batchInput.value = extracted.join("\n");
    showToast(`Detected ${extracted.length} URLs - switched to Batch Mode`, "info");
  }

  setLoading(true);
  mediaCard.style.display = "none";
  progressCard.style.display = "none";

  try {
    const cookieBrowser = cookieSelect ? cookieSelect.value : null;
    let info;
    if (extracted.length > 1) {
      info = await fetchBatchMediaInfo(extracted, cookieBrowser);
    } else {
      const singleUrl = extracted[0];
      if (urlInput) urlInput.value = singleUrl;
      updatePlatformHighlights(singleUrl);
      info = await fetchMediaInfo(singleUrl, cookieBrowser);
    }
    currentMedia = info;
    renderMediaInfo(info);
  } catch (err) {
    showError(err);
  } finally {
    setLoading(false);
  }
}

if (urlForm) {
  urlForm.addEventListener("submit", handleUrlSubmission);
}
if (btnSubmit) {
  btnSubmit.addEventListener("click", handleUrlSubmission);
}

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
  } else if (platformName === "BATCH") {
    platformBadge.style.color = "#a855f7";
    platformBadge.style.borderColor = "rgba(168, 85, 247, 0.4)";
    platformBadge.style.background = "rgba(168, 85, 247, 0.12)";
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
    const isBatch = (info.platform === "batch");
    mediaBadge.textContent = isBatch ? "BATCH" : "PLAYLIST";
    mediaBadge.style.color = isBatch ? "#a855f7" : "#7928ca";
    mediaBadge.style.borderColor = isBatch ? "rgba(168, 85, 247, 0.4)" : "rgba(121, 40, 202, 0.4)";
    mediaBadge.style.background = isBatch ? "rgba(168, 85, 247, 0.15)" : "rgba(121, 40, 202, 0.15)";
    mediaDuration.textContent = `${info.item_count} Items`;

    // Render playlist items with item-level size badge
    playlistCount.textContent = isBatch ? `Batch Items (${info.item_count})` : `Playlist Items (${info.item_count})`;
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

  const isBatch = currentMedia && currentMedia.platform === "batch";
  const typeName = isBatch ? "Batch" : "Playlist";
  const sizeText = totalBytes > 0 ? ` • ~${formatBytes(totalBytes)}` : "";
  const label = `Download ${typeName} (${selectedCount} Selected${sizeText})`;
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
      batchItems: (currentMedia.platform === "batch") ? currentMedia.items : null,
      playlistTitle: currentMedia.title,
      quality,
      cookieBrowser,
      downloadDir: downloadDir || null,
    });

    currentTaskId = res.task_id;
    showProgressView(currentTaskId);
  } catch (err) {
    showError(err);
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

  // Lock progress size denominator to expected quality format
  const selectedQuality = qualitySelect ? qualitySelect.value : "best";
  const lockedTotalFormatted = (currentMedia && currentMedia.quality_sizes_formatted && currentMedia.quality_sizes_formatted[selectedQuality])
    || (currentMedia && currentMedia.filesize_formatted)
    || null;

  // Set initial estimated size
  if (progressSize) {
    progressSize.textContent = lockedTotalFormatted ? `Size: ${lockedTotalFormatted}` : "Size: Calculating...";
  }

  // Display and reset Cancel and Pause buttons
  isDownloadPaused = false;
  if (btnPauseDownload) {
    btnPauseDownload.style.display = "inline-flex";
    btnPauseDownload.classList.remove("is-paused");
    if (btnPauseText) btnPauseText.textContent = "Pause";
    if (iconPause) iconPause.style.display = "inline";
    if (iconResume) iconResume.style.display = "none";
  }

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

      if (data.status === "paused") {
        isDownloadPaused = true;
        progressBarFill.style.background = "linear-gradient(90deg, #f59e0b, #fbbf24)";
        progressSpeed.textContent = "Speed: Paused";
        if (btnPauseDownload) {
          btnPauseDownload.classList.add("is-paused");
          if (btnPauseText) btnPauseText.textContent = "Resume";
          if (iconPause) iconPause.style.display = "none";
          if (iconResume) iconResume.style.display = "inline";
        }
      } else if (data.status === "downloading" && isDownloadPaused) {
        isDownloadPaused = false;
        progressBarFill.style.background = "linear-gradient(90deg, #00d2ff, #00f0b5)";
        if (btnPauseDownload) {
          btnPauseDownload.classList.remove("is-paused");
          if (btnPauseText) btnPauseText.textContent = "Pause";
          if (iconPause) iconPause.style.display = "inline";
          if (iconResume) iconResume.style.display = "none";
        }
      }

      // Update real-time downloaded vs locked total size
      if (progressSize) {
        const dlStr = (data.downloaded_bytes && data.downloaded_bytes > 0) ? formatBytes(data.downloaded_bytes) : null;
        const totStr = lockedTotalFormatted || ((data.total_bytes && data.total_bytes > 0) ? formatBytes(data.total_bytes) : null);
        if (dlStr && totStr) {
          progressSize.textContent = `Size: ${dlStr} / ${totStr}`;
        } else if (dlStr) {
          progressSize.textContent = `Size: ${dlStr}`;
        } else if (totStr) {
          progressSize.textContent = `Size: ${totStr}`;
        }
      }

      if (data.current_item) {
        progressItemTitle.textContent = data.current_item;
      }

      // Hide cancel & pause buttons if completed or 100%
      if (data.status === "completed" || pct >= 100) {
        if (btnCancelDownload) btnCancelDownload.style.display = "none";
        if (btnPauseDownload) btnPauseDownload.style.display = "none";
      }

      setDownloadButtonState("downloading", `Downloading (${pct.toFixed(0)}%)...`);
    },
    onComplete: (data) => {
      if (btnCancelDownload) btnCancelDownload.style.display = "none";
      if (btnPauseDownload) btnPauseDownload.style.display = "none";
      progressBarFill.style.width = "100%";
      progressPercentage.textContent = "100%";
      progressSpeed.textContent = "Speed: Complete";
      progressEta.textContent = "ETA: Done";
      progressItemTitle.textContent = "Download completed successfully!";

      if (progressSize) {
        const finalSize = (data.total_bytes && data.total_bytes > 0) ? formatBytes(data.total_bytes) : lockedTotalFormatted;
        if (finalSize) {
          progressSize.textContent = `Total: ${finalSize}`;
        }
      }

      // Reveal post-download actions
      progressActions.style.display = "flex";

      // Transform button to Open / Play File
      setDownloadButtonState("completed");
    },
    onCancel: (data) => {
      if (btnCancelDownload) btnCancelDownload.style.display = "none";
      if (btnPauseDownload) btnPauseDownload.style.display = "none";
      progressBarFill.style.width = "100%";
      progressBarFill.style.background = "#f59e0b";
      progressPercentage.textContent = "Cancelled";
      progressSpeed.textContent = "Speed: --";
      progressEta.textContent = "ETA: --";
      progressItemTitle.textContent = "Download was cancelled.";
      setDownloadButtonState("ready");
      showToast("Download was cancelled.", "info");
    },
    onError: (err) => {
      if (btnCancelDownload) btnCancelDownload.style.display = "none";
      if (btnPauseDownload) btnPauseDownload.style.display = "none";
      showError(err);
      progressItemTitle.textContent = "Download failed.";
      progressBarFill.style.background = "#ef4444";
      progressPercentage.textContent = "Failed";
      setDownloadButtonState("ready");
    },
  });

  currentTracker.start();
}

// Pause / Resume Download Click Handler
if (btnPauseDownload) {
  btnPauseDownload.addEventListener("click", async () => {
    if (!currentTaskId) return;
    try {
      if (!isDownloadPaused) {
        await pauseTask(currentTaskId);
        isDownloadPaused = true;
        progressBarFill.style.background = "linear-gradient(90deg, #f59e0b, #fbbf24)";
        progressSpeed.textContent = "Speed: Paused";
        btnPauseDownload.classList.add("is-paused");
        if (btnPauseText) btnPauseText.textContent = "Resume";
        if (iconPause) iconPause.style.display = "none";
        if (iconResume) iconResume.style.display = "inline";
        showToast("Download paused.", "info", 1500);
      } else {
        await resumeTask(currentTaskId);
        isDownloadPaused = false;
        progressBarFill.style.background = "linear-gradient(90deg, #00d2ff, #00f0b5)";
        progressSpeed.textContent = "Speed: Resuming...";
        btnPauseDownload.classList.remove("is-paused");
        if (btnPauseText) btnPauseText.textContent = "Pause";
        if (iconPause) iconPause.style.display = "inline";
        if (iconResume) iconResume.style.display = "none";
        showToast("Download resumed.", "info", 1500);
      }
    } catch (err) {
      console.warn("Pause/resume error:", err);
      showToast(err.message || "Failed to toggle pause.", "error");
    }
  });
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
    if (btnPauseDownload) btnPauseDownload.style.display = "none";
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

// "Show in Folder" action
if (btnOpenFolder) {
  btnOpenFolder.addEventListener("click", async () => {
    try {
      showToast("Opening folder...", "info");
      await openDownloadsFolder(currentTaskId);
    } catch (err) {
      console.error("Failed to open folder:", err);
      showError("Could not reveal file in folder.");
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

// ==========================================================================
// In-App Application Updater Controller
// ==========================================================================
const btnCheckUpdates = document.getElementById("btn-check-updates");
const updateBtnLabel = document.getElementById("update-btn-label");
const updateBadgeDot = document.getElementById("update-badge-dot");

const appUpdateModal = document.getElementById("app-update-modal");
const btnCloseUpdateModal = document.getElementById("btn-close-update-modal");
const btnUpdateLater = document.getElementById("btn-update-later");
const btnUpdateAction = document.getElementById("btn-update-action");
const btnUpdateActionText = document.getElementById("btn-update-action-text");
const btnUpdateGithubLink = document.getElementById("btn-update-github-link");
const btnUpdateCancel = document.getElementById("btn-update-cancel");

const updateCurrentVersion = document.getElementById("update-current-version");
const updateTargetVersion = document.getElementById("update-target-version");
const updateDateText = document.getElementById("update-date-text");
const updateSizeText = document.getElementById("update-size-text");
const updateNotesContent = document.getElementById("update-notes-content");

const updateDownloadDeck = document.getElementById("update-download-deck");
const updateDownloadStatusLabel = document.getElementById("update-download-status-label");
const updateDownloadPercentLabel = document.getElementById("update-download-percent-label");
const updateDownloadBarFill = document.getElementById("update-download-bar-fill");
const updateDownloadBytesText = document.getElementById("update-download-bytes-text");
const updateDownloadSpeedText = document.getElementById("update-download-speed-text");

let latestUpdateData = null;
let updatePollTimer = null;
let isUpdateDownloading = false;
let isUpdateReadyToInstall = false;

function formatReleaseNotes(markdown) {
  if (!markdown || !markdown.trim()) {
    return "<p>No release notes provided for this version.</p>";
  }
  
  const lines = markdown.split("\n");
  let html = "";
  let inList = false;

  for (let line of lines) {
    let trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      continue;
    }

    if (trimmed.startsWith("#")) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      const headingText = trimmed.replace(/^#+\s*/, "");
      html += `<div style="font-weight: 700; color: #fff; margin: 0.5rem 0 0.25rem;">${escapeHtml(headingText)}</div>`;
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      let itemText = trimmed.substring(2);
      itemText = escapeHtml(itemText)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>");
      html += `<li>${itemText}</li>`;
      continue;
    }

    if (inList) {
      html += "</ul>";
      inList = false;
    }
    let pText = escapeHtml(trimmed)
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
    html += `<p style="margin: 0.25rem 0;">${pText}</p>`;
  }

  if (inList) html += "</ul>";
  return html;
}

function openUpdateModal(data) {
  if (!appUpdateModal) return;

  if (updateCurrentVersion) {
    updateCurrentVersion.textContent = `v${data.current_version || "1.2.4"}`;
  }
  if (updateTargetVersion) {
    updateTargetVersion.textContent = data.tag_name || `v${data.latest_version}`;
  }
  if (updateDateText) {
    if (data.published_at) {
      try {
        const d = new Date(data.published_at);
        updateDateText.textContent = `Released: ${d.toLocaleDateString()}`;
      } catch (_) {
        updateDateText.textContent = "Released: Recent";
      }
    } else {
      updateDateText.textContent = "Released: Recent";
    }
  }
  if (updateSizeText) {
    updateSizeText.textContent = data.file_size ? `Size: ${formatBytes(data.file_size)}` : "Size: ~48 MB";
  }
  if (updateNotesContent) {
    updateNotesContent.innerHTML = formatReleaseNotes(data.release_notes);
  }
  if (btnUpdateGithubLink) {
    btnUpdateGithubLink.href = data.release_url || "https://github.com/Aniketkumar-01/socials_downloader/releases";
  }

  // Reset download state views if not actively running
  if (!isUpdateDownloading && !isUpdateReadyToInstall) {
    if (updateDownloadDeck) updateDownloadDeck.style.display = "none";
    if (btnUpdateCancel) btnUpdateCancel.style.display = "none";
    if (btnUpdateLater) btnUpdateLater.style.display = "inline-flex";
    if (btnUpdateAction) {
      btnUpdateAction.disabled = false;
      if (btnUpdateActionText) btnUpdateActionText.textContent = "Download & Install";
    }
  }

  appUpdateModal.style.display = "flex";
}

function closeUpdateModal() {
  if (!appUpdateModal) return;
  appUpdateModal.style.display = "none";
}

async function handleCheckForUpdates(manualClick = true) {
  if (!btnCheckUpdates) return;

  btnCheckUpdates.classList.add("is-checking");
  if (updateBtnLabel) updateBtnLabel.textContent = "Checking...";

  try {
    const data = await checkAppUpdates(manualClick);
    if (data.status === "success" && data.update_available) {
      latestUpdateData = data;
      btnCheckUpdates.classList.add("has-update");
      if (updateBadgeDot) updateBadgeDot.style.display = "block";

      if (manualClick) {
        openUpdateModal(data);
      }
    } else if (data.status === "success" && !data.update_available) {
      btnCheckUpdates.classList.remove("has-update");
      if (updateBadgeDot) updateBadgeDot.style.display = "none";

      if (manualClick) {
        showToast(`You're up to date! OmniDownloader v${data.current_version || "1.2.4"} is the latest version.`, "success");
      }
    } else {
      // Rate limited or other notice
      if (manualClick) {
        showToast(data.message || "Could not check for updates. Please try again later.", "error");
      }
    }
  } catch (err) {
    console.error("Update check failed:", err);
    if (manualClick) {
      showToast("Unable to reach update server. Check your internet connection.", "error");
    }
  } finally {
    btnCheckUpdates.classList.remove("is-checking");
    if (updateBtnLabel) updateBtnLabel.textContent = "Check for Updates";
  }
}

async function handleStartUpdate() {
  if (isUpdateReadyToInstall) {
    // 2nd stage: Trigger installation & restart
    try {
      if (btnUpdateAction) btnUpdateAction.disabled = true;
      if (btnUpdateActionText) btnUpdateActionText.textContent = "Restarting...";
      showToast("Launching installer and restarting OmniDownloader...", "info", 5000);
      await applyAppUpdate(latestUpdateData?.downloaded_path, true);
    } catch (err) {
      showToast(err.message || "Failed to launch installer.", "error");
      if (btnUpdateAction) btnUpdateAction.disabled = false;
      if (btnUpdateActionText) btnUpdateActionText.textContent = "Retry Install";
    }
    return;
  }

  if (!latestUpdateData || !latestUpdateData.download_url) {
    showToast("Update installer not directly downloadable. Opening release page...", "info");
    if (latestUpdateData?.release_url) {
      window.open(latestUpdateData.release_url, "_blank");
    }
    return;
  }

  // 1st stage: Start in-app download
  isUpdateDownloading = true;
  if (updateDownloadDeck) updateDownloadDeck.style.display = "flex";
  if (btnUpdateCancel) btnUpdateCancel.style.display = "inline-flex";
  if (btnUpdateLater) btnUpdateLater.style.display = "none";
  if (btnUpdateAction) btnUpdateAction.disabled = true;
  if (btnUpdateActionText) btnUpdateActionText.textContent = "Downloading...";

  try {
    await startAppUpdateDownload(
      latestUpdateData.download_url,
      latestUpdateData.file_size || 0,
      latestUpdateData.tag_name || "latest"
    );

    if (updatePollTimer) clearInterval(updatePollTimer);
    updatePollTimer = setInterval(async () => {
      try {
        const progress = await getAppUpdateProgress();
        if (progress.status === "downloading") {
          const pct = Math.min(100, Math.max(0, progress.percent || 0));
          if (updateDownloadPercentLabel) updateDownloadPercentLabel.textContent = `${pct.toFixed(0)}%`;
          if (updateDownloadBarFill) updateDownloadBarFill.style.width = `${pct}%`;
          if (updateDownloadStatusLabel) updateDownloadStatusLabel.textContent = "Downloading installer...";
          if (updateDownloadBytesText) {
            updateDownloadBytesText.textContent = `${formatBytes(progress.downloaded_bytes)} / ${formatBytes(progress.total_bytes)}`;
          }
          if (updateDownloadSpeedText) {
            updateDownloadSpeedText.textContent = progress.speed_str || "--";
          }
        } else if (progress.status === "completed") {
          clearInterval(updatePollTimer);
          updatePollTimer = null;
          isUpdateDownloading = false;
          isUpdateReadyToInstall = true;

          if (latestUpdateData) {
            latestUpdateData.downloaded_path = progress.file_path;
          }

          if (updateDownloadPercentLabel) updateDownloadPercentLabel.textContent = "100%";
          if (updateDownloadBarFill) updateDownloadBarFill.style.width = "100%";
          if (updateDownloadStatusLabel) {
            updateDownloadStatusLabel.textContent = "✓ Verified & Ready to Install";
          }
          if (updateDownloadSpeedText) updateDownloadSpeedText.textContent = "Completed";

          if (btnUpdateCancel) btnUpdateCancel.style.display = "none";
          if (btnUpdateAction) {
            btnUpdateAction.disabled = false;
            if (btnUpdateActionText) btnUpdateActionText.textContent = "Install & Restart Now";
          }
          showToast("Update downloaded! Click 'Install & Restart Now' to finish.", "success", 4000);
        } else if (progress.status === "failed") {
          clearInterval(updatePollTimer);
          updatePollTimer = null;
          isUpdateDownloading = false;
          if (updateDownloadStatusLabel) {
            updateDownloadStatusLabel.textContent = `Download Failed: ${progress.error || "Network error"}`;
          }
          if (btnUpdateAction) {
            btnUpdateAction.disabled = false;
            if (btnUpdateActionText) btnUpdateActionText.textContent = "Retry Download";
          }
          if (btnUpdateCancel) btnUpdateCancel.style.display = "none";
          if (btnUpdateLater) btnUpdateLater.style.display = "inline-flex";
          showToast(`Download failed: ${progress.error || "Network error"}`, "error");
        } else if (progress.status === "cancelled") {
          clearInterval(updatePollTimer);
          updatePollTimer = null;
          isUpdateDownloading = false;
          if (updateDownloadDeck) updateDownloadDeck.style.display = "none";
          if (btnUpdateCancel) btnUpdateCancel.style.display = "none";
          if (btnUpdateLater) btnUpdateLater.style.display = "inline-flex";
          if (btnUpdateAction) {
            btnUpdateAction.disabled = false;
            if (btnUpdateActionText) btnUpdateActionText.textContent = "Download & Install";
          }
          showToast("Update download cancelled.", "info");
        }
      } catch (pollErr) {
        console.error("Progress poll error:", pollErr);
      }
    }, 500);

  } catch (err) {
    isUpdateDownloading = false;
    showToast(err.message || "Could not start download.", "error");
    if (btnUpdateAction) {
      btnUpdateAction.disabled = false;
      if (btnUpdateActionText) btnUpdateActionText.textContent = "Download & Install";
    }
    if (btnUpdateCancel) btnUpdateCancel.style.display = "none";
    if (btnUpdateLater) btnUpdateLater.style.display = "inline-flex";
  }
}

async function handleCancelUpdate() {
  try {
    await cancelAppUpdate();
  } catch (err) {
    console.warn("Cancel update error:", err);
  }
}

// Attach Event Listeners
if (btnCheckUpdates) {
  btnCheckUpdates.addEventListener("click", () => handleCheckForUpdates(true));
}
if (btnCloseUpdateModal) {
  btnCloseUpdateModal.addEventListener("click", closeUpdateModal);
}
if (btnUpdateLater) {
  btnUpdateLater.addEventListener("click", closeUpdateModal);
}
if (appUpdateModal) {
  appUpdateModal.addEventListener("click", (e) => {
    if (e.target === appUpdateModal && !isUpdateDownloading) {
      closeUpdateModal();
    }
  });
}
if (btnUpdateAction) {
  btnUpdateAction.addEventListener("click", handleStartUpdate);
}
if (btnUpdateCancel) {
  btnUpdateCancel.addEventListener("click", handleCancelUpdate);
}

// Non-blocking background silent update check on startup (delayed 3.5s)
setTimeout(() => {
  handleCheckForUpdates(false);
}, 3500);

// ==========================================================================
// Process Lifetime & Window Closure Handlers
// ==========================================================================
async function sendHeartbeat() {
  try {
    const token = await syncAuthToken();
    const url = token ? `/api/heartbeat?token=${encodeURIComponent(token)}` : "/api/heartbeat";
    const res = await fetch(url, { method: "POST" });
    if (res.ok) {
      const serverStatusIndicator = document.getElementById("server-status-indicator");
      if (serverStatusIndicator && !serverStatusIndicator.classList.contains("active")) {
        serverStatusIndicator.classList.add("active");
        const label = serverStatusIndicator.querySelector(".node-label");
        if (label) label.textContent = "Server Ready";
      }
    }
  } catch (_) {
    const serverStatusIndicator = document.getElementById("server-status-indicator");
    if (serverStatusIndicator && serverStatusIndicator.classList.contains("active")) {
      serverStatusIndicator.classList.remove("active");
      const label = serverStatusIndicator.querySelector(".node-label");
      if (label) label.textContent = "Reconnecting...";
    }
  }
}

// Initial ping + 3.0s recurring interval
sendHeartbeat();
setInterval(sendHeartbeat, 3000);

// Ping immediately whenever window or tab regains focus or visibility
window.addEventListener("focus", sendHeartbeat);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    sendHeartbeat();
  }
});

// Notify backend with 15s grace period when window closes
window.addEventListener("pagehide", () => {
  const token = window.__AUTH_TOKEN__ || "";
  const shutdownUrl = `/api/shutdown?token=${encodeURIComponent(token)}`;
  if (navigator.sendBeacon) {
    navigator.sendBeacon(shutdownUrl);
  } else {
    fetch(shutdownUrl, { method: "POST", keepalive: true }).catch(() => {});
  }
});

// ==========================================================================
// Application Version Display & Click-to-Check Handler
// ==========================================================================
async function initAppVersionDisplay() {
  try {
    const data = await getAppVersion();
    if (data && data.version && appVersionIndicator) {
      appVersionIndicator.textContent = `v${data.version}`;
    }
  } catch (_) {}
}

initAppVersionDisplay();

if (appVersionIndicator) {
  appVersionIndicator.style.cursor = "pointer";
  appVersionIndicator.addEventListener("click", () => {
    handleCheckForUpdates(true);
  });
}
