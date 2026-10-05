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

## 📦 Standalone Executable (No Python Required!)

Users can run OmniDownloader without installing Python or dependencies:

1. Go to the [**GitHub Releases**](https://github.com/Aniketkumar-01/socials_downloader/releases) page.
2. Download **`OmniDownloader.exe`**.
3. Double-click **`OmniDownloader.exe`**.
4. The app will launch in your default web browser at `http://127.0.0.1:8000`.
5. Paste any video or playlist link and start downloading!

> **⚠️ Prerequisites for 1080p, 4K & MP3**:
> YouTube and major platforms split high-resolution streams into separate video and audio channels. Merging them requires **FFmpeg**.
> - You can install FFmpeg with **1-click** right inside the app interface.
> - Or run this command in terminal/PowerShell:
>   ```powershell
>   winget install Gyan.FFmpeg
>   ```

---

## 🛠️ Building the `.exe` Locally

To build your own standalone Windows executable from source:
1. Double-click **`build_exe.bat`** in this folder (or run `pyinstaller --clean omnidownloader.spec`).
2. The compiled binary will be placed at **`dist\OmniDownloader.exe`**.

---

## 🚀 Developer / Source Quick Start (Windows)

### Option 1: Double-click launcher (`start.bat`)
Double-click `start.bat`. It will prepare `venv`, install dependencies, and launch the application.

### Option 2: Run Python Desktop Launcher
```powershell
pip install -r backend/requirements.txt
python launcher.py
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
