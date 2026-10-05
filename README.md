# OmniDownloader - Universal Video & Playlist Downloader

A modern, fast, local-first web application to download videos, Reels, Shorts, and playlists from YouTube, Instagram, TikTok, Twitter / X, Bilibili, and more at full quality with real-time download progress and original titles.

---

## ✨ Features

- **Universal Multi-Platform Support**: Download videos, Reels, and clips from:
  - **YouTube** (Videos, Shorts, Playlists)
  - **Instagram** (Reels, Posts, Videos)
  - **TikTok** (HD Videos without watermarks when available)
  - **Twitter / X** (Video tweets)
  - **Bilibili** (Videos & Bangumi)
  - **Facebook & Reddit**
- **Original Title Preservation**: Automatically retains the authentic media title as the file name, safely sanitized for Windows filesystems.
- **Playlist & Batch Support**: Automatically detects playlists, extracts constituent items, and lets you select specific videos or batch download all into a dedicated folder.
- **Live Real-Time Progress Bar**: Powered by dual-mode Server-Sent Events (SSE) and reactive polling tracking percentage, download speed (MB/s), and estimated time remaining (ETA).
- **Dual Delivery**:
  - Automatically saves directly to your local `downloads/` directory.
  - "Show in Folder" button opens the file in Windows Explorer, plus a "Save File" direct browser download button.
- **Sleek Dark UI**: Built with responsive modern CSS, glowing accents, and typography (`Outfit`).

---

## 🚀 Quick Start (Windows 10 / Windows 11)

### Option 1: 🖥️ Launch as Windows PC Desktop Application (Recommended)
Double-click **`OmniDownloader.vbs`** in this folder:
- Launches as a **full-fledged standalone Windows desktop application**.
- **No browser tabs, no address bars, and no terminal console window** popping up.
- Integrates with Windows 10/11 snap layouts, taskbar, and native window controls.

> **💡 Tip**: Double-click **`create_desktop_shortcut.vbs`** to place an **OmniDownloader** shortcut directly onto your Windows Desktop!

### Option 2: Double-click launcher (`start.bat`)
Double-click `start.bat`. It will verify Python, prepare `venv`, install dependencies, and launch the standalone desktop app window.

### Option 3: PowerShell
Run:
```powershell
.\start.ps1
```

### Option 4: Python Desktop Controller
```powershell
.\venv\Scripts\activate
python desktop.py
```

---

## 📁 Project Layout

```
d:/AG/yt/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server, endpoints, and SSE routes
│   │   ├── downloader.py        # yt-dlp metadata extractor & format builder
│   │   ├── task_manager.py      # Background worker with progress hooks
│   │   ├── models.py            # Pydantic request & response schemas
│   │   └── config.py            # Paths, settings, and Windows sanitization
│   ├── tests/
│   │   └── test_downloader.py  # Unit test suite
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── index.html               # Main application layout
│   ├── css/
│   │   └── styles.css           # Premium dark-theme stylesheet
│   └── js/
│       ├── app.js               # Frontend controller & UI state
│       ├── api.js               # Backend REST API client
│       └── progress.js          # SSE event listener
├── downloads/                   # Default storage for downloaded videos
├── SPEC.md                      # Detailed technical specification
├── tasks/
│   ├── plan.md                  # Implementation roadmap
│   └── todo.md                  # Completed task checklist
├── start.bat                    # Windows Batch quick launcher
└── start.ps1                    # PowerShell launcher
```

---

## 🛠️ Note on FFmpeg
To merge separate video and audio streams for 1080p+ resolution or convert audio to MP3, `ffmpeg` is recommended on your system PATH:
- If you use `winget`: `winget install Gyan.FFmpeg`
- Or via `scoop`: `scoop install ffmpeg`
- Or via `choco`: `choco install ffmpeg`

---

## 🌐 Regional Restrictions & Country Bans (VPN Advisory)
> [!WARNING]
> **Platform Bans (e.g., TikTok in India)**:
> If an online platform is banned or restricted by your country's government or Internet Service Providers (ISPs), direct connection attempts will silently time out (`Connection to www.tiktok.com timed out`).
> 
> To download media from banned or region-locked platforms:
> 1. Turn on a **VPN** connected to an unrestricted region (e.g., Cloudflare WARP, ProtonVPN, Windscribe).
> 2. Or configure an HTTP/SOCKS5 proxy before launching OmniDownloader.
