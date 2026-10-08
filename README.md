<div align="center">

# ⚡ OmniDownloader

**Universal High-Performance Video, Audio & Playlist Downloader for Windows & Android**

*Download videos, Reels, Shorts, and entire playlists from YouTube, Instagram, TikTok, X (Twitter), Bilibili, and 1,000+ sites at full quality with real-time SSE progress.*

[![Latest Release](https://img.shields.io/github/v/release/Aniketkumar-01/socials_downloader?color=00f0b5&label=Release&style=flat-square)](https://github.com/Aniketkumar-01/socials_downloader/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-00d2ff.svg?style=flat-square)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0e121a.svg?style=flat-square&logo=windows)](https://github.com/Aniketkumar-01/socials_downloader/releases)
[![Platform: Android](https://img.shields.io/badge/Platform-Android%207.0%2B-3DDC84.svg?style=flat-square&logo=android)](android/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)

[**Download Windows Installer**](https://github.com/Aniketkumar-01/socials_downloader/releases/latest) • [**Android App Guide**](android/README.md) • [**Architecture & Documentation**](DOCUMENTATION.md) • [**Features**](#-features) • [**Quick Start**](#-quick-start-no-python-required) • [**FFmpeg Setup**](#-ffmpeg-setup-for-1080p-4k--mp3)

</div>

---

## ✨ Features

- **🌐 Universal Platform Coverage**: Extract media from:
  - **YouTube**: Videos, Shorts, Channels, and Full Playlists (up to 4K/8K 60fps).
  - **Instagram**: Reels, Stories, Posts, and Carousel Clips.
  - **TikTok**: High-definition video without platform watermarks.
  - **Twitter / X**: Embedded video tweets and media threads.
  - **Bilibili**: High-resolution video and Bangumi anime episodes.
  - **Facebook, Reddit, Pinterest, Twitch, Vimeo, SoundCloud**, and 1,000+ supported sites.
- **🏷️ Original Authentic Titles**: Preserves the original media title, author, and metadata while safely sanitizing Windows-reserved filesystem characters (`:`, `*`, `?`, `"`, `<`, `>`, `|`, `CON`, `NUL`, etc.).
- **📑 Smart Playlist & Batch Downloader**: Automatically detects playlist URLs, parses constituent videos, provides granular checkboxes for selective item downloading, or downloads entire collections into a dedicated folder with 1 click.
- **⚡ Real-Time Progress Stream**: Powered by Server-Sent Events (SSE) with millisecond-precision tracking for progress percentage, live download speed (MB/s), downloaded size, and dynamic Estimated Time of Arrival (ETA).
- **🎨 Sleek Dark Cyber-Obsidian UI**: Modern, responsive user interface built with smooth gradients, vibrant glowing accents, and high-legibility typography (`Outfit` and `JetBrains Mono`).
- **🛡️ Local-First & Privacy-Focused**: Runs completely locally on your PC. No external tracking, no cloud telemetry, no account registration required.
- **🍪 Bot Challenge Bypass**: Integrated cookie manager supports importing Netscape `cookies.txt` or auto-probing your local Edge/Chrome browser profiles to seamlessly bypass YouTube "Sign in to confirm you're not a bot" verifications.

---

## 📦 Quick Start (No Python Required!)

For regular Windows users, OmniDownloader is distributed as a pre-compiled Windows application that runs out-of-the-box:

### 1. Download
Visit the [**Latest GitHub Releases**](https://github.com/Aniketkumar-01/socials_downloader/releases/latest) page and download:
- **`OmniDownloader-Setup.exe` (Recommended)**:
  - Modern Windows Setup wizard.
  - Adds **OmniDownloader** to your **Start Menu** and makes it searchable via Windows Search (<kbd>Win</kbd> + type `"Omni"`).
  - Places a desktop shortcut.
  - Installs cleanly into your user profile (no Administrator prompt required).
  - Easily uninstalled or updated via **Windows Settings > Installed apps**.
- **`OmniDownloader.exe` (Portable)**:
  - Single standalone portable binary. No installation required—double-click and run immediately from any folder or USB drive.

### 2. Usage
1. Open **OmniDownloader**.
2. Paste any video, Reel, or playlist link into the input box.
3. Click **Fetch Details** (or press <kbd>Enter</kbd>).
4. Choose your preferred quality (`Best Available`, `1080p Full HD`, `720p HD`, `480p`, or `Audio (MP3)`).
5. Click **Download**!
6. Once finished, click **Show in Folder** to open the file directly in Windows Explorer.

---

## 🛠️ FFmpeg Setup (For 1080p, 4K & MP3)

Modern media platforms (like YouTube) store high-resolution video (1080p, 1440p, 4K) and audio in separate streams. Merging them into a single `.mp4` file or converting audio to `.mp3` requires **FFmpeg**.

OmniDownloader automatically detects FFmpeg on your system PATH or local application directories.

### Option A: Install via Windows Package Manager (Recommended)
Open PowerShell and run:
```powershell
winget install Gyan.FFmpeg
```

### Option B: Install via Chocolatey or Scoop
```powershell
choco install ffmpeg
# or
scoop install ffmpeg
```

### Option C: In-App 1-Click Installation
Click the **Settings** gear icon in OmniDownloader and use the built-in FFmpeg download utility.

---

## 🍪 Bypassing YouTube "Sign In to Confirm You're Not a Bot"

YouTube occasionally blocks anonymous requests from automated tools. OmniDownloader provides two foolproof solutions:

1. **Option 1 (Easiest)**: In the format selection card, open the **Authentication / Cookies** dropdown and choose your installed browser (e.g. `Edge`, `Chrome`, or `Firefox`). OmniDownloader will automatically use your existing browser session.
2. **Option 2 (Persistent `cookies.txt`)**: 
   - Export your cookies using any standard browser extension (such as *Get cookies.txt LOCALLY* for Chrome/Edge/Firefox).
   - Click the **Cookies / Auth** button in OmniDownloader and upload your exported `cookies.txt`.
   - Your cookies are stored securely on your local PC in `%LOCALAPPDATA%\OmniDownloader\cookies.txt` and never transmitted anywhere else.

---

## 🌐 Regional Bans & VPN Advisory

> [!WARNING]
> **Platform Bans (e.g., TikTok in India)**:
> If an online platform is banned or restricted by your country's government or Internet Service Providers (ISPs), connection attempts will silently time out (`Connection to www.tiktok.com timed out`).
> 
> To download media from banned or region-locked platforms:
> 1. Turn on a **VPN** connected to an unrestricted region (e.g., Cloudflare WARP, ProtonVPN, Windscribe).
> 2. Or configure a system HTTP/SOCKS5 proxy before launching OmniDownloader.

---

## 💻 Developer Quick Start

If you are a developer looking to run or contribute to OmniDownloader from source:

### Prerequisites
- Windows 10 or 11
- Python 3.10+
- Git

### 1. Clone Repository
```powershell
git clone https://github.com/Aniketkumar-01/socials_downloader.git
cd socials_downloader
```

### 2. Run with 1-Click Launcher
Double-click `start.bat`. This script will:
1. Automatically create a Python virtual environment (`venv`).
2. Install all required dependencies from `backend/requirements.txt`.
3. Launch the application in a standalone native desktop window.

### 3. Manual Startup
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run desktop launcher
python launcher.py
```

The web console will be accessible at: `http://localhost:8000`

---

## 🏗️ Building Windows Binaries Locally

You can compile standalone binaries using PyInstaller and Inno Setup:

```powershell
# 1. Install dependencies & PyInstaller
pip install -r backend/requirements.txt pyinstaller pillow

# 2. Generate application icon
python create_icon.py

# 3. Build standalone portable executable
pyinstaller --clean omnidownloader.spec

# 4. (Optional) Compile Inno Setup installer
iscc installer.iss
```

Compiled binaries will be created directly in `dist\`:
- `dist\OmniDownloader-Setup.exe`
- `dist\OmniDownloader.exe`

---

## 🔒 Security & Privacy Architecture

OmniDownloader is engineered with strict local security safeguards:
- **Localhost-Only Binding**: Backend server strictly binds to `127.0.0.1`, ignoring external network interfaces.
- **Dynamic Authentication Token**: All `/api/*` endpoints require a cryptographic `X-Auth-Token` generated at startup to prevent unauthorized browser tab access.
- **Cross-Site Attack Protection**: Requests with external `Origin` headers or `Sec-Fetch-Site: cross-site` are blocked with `403 Forbidden`.
- **Command Injection Prevention**: File launch and directory inspection calls use `os.startfile()` and token-safe `explorer.exe` process arguments without shell expansion (`shell=False`).
- **Path Traversal Guards**: Strict containment checks ensure all disk operations and file retrieval requests are confined within the user's active downloads folder.
- **Input Bounding**: Hard limits on URL lengths (2048 chars), directory paths (1000 chars), and playlist items (500 items ceiling) protect system memory against denial-of-service abuse.
- **Zero Telemetry**: No third-party analytics, ads, or external cloud requests.

---

## 📂 Project Structure

```
d:/AG/yt/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application, REST endpoints & SSE streams
│   │   ├── downloader.py        # yt-dlp metadata extraction & format resolution
│   │   ├── task_manager.py      # Async background download manager & progress hooks
│   │   ├── models.py            # Pydantic schemas, validation & length bounds
│   │   └── config.py            # Local storage paths, settings & filename sanitization
│   ├── tests/
│   │   ├── test_downloader.py  # Unit tests for metadata and extraction logic
│   │   ├── test_hardening.py   # Security test suite (tokens, origins, path traversal)
│   │   └── test_quality.py     # Quality tier selection & file size estimation tests
│   └── requirements.txt         # Pinned backend dependencies
├── frontend/
│   ├── index.html               # Main semantic HTML5 interface
│   ├── css/
│   │   └── styles.css           # Premium cyber-obsidian responsive styles
│   └── js/
│       ├── app.js               # UI interaction controller & state management
│       ├── api.js               # REST client with auth token synchronization
│       └── progress.js          # Real-time SSE progress monitor & fallback poller
├── .github/
│   └── workflows/
│       └── release.yml          # GitHub Actions workflow for automated Windows builds
├── launcher.py                  # Self-healing Windows desktop app launcher
├── omnidownloader.spec          # PyInstaller executable build specification
├── installer.iss                # Inno Setup 6 Windows installer compiler script
├── create_icon.py               # Vector-style high-resolution Windows icon generator
├── start.bat                    # 1-click Windows quick launcher
├── cookies.txt.example          # Safe Netscape cookies template example
├── DOCUMENTATION.md             # Architecture manual & API specifications
├── .gitignore                   # Git exclusion rules
└── LICENSE                      # MIT Open Source License
```

---

## ⚖️ Legal Disclaimer & Fair Use Notice

OmniDownloader is an open-source software tool intended strictly for personal, educational, and fair use purposes (such as offline archival of content you own, have created, or have explicit permission to download). 

Users are solely and independently responsible for ensuring compliance with applicable copyright laws, local regulations, and the respective platform's Terms of Service. OmniDownloader is not affiliated with, endorsed by, or sponsored by YouTube, Meta (Instagram/Facebook), TikTok (ByteDance), X Corp, Bilibili, or any other media provider.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
