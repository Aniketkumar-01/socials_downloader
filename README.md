<div align="center">

# ⚡ OmniDownloader

**Universal High-Performance Video, Audio & Playlist Downloader for Windows**

*Download videos, Reels, Shorts, and entire playlists from YouTube, Instagram, TikTok, X (Twitter), Bilibili, and 1,000+ sites with real-time SSE progress.*

[![Latest Release](https://img.shields.io/github/v/release/Aniketkumar-01/socials_downloader?color=00f0b5&label=Release&style=flat-square)](https://github.com/Aniketkumar-01/socials_downloader/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-00d2ff.svg?style=flat-square)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0e121a.svg?style=flat-square&logo=windows)](https://github.com/Aniketkumar-01/socials_downloader/releases)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)

[**Download Windows Installer**](https://github.com/Aniketkumar-01/socials_downloader/releases/latest) • [**Architecture & Documentation**](DOCUMENTATION.md) • [**Features**](#-features) • [**Quick Start**](#-quick-start-no-python-required) • [**FFmpeg Bundling**](#-built-in-ffmpeg-engine-1080p-4k--mp3) • [**Developer Guide**](#-developer-quick-start) • [**Security**](#-security--privacy-architecture)

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
- **🎨 Sleek Dark Cyber-Obsidian UI**: Modern, responsive user interface built with smooth gradients, vibrant glowing accents, and locally bundled typography (`Outfit` and `JetBrains Mono`) for 100% offline support.
- **🛡️ Local-First & Privacy-Focused**: Runs completely locally on your PC (`127.0.0.1`). No external tracking, no cloud telemetry, no account registration required.
- **🍪 Resilient Extraction**: Integrated cookie jar manager supports importing Netscape `cookies.txt` and provides privacy-preserving opt-in local browser session probing (Edge, Chrome, Firefox, Brave) to pass verification challenges.
- **🎬 Built-In FFmpeg Engine**: Bundles FFmpeg out-of-the-box via `imageio-ffmpeg` for lossless video stream-copy remuxing and 320kbps MP3 transcoding without manual installation.

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

## 🎬 Built-in FFmpeg Engine (1080p, 4K & MP3)

Modern media platforms (like YouTube) store high-resolution video (1080p, 1440p, 4K) and audio in separate DASH streams. Merging them into a single universal `.mp4` container or converting audio to `.mp3` requires **FFmpeg**.

OmniDownloader bundles FFmpeg directly inside both the installer and standalone executable via `imageio-ffmpeg`. No manual installation, `winget` commands, or system PATH modifications are required.

- **Video Merging**: Performed via lossless stream-copy remuxing (no re-encoding, preserving exact original stream quality).
- **Audio Extraction**: Converted to high-bitrate 320kbps MP3 with embedded metadata and full-resolution thumbnail cover art.

---

## 🍪 Resilient Extraction & Platform Verification Challenges

YouTube occasionally blocks anonymous automated requests. OmniDownloader provides two reliable solutions:

1. **Option 1 (Opt-In Local Browser Probing)**: 
   - Open **Settings** in OmniDownloader and toggle **Allow Local Browser Session Probing** (default is OFF for user privacy).
   - In the format selection card, choose your installed browser (e.g. `Edge`, `Chrome`, `Firefox`, `Brave`). OmniDownloader queries your existing browser session in read-only mode to pass the verification challenge.
2. **Option 2 (Persistent `cookies.txt`)**: 
   - Export your cookies using any standard browser extension (such as *Get cookies.txt LOCALLY* for Chrome/Edge/Firefox).
   - Upload your exported `cookies.txt` through the app.
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

### 2. Run with Automated Bootstrap Script
Execute `.\scripts\start.ps1` in PowerShell. This script will:
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

---

## 🏗️ Building Windows Binaries Locally

To compile your own standalone executable (`OmniDownloader.exe`) or Inno Setup installer (`OmniDownloader-Setup.exe`):

1. Ensure **Inno Setup 6** is installed (install via `winget install JRSoftware.InnoSetup` or `choco install innosetup`).
2. Run the unified build script:
   ```powershell
   .\scripts\build.ps1 -Target All
   ```
   *(Or specify `-Target Exe` or `-Target Installer`)*.
3. Your compiled artifacts will be output directly into the `dist\` folder:
   - `dist\OmniDownloader-Setup.exe`
   - `dist\OmniDownloader.exe`

---

## 🔒 Security & Privacy Architecture

OmniDownloader is engineered with strict local security safeguards:
- **Localhost-Only Binding**: Backend server strictly binds to `127.0.0.1` on a dynamically assigned ephemeral port (port 0).
- **Session Authentication Token**: All `/api/*` endpoints require a cryptographic `X-Omni-Token` generated at launcher startup. Requests without a valid token are rejected with `403 Forbidden`.
- **Host Header Validation**: Rejects requests whose `Host` header does not match `127.0.0.1:{port}` or `localhost:{port}`, mitigating DNS rebinding attacks.
- **Cross-Site Attack Protection**: Requests with external `Origin` headers or `Sec-Fetch-Site: cross-site` are blocked with `403 Forbidden`.
- **Command Injection Prevention**: Subprocess calls strictly enforce `shell=False` and list-based arguments. Windows Explorer reveals format switch strings safely without shell expansion.
- **Path Traversal Guards**: Strict containment checks ensure all disk operations and file retrieval requests are confined within the user's active downloads folder.
- **Input Bounding**: Hard limits on URL lengths (2048 chars), directory paths (1000 chars), and playlist items (500 items ceiling) protect system memory against denial-of-service abuse.
- **Zero Telemetry**: No third-party analytics, ads, or external cloud requests.

---

## 📂 Project Structure

```
OmniDownloader/
├── .github/
│   └── workflows/
│       └── release.yml          # GitHub Actions CI/CD (lint, test, build matrix)
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, REST endpoints, token & Host middleware
│   │   ├── downloader.py        # yt-dlp metadata extraction & resilient fallback logic
│   │   ├── task_manager.py      # Async background download manager & progress hooks
│   │   ├── models.py            # Pydantic schemas, validation, task & settings models
│   │   └── config.py            # Local storage paths, settings & filename sanitization
│   ├── tests/
│   │   ├── test_downloader.py  # Unit tests for metadata and extraction logic
│   │   ├── test_hardening.py   # Security test suite (tokens, Host rebinding, traversal)
│   │   └── test_quality.py     # Quality tier selection & file size estimation tests
│   └── requirements.txt         # Pinned backend dependencies
├── frontend/
│   ├── css/
│   │   └── styles.css           # Premium cyber-obsidian responsive styles
│   ├── fonts/                   # Bundled offline fonts (Outfit & JetBrains Mono)
│   ├── js/
│   │   ├── app.js               # UI interaction controller & settings modal
│   │   ├── api.js               # REST client with auth token synchronization
│   │   └── progress.js          # Real-time SSE progress monitor & fallback poller
│   └── index.html               # Semantic HTML5 single-page application
├── scripts/
│   ├── build.ps1                # Unified build script (Exe & Installer)
│   ├── release.ps1              # Unified release script (stage, commit, tag, push)
│   └── start.ps1                # 1-Click developer bootstrap script
├── tools/
│   ├── create_icon.py           # Asset generator for app.ico
│   └── download_fonts.py        # Offline font asset downloader
├── examples/
│   └── cookies.txt.example      # Safe Netscape cookies template example
├── assets/
│   └── app.ico                  # Application icon
├── .gitignore                   # Git ignore rules
├── DOCUMENTATION.md             # Comprehensive technical architecture manual
├── installer.iss                # Inno Setup 6 installer script
├── launcher.py                  # Standalone desktop bootstrap launcher
├── LICENSE                      # MIT Open Source License
├── omnidownloader.spec          # PyInstaller executable build specification
└── README.md                    # Repository landing page and user guide
```

---

## ⚖️ Legal / Responsible Use

OmniDownloader is an open-source utility designed for personal archival, educational research, and fair use of media content you have lawful rights or explicit permission to access. 

Users are solely and independently responsible for ensuring full compliance with applicable copyright laws, local regulations, and the respective platform's Terms of Service. OmniDownloader is not affiliated with, endorsed by, or sponsored by YouTube, Meta (Instagram/Facebook), TikTok (ByteDance), X Corp, Bilibili, or any other media provider.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
