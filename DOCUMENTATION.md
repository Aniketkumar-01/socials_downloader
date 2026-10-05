# ⚡ OmniDownloader — Comprehensive Technical Documentation & Architecture Manual

> **Version:** 1.3.0  
> **Target OS:** Windows 10 / 11 (x64)  
> **Architecture:** Local-First Micro-Service / Hybrid Desktop Client  
> **Repository:** [Aniketkumar-01/socials_downloader](https://github.com/Aniketkumar-01/socials_downloader)  
> **License:** MIT  

---

## Table of Contents
1. [Executive Summary & Core Philosophy](#1-executive-summary--core-philosophy)
2. [Technology Stack: What We Use & Why We Use It](#2-technology-stack-what-we-use--why-we-use-it)
3. [End-to-End System Architecture](#3-end-to-end-system-architecture)
   - [3.3 Repository File & Directory Structure](#33-repository-file--directory-structure)
4. [Backend Engineering & Module Breakdown](#4-backend-engineering--module-breakdown)
5. [Frontend Architecture & Cyber-Obsidian UI/UX Design System](#5-frontend-architecture--cyber-obsidian-uiux-design-system)
6. [Security Architecture & Threat Hardening](#6-security-architecture--threat-hardening)
7. [REST API & Real-Time SSE Protocol Specification](#7-rest-api--real-time-sse-protocol-specification)
8. [Media Extraction, Remuxing & Resilient Extraction Engine](#8-media-extraction-remuxing--resilient-extraction-engine)
9. [Build, Packaging & Distribution Pipeline](#9-build-packaging--distribution-pipeline)
10. [Operational Runbook, Edge Cases & Troubleshooting](#10-operational-runbook-edge-cases--troubleshooting)

---

## 1. Executive Summary & Core Philosophy

**OmniDownloader** is a high-performance, local-first Windows desktop media extraction and remuxing suite. It enables users to download high-definition video, audio, and playlists from YouTube, Instagram, TikTok, X (Twitter), Bilibili, and over 1,000 supported platforms with optimal fidelity (video stream merging uses lossless stream-copy remuxing without re-encoding, while audio conversion performs high-bitrate 320kbps MP3 transcoding), real-time byte-level telemetry, and zero cloud dependency.

### Core Engineering Principles
1. **100% Privacy & Local-First Execution**: The application runs entirely on the user's workstation (`127.0.0.1`). No media, URLs, telemetry, or user credentials ever touch an intermediary cloud server.
2. **Zero-Bloat Native Windows Experience**: Rather than shipping a 150MB+ Electron runtime with redundant Chromium instances, OmniDownloader leverages the operating system's native **Microsoft Edge WebView2** engine and Win32 APIs, keeping the installer lightweight and memory footprint minimal.
3. **Resilient Multi-Platform Extraction**: Social media platforms constantly evolve bot mitigations, rate limits, and client signatures. OmniDownloader embeds a multi-tier fallback architecture combining active web extractors, privacy-preserving opt-in local browser session probing, and mobile API client fallbacks.
4. **Defense in Depth**: Robust defenses against Windows-specific vulnerabilities, including path traversal, mount-point crashes (`WinError 448`), DOS device name injection (`CON`, `PRN`, `NUL`), Host header rebinding, and mandatory session token authentication.
5. **Cyber-Obsidian Aesthetic**: A state-of-the-art UI featuring deep obsidian dark tones, glowing neon mint/cyan accents, micro-animations, and high-legibility typography designed for clarity and visual delight.

---

## 2. Technology Stack: What We Use & Why We Use It

Every library, framework, and tool in OmniDownloader was deliberately chosen to balance performance, reliability, native Windows integration, and bundle size.

| Layer | Technology Selected | Alternatives Considered | Technical Rationale & Justification ("Why") |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | **Python 3.10+ (64-bit)** | Node.js, Go, Rust | Native compatibility with yt-dlp and Win32 APIs with high asynchronous I/O throughput. |
| **Web Server Framework** | **FastAPI + Starlette** | Flask, Django, Express | Asynchronous ASGI request handling, Pydantic v2 data validation, and native SSE streaming. |
| **ASGI Server** | **Uvicorn (h11 protocol)** | Hypercorn, Daphne, Gunicorn | High-performance asynchronous web server bound strictly to loopback in an isolated daemon thread. |
| **Data Validation** | **Pydantic v2** | Marshmallow, Cerberus | Rust-compiled validation core offering low deserialization latency and strict schema enforcement. |
| **Media Extraction** | **yt-dlp** | youtube-dl, pytube, custom scrapers | Community-standard extraction engine supporting over 1,000 platforms with active signature deciphering. |
| **Media Transcoding** | **FFmpeg (bundled via imageio-ffmpeg)** | libav, moviepy, handbrake | Industry-standard muxer required for DASH stream-copy video merging and 320kbps MP3 transcoding. |
| **Desktop Window GUI** | **PyWebView / Edge WebView2 App Mode** | Electron, Tauri, PyQt | Reuses native Windows Evergreen Edge WebView2 to eliminate heavy Chromium bundle overhead. |
| **Win32 Integration** | **PyWebView Dialogs + Win32 ctypes** | Tkinter, PowerShell STA, pywin32 | Native OS folder dialogs and Explorer reveals without heavy C-extensions or GUI toolkits. |
| **Frontend Framework** | **Vanilla ES6+ JavaScript** | React, Vue, Svelte | Zero build step and instant DOM execution using native browser fetch and EventSource APIs. |
| **Frontend Styling** | **Vanilla CSS3 (Design System)** | Tailwind CSS, Bootstrap | Custom CSS design tokens with hardware-accelerated transitions and zero compilation overhead. |
| **Typography** | **Local Fonts (`Outfit` & `JetBrains Mono`)** | Google Fonts CDN, system fonts | Bundled offline font files ensuring zero cloud network requests and consistent typography. |
| **Binary Compiler** | **PyInstaller** | Nuitka, cx_Freeze | Packages dependencies into a single windowed binary with UPX disabled for antivirus trust. |
| **Windows Installer** | **Inno Setup 6** | WiX Toolset, NSIS, MSIX | Standard enterprise Windows installer creating per-user non-admin setups with Start Menu integration. |
| **CI/CD Automation** | **GitHub Actions (`windows-latest`)** | AppVeyor, GitLab CI | Automated linting, pytest hardening tests, and release compilation on clean Windows runners. |

---

## 3. End-to-End System Architecture

OmniDownloader employs a **Local-First Client-Server Architecture** operating entirely inside the user's local operating system boundary.

### High-Level Architectural Diagram

```mermaid
graph TD
    subgraph Desktop Shell ["🖥️ Windows Desktop Shell"]
        Launcher["launcher.py<br/>(Self-Healing Host)"]
        UI["WebView2 / Browser App Window<br/>(Vanilla HTML5 / CSS3 / ES6)"]
    end

    subgraph Backend Engine ["⚡ Localhost Backend (127.0.0.1:8000+)"]
        API["FastAPI / Uvicorn Server<br/>(Endpoints, CORS, Traversal Checks)"]
        TaskManager["TaskManager<br/>(Thread-Safe Queue & State Machine)"]
        SSEHub["SSE Event Stream<br/>(Real-Time Progress Pub/Sub)"]
    end

    subgraph Media Worker Pipeline ["⚙️ Media Execution Pipeline"]
        WorkerPool["ThreadPoolExecutor<br/>(Non-blocking I/O Workers)"]
        YTDLP["yt-dlp Extraction Core<br/>(Platform Detect, Sig Decipher, Probing)"]
        FFMPEG["FFmpeg Binary<br/>(Muxer, Transcoder, Tag Writer)"]
    end

    subgraph Storage & OS ["💾 Windows Operating System"]
        Settings["%LOCALAPPDATA%/OmniDownloader<br/>(settings.json, cookies.txt, logs)"]
        Downloads["Target Destination Folder<br/>(e.g., Desktop/dds or Downloads)"]
        Explorer["Windows Explorer<br/>(File Highlight & Reveal)"]
    end

    Launcher -->|Spawns in Daemon Thread| API
    Launcher -->|Launches Native Window| UI
    UI -->|REST: /api/info, /api/download| API
    UI -->|SSE: /api/progress/{task_id}| SSEHub
    API -->|Queues Tasks| TaskManager
    TaskManager -->|Dispatches Job| WorkerPool
    WorkerPool -->|Executes Download| YTDLP
    YTDLP -->|Streams Hooks| TaskManager
    TaskManager -->|Pushes Real-time State| SSEHub
    YTDLP -->|Remuxes / Merges| FFMPEG
    FFMPEG -->|Writes Media File| Downloads
    API -->|Persists Directory & Config| Settings
    API -->|Triggers Reveal| Explorer
```

### Request & Execution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Frontend Client (WebView2)
    participant API as FastAPI Backend (main.py)
    participant TM as TaskManager (task_manager.py)
    participant YTDLP as yt-dlp Core (downloader.py)
    participant FF as FFmpeg Engine
    participant FS as Local Filesystem

    User->>UI: Enters Video / Playlist URL
    UI->>API: POST /api/info { url }
    API->>YTDLP: extract_media_info(url)
    Note over YTDLP: Probes format table, authentic title,<br/>thumbnails & playlist items
    YTDLP-->>API: MediaInfoResponse
    API-->>UI: 200 OK (Render Inspection Bay & Quality Chips)
    
    User->>UI: Selects Quality (e.g., 1080p) & clicks "Download Now"
    UI->>API: POST /api/download { url, quality, download_dir }
    API->>TM: create_task(request)
    TM-->>API: task_id
    API-->>UI: 200 OK { task_id, status: "queued" }

    UI->>API: GET /api/progress/{task_id} (SSE EventSource)
    API->>TM: Subscribe to Task Event Queue
    
    TM->>YTDLP: Execute download in ThreadPool worker
    loop Progress Streaming
        YTDLP->>TM: progress_hook(bytes, speed, eta)
        TM->>API: SSE message (percent, speed_str, eta_str)
        API->>UI: Update progress bar, speed badge, & ETA counter
    end

    alt Merging or Audio Conversion
        YTDLP->>FF: Postprocessor (merge video+audio / convert to MP3)
        TM->>UI: SSE message { status: "merging", current_item: "Merging..." }
    end

    YTDLP->>FS: Write finalized file (e.g. "Video Title.mp4")
    TM->>UI: SSE message { status: "completed", output_files: [...] }
    UI->>User: Display Download Complete & "Show in Folder" Button

    User->>UI: Clicks "Show in Folder"
    UI->>API: POST /api/open-folder { task_id }
    API->>FS: Path traversal validation
    API->>FS: Launch explorer.exe /select,"C:\path\to\file.mp4"
```

### 3.3 Repository File & Directory Structure

```
OmniDownloader/
├── .github/
│   └── workflows/
│       └── release.yml                    # Automated GitHub Actions CI/CD (lint, test, build matrix)
├── backend/
│   ├── app/
│   │   ├── __init__.py                    # Python package initializer
│   │   ├── config.py                      # App configuration, frozen paths (_MEIPASS), sanitization, WinError 448 mitigation
│   │   ├── downloader.py                  # yt-dlp core, platform detection, format matrix, opt-in browser probing, FFmpeg muxer
│   │   ├── main.py                        # FastAPI REST API, Host/Origin security, token auth, native dialog, Explorer reveal
│   │   ├── models.py                      # Pydantic v2 data validation schemas (requests, responses, task & settings models)
│   │   └── task_manager.py                # Thread-safe task state machine, ThreadPoolExecutor, SSE pub/sub queue, cancellation
│   ├── tests/
│   │   ├── conftest.py                    # Pytest test fixtures and loopback environment setup
│   │   ├── test_downloader.py             # Unit tests for platform detection, format parsing, and extraction logic
│   │   ├── test_hardening.py              # Security tests: session token, Host rebinding, path traversal, DOS devices
│   │   └── test_quality.py                # Tests for resolution tiering, audio extraction, and bitrate calculation
│   └── requirements.txt                   # Backend Python dependencies (FastAPI, Uvicorn, yt-dlp, Pydantic, etc.)
├── frontend/
│   ├── css/
│   │   └── styles.css                     # Cyber-Obsidian UI design system, CSS variables, glassmorphism, animations
│   ├── fonts/                             # Locally bundled offline typography (Outfit & JetBrains Mono)
│   ├── js/
│   │   ├── api.js                         # Fetch API client, REST endpoints wrapper, auth token synchronization, settings
│   │   ├── app.js                         # Primary frontend controller, DOM manipulation, format selector, settings modal
│   │   └── progress.js                    # Server-Sent Events (SSE) listener, live progress smoothing, ETA/speed formatting
│   └── index.html                         # Semantic HTML5 desktop single-page application shell
├── scripts/
│   ├── build.ps1                          # Unified build script for standalone executable and Inno Setup installer
│   ├── release.ps1                        # Unified release script (stages, commits, tags, and pushes to GitHub)
│   └── start.ps1                          # 1-Click developer bootstrap script (creates venv, installs deps, runs launcher)
├── tools/
│   ├── create_icon.py                     # Asset generator for multi-resolution Windows app.ico
│   └── download_fonts.py                  # Offline font asset downloader
├── examples/
│   └── cookies.txt.example                # Example Netscape format cookies template for manual authentication
├── assets/
│   └── app.ico                            # Committed multi-resolution application icon
├── .gitignore                             # Git ignore rules for virtualenvs, caches, media files, and build artifacts
├── DOCUMENTATION.md                       # Comprehensive architecture manual, API specifications, and threat model
├── installer.iss                          # Inno Setup 6 compiler script for non-admin per-user Windows Setup wizard
├── launcher.py                            # Standalone desktop bootstrap launcher (port 0 discovery, Edge WebView2, token injection)
├── LICENSE                                # MIT open-source license
├── omnidownloader.spec                    # PyInstaller bundle specification (hidden imports, upx=False, windowed mode)
└── README.md                              # Public GitHub repository landing page, features, and quick start guide
```

---

## 4. Backend Engineering & Module Breakdown

### 4.1 `launcher.py` — Self-Healing Host Launcher
`launcher.py` is the bootstrap entry point for both frozen standalone binaries (`OmniDownloader.exe`) and source installations.
- **Port Discovery (`get_free_port`)**: Binds dynamically to port `0` and lets the Windows operating system assign an available ephemeral port, eliminating port scan collisions.
- **Session Authentication Token**: Generates a random cryptographic URL-safe session token (`secrets.token_urlsafe(32)`), exports it to `os.environ["OMNI_TOKEN"]`, and injects it into the frontend single-page application.
- **Mount Point Hardening (`_safe_realpath` & `sanitize_system_path`)**: Protects against Windows `WinError 448: ERROR_UNTRUSTED_MOUNT_POINT` caused by broken symlinks or Node Version Manager (`.nodejs`) junctions in system `PATH`.
- **Subprocess Safety**: All process launches enforce `shell=False` and list-based arguments.
- **Tri-Level Window Orchestration**:
  1. *Level 1 (PyWebView)*: Attempts native Edge WebView2 creation.
  2. *Level 2 (Native Edge App Shell)*: If PyWebView is absent, locates `msedge.exe` or `chrome.exe` and launches with `--app=http://127.0.0.1:{port}` and an isolated profile, giving a windowed application without browser tabs or address bar.
  3. *Level 3 (Default Browser Fallback)*: Opens system browser and keeps background daemon alive.
- **Native Diagnostic Fallback (`show_native_message`)**: Invokes `MessageBoxW` via Win32 `ctypes` on fatal bootstrap errors so the user is never left with silent failures.

### 4.2 `backend/app/main.py` — REST API & Security Gateway
- **Session Token Enforcement**: Validates `X-Omni-Token` (or legacy `X-Auth-Token`) on all `/api/*` endpoints with `secrets.compare_digest`. Rejects missing or invalid tokens with `403 Forbidden`.
- **Host Header Validation Middleware**: Mitigates DNS rebinding by inspecting the HTTP `Host` header and rejecting any request not directed to `127.0.0.1:{port}` or `localhost:{port}` with `403 Forbidden`.
- **CORS Middleware**: Restricts allowed origins strictly to local loopback hosts (`127.0.0.1`, `localhost`).
- **Path Traversal Shield**: All endpoints accepting or returning paths (`/api/file`, `/api/open-folder`, `/api/choose-folder`) resolve paths strictly with `Path.resolve()` and verify containment against whitelisted directories via `is_relative_to()`.
- **Windows Explorer Launcher (`/api/open-folder`)**: Formats command strings directly (`explorer.exe /select,"<filepath>"`) with `shell=False` rather than passing Python argument lists, preventing Python's `list2cmdline` from incorrectly quoting switches and defaulting to `Documents`.
- **Folder Picker Service (`/api/choose-folder`)**: Replaces Tkinter and PowerShell STA with PyWebView's native folder dialog (`window.create_file_dialog(webview.FOLDER_DIALOG)`), providing smooth native Windows folder browsing.


### 4.3 `backend/app/task_manager.py` — State Machine & Concurrency Hub
- **Thread Safety**: Protects shared task maps using internal synchronization and thread-safe queue dispatches (`loop.call_soon_threadsafe`).
- **Cooperative Cancellation**: Tracks cancelled task IDs in a thread-safe set. `progress_hook` and `postprocessor_hook` check cancellation flags before every I/O chunk, raising `DownloadCancelled` to terminate `yt-dlp` immediately and clean up partial files.
- **Cookie Jar Isolation**: When a task executes, any persistent `cookies.txt` is cloned to a temporary per-task file (`cookie_task_{task_id}.txt`). This prevents concurrent downloads from corrupting the master cookie file during session writebacks.
- **Subscriber Event Queues**: Each SSE client connection obtains an isolated `asyncio.Queue`. The worker thread updates task progress up to 5 times per second, discarding duplicate states to prevent queue saturation.

### 4.4 `backend/app/downloader.py` — Universal Extraction Engine
- **Platform Detection**: RegEx parser identifying YouTube (Videos, Shorts, Playlists), Instagram, TikTok, X (Twitter), Bilibili, and generic sites.
- **Adaptive Quality Tiering**:
  - Analyzes video format lists and groups available streams into clean resolution tiers: `2160p (4K)`, `1440p (2K)`, `1080p (FHD)`, `720p (HD)`, `480p (SD)`, `360p`, and `audio_mp3`.
  - Calculates approximate file sizes based on bitrate (`tbr`, `vbr`, `abr`) and media duration.
- **Stream Merging & Codec Handling**:
  - Automatically merges optimal video stream (`bestvideo`) with optimal audio stream (`bestaudio`) using FFmpeg.
  - Sets output container to `.mp4` for maximum device compatibility.
  - When `audio_mp3` is selected, extracts audio, transcodes to 320kbps MP3 via `FFmpegExtractAudio`, and embeds thumbnail cover art using `FFmpegThumbnailsConvertor`.
- **Automated Anti-Bot Probing**:
  - If YouTube issues a bot verification challenge (`Sign in to confirm you're not a bot`), automatically probes local browser cookies (`edge`, `chrome`, `firefox`, `brave`) in read-only mode to pass the challenge without manual user configuration.

### 4.5 `backend/app/models.py` — Strict Pydantic Data Contracts
Defines validated input/output models:
- `InfoRequest`: URL string with validation and browser session selector.
- `MediaInfoResponse`: Structured metadata including platform, title, duration, author, format list, and playlist items.
- `DownloadRequest`: Target URL, quality selector, playlist item IDs, and optional custom download directory.
- `DownloadTaskStatus`: Real-time state representation containing progress percentage, speed, ETA, status enum, output file paths, and active download directory.

### 4.6 `backend/app/config.py` — System Environment & Path Sanitization
- Resolves directories dynamically whether running in development or inside a PyInstaller frozen bundle (`sys._MEIPASS`).
- Standardizes user data storage in `%LOCALAPPDATA%\OmniDownloader`.
- **`sanitize_filename()`**: Enforces Windows filesystem compliance by replacing illegal characters (`< > : " / \ | ? *`) with underscores, trimming trailing dots/spaces, escaping DOS reserved names (`CON`, `PRN`, `AUX`, `NUL`, etc.), and enforcing a 150-character limit to avoid path length overflow (`MAX_PATH`).

---

## 5. Frontend Architecture & Cyber-Obsidian UI/UX Design System

The frontend is implemented with zero framework dependencies, running natively in modern Chromium-based WebView2 engines.

### 5.1 Design System Tokens & Aesthetics
```css
:root {
  /* Surface & Background Hierarchy */
  --bg-core: #08090d;           /* Deep obsidian foundation */
  --bg-shell: #0e121a;          /* Card & container elevation */
  --bg-surface: #141923;        /* Input & interactive element fill */
  --bg-surface-hover: #1c2331;  /* High-contrast hover state */

  /* Cyber Glow Accents */
  --accent-primary: #00f0b5;    /* Vibrant neon mint */
  --accent-glow: rgba(0, 240, 181, 0.25);
  --accent-secondary: #00d2ff;  /* Electric cyan */

  /* Status Colors */
  --status-success: #00f0b5;
  --status-error: #ff3366;
  --status-warning: #ffb800;

  /* Typography */
  --font-display: 'Outfit', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

### 5.2 Key UI Components
1. **Omni-Search Hero Bar**:
   - High-contrast URL input field with auto-paste detection, clear button, and keyboard shortcut handler (<kbd>Enter</kbd> to submit).
   - Dynamic validation badge indicating recognized platform (YouTube, TikTok, Instagram, etc.).
2. **Media Inspection Bay**:
   - Renders media thumbnail, authentic creator/author, duration badge, and video title with smooth fade-in animations.
   - For playlists: Displays total item count, cumulative playlist runtime, and an expandable item checklist.
3. **Adaptive Quality Selector**:
   - Radio pill buttons dynamically populated based on stream availability (`Best`, `1080p`, `720p`, `480p`, `MP3`).
   - Displays estimated file size badges calculated from stream bitrates.
4. **Active Download Drawer & Progress Dashboard**:
   - Multi-stage state machine: `queued` → `downloading` → `merging` → `completed` (or `cancelled` / `error`).
   - Smooth animated progress bar with glowing cyan head.
   - Real-time download speed (`MB/s`), total size downloaded, and dynamic ETA counter.
   - Action bay offering direct "Show in Folder" exploration and "Download Another" reset.
5. **Settings & Environment Modal**:
   - Allows changing the destination download folder with a single-dialog native folder picker.
   - Displays FFmpeg installation status and 1-click winget installer.

---

## 6. Security Architecture & Threat Hardening

OmniDownloader adheres to strict security standards to ensure safe desktop execution:

```
+-------------------------------------------------------------------------+
|                         THREAT MITIGATION MATRIX                        |
+-----------------------------------+-------------------------------------+
| Threat Vector                     | Mitigation Implemented              |
+-----------------------------------+-------------------------------------+
| Path Traversal (Directory Escape) | Strict Path.resolve() verification  |
|                                   | Whitelist checking via is_relative  |
+-----------------------------------+-------------------------------------+
| Command Injection                 | Subprocess arguments passed as safe |
|                                   | lists; shell=False everywhere       |
+-----------------------------------+-------------------------------------+
| Windows Explorer Quoting Bugs     | Formatted string with explicit      |
|                                   | quotes: explorer.exe /select,"path" |
+-----------------------------------+-------------------------------------+
| DOS Reserved Device Name Denial   | sanitize_filename() prepends '_' to |
|                                   | names like CON, PRN, AUX, NUL       |
+-----------------------------------+-------------------------------------+
| Untrusted Mount Points (WinErr448)| Safe realpath wrapper intercepts    |
|                                   | OSError and purges broken junctions |
+-----------------------------------+-------------------------------------+
| Cross-Site Request Forgery (CSRF) | CORS middleware restricts origins   |
|                                   | to localhost loopback only          |
+-----------------------------------+-------------------------------------+
| Cookie Jar Corruption             | Per-task isolated temporary cookie  |
|                                   | copies during downloads             |
+-----------------------------------+-------------------------------------+
```

---

## 7. REST API & Real-Time SSE Protocol Specification

All API communication is served over `http://127.0.0.1:{PORT}` with JSON payloads and Server-Sent Events.

### 7.1 Media Extraction: `POST /api/info`
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "cookie_browser": "none"
  }
  ```
- **Response Model (`MediaInfoResponse`)**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "duration": 213,
    "duration_formatted": "03:33",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "uploader": "Rick Astley",
    "platform": "youtube",
    "is_playlist": false,
    "available_qualities": ["best", "1080p", "720p", "480p", "360p", "audio_mp3"],
    "quality_sizes_formatted": {
      "best": "~45.2 MB",
      "1080p": "~38.1 MB",
      "audio_mp3": "~5.1 MB"
    },
    "playlist_items": []
  }
  ```

### 7.2 Start Download: `POST /api/download`
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "1080p",
    "is_playlist": false,
    "selected_video_ids": null,
    "download_dir": "C:\\Users\\User\\Desktop\\dds"
  }
  ```
- **Response**:
  ```json
  {
    "task_id": "a1b2c3d4",
    "status": "queued",
    "message": "Download task queued successfully."
  }
  ```

### 7.3 Real-Time Progress Stream: `GET /api/progress/{task_id}`
- **Protocol**: `text/event-stream` (Server-Sent Events)
- **Sample Event Stream**:
  ```
  event: message
  data: {"task_id":"a1b2c3d4","status":"downloading","progress":42.5,"speed_str":"8.5 MB/s","eta_str":"00:12","current_item":"Downloading video streams...","completed_items":0,"total_items":1,"output_files":[],"download_dir":"C:\\Users\\User\\Desktop\\dds"}

  event: message
  data: {"task_id":"a1b2c3d4","status":"merging","progress":99.0,"speed_str":"Processing","eta_str":"00:01","current_item":"Merging audio and video streams (ffmpeg)...","completed_items":0,"total_items":1,"output_files":[],"download_dir":"C:\\Users\\User\\Desktop\\dds"}

  event: message
  data: {"task_id":"a1b2c3d4","status":"completed","progress":100.0,"speed_str":"Complete","eta_str":"00:00","current_item":"Download completed successfully!","completed_items":1,"total_items":1,"output_files":["C:\\Users\\User\\Desktop\\dds\\Rick Astley - Never Gonna Give You Up.mp4"],"download_dir":"C:\\Users\\User\\Desktop\\dds"}
  ```

### 7.4 Cancel Download: `POST /api/cancel/{task_id}`
- Cancels active worker threads, halts ffmpeg processes, removes temporary `.part` files, and emits status `"cancelled"`.

### 7.5 Native Folder Dialog: `POST /api/choose-folder`
- Spawns a single native Windows folder picker modal. Returns:
  ```json
  {
    "status": "success",
    "download_dir": "C:\\Users\\User\\Desktop\\dds",
    "path": "C:\\Users\\User\\Desktop\\dds"
  }
  ```
- If closed or cancelled, returns immediately:
  ```json
  {
    "status": "cancelled",
    "download_dir": "C:\\Users\\User\\Downloads",
    "path": "C:\\Users\\User\\Downloads"
  }
  ```

### 7.6 Windows Explorer Reveal: `POST /api/open-folder`
- **Query Parameter**: `task_id` (optional)
- Uses `explorer.exe /select,"<filepath>"` to open Windows Explorer with the specific downloaded file highlighted and selected.

---

## 8. Media Extraction, Remuxing & Resilient Extraction Engine

```mermaid
graph TD
    A["Target URL Submitted"] --> B["Platform Identification<br/>(RegEx URL Domain Parser)"]
    B --> C["YouTube"]
    B --> D["Instagram"]
    B --> E["TikTok / X / Others"]
    C --> F{"Bot Challenge Detected?"}
    F -- "Yes & Probing Opted In" --> G["Query Local Browser Session<br/>(Read-Only Edge/Chrome)"]
    F -- "No / Standard" --> H["Extract Stream Format Matrix"]
    G --> H
    D --> H
    E --> H
    H --> I["Download Video & Audio Streams"]
    I --> J["FFmpeg Stream-Copy Remuxing (MP4)<br/>or Lossy Transcoding (MP3 320kbps)"]
    J --> K["Sanitized Media Written to Disk"]
```

### Format Selection Matrix
- **`best`**: Downloads the absolute highest resolution available (up to 4K/8K 60fps) and merges with highest bitrate audio via lossless stream-copy remuxing (no re-encoding).
- **`1080p`**: `bestvideo[height<=1080]+bestaudio/best[height<=1080]` (lossless video stream-copy).
- **`720p`**: `bestvideo[height<=720]+bestaudio/best[height<=720]` (lossless video stream-copy).
- **`480p`**: `bestvideo[height<=480]+bestaudio/best[height<=480]` (lossless video stream-copy).
- **`audio_mp3`**: Extracts best audio stream, transcodes to constant 320kbps MP3 via FFmpeg (lossy transcoding), writes ID3 tags, and embeds full-resolution thumbnail art.

---

## 9. Build, Packaging & Distribution Pipeline

OmniDownloader employs a fully automated dual-binary release pipeline generating both an enterprise-grade installer and a portable executable.

### 9.1 PyInstaller Spec Configuration (`omnidownloader.spec`)
- **Bundle Composition**: Packages Python 3.11 runtime, `uvicorn`, `fastapi`, `starlette`, `sse_starlette`, `yt-dlp`, `platformdirs`, `imageio-ffmpeg` binaries, `frontend/` assets, and `backend/app/` logic.
- **`console=False`**: Compiles in windowed mode. Suppresses command prompt terminal windows from appearing.
- **`upx=False`**: UPX compression is deliberately disabled to eliminate antivirus heuristic false positives (Windows Defender, etc.). Tradeoff: Standalone binary is slightly larger (~15-20%), but execution reliability and consumer trust are maximized.

### 9.2 Inno Setup Configuration (`installer.iss`)
- **Per-User Non-Admin Install (`PrivilegesRequired=lowest`)**:
  - Installs cleanly into `%LOCALAPPDATA%\Programs\OmniDownloader`.
  - Zero Windows UAC / Administrator permission prompts required.
- **Bundled FFmpeg**:
  - FFmpeg is bundled directly inside `OmniDownloader.exe` via `imageio-ffmpeg` data files, so the installer delivers full 1080p/4K merging and MP3 conversion capabilities with zero external dependencies.
- **Windows Integration**:
  - Places shortcut in `{autoprograms}` (Start Menu), indexed immediately by **Windows Search** (<kbd>Win</kbd> + type `"Omni"`).
  - Optional Desktop shortcut.
  - Registers full uninstaller in **Windows Settings > Installed apps**.

### 9.3 Automated GitHub Actions CI/CD (`.github/workflows/release.yml`)
- Triggered automatically on git tags matching `v*` (e.g. `v1.2.3`).
- Provisions a `windows-latest` virtual environment.
- Enforces quality gates: `ruff` linting and `pytest backend/tests/` unit/security tests must pass before compiling.
- Bundles offline fonts via `tools/download_fonts.py`.
- Compiles `OmniDownloader.exe` via PyInstaller and `OmniDownloader-Setup.exe` via Inno Setup 6.
- Publishes automated release with release notes and downloadable binary assets.

---

## 10. Operational Runbook, Edge Cases & Troubleshooting

### 10.1 Dynamic Port Discovery (Zero Collisions)
- **Mechanism**: `launcher.py` binds to port `0` (`get_free_port()`), allowing the Windows OS kernel to assign a guaranteed free ephemeral port. Eliminates static port scanning and collision crashes.

### 10.2 Windows SmartScreen Warning on Newly Compiled Releases
- **Symptom**: Windows displays *"Windows protected your PC"* when opening a newly downloaded `.exe`.
- **Cause**: Standard behavior for open-source binaries that have not yet accrued global hash reputation or an expensive commercial EV Code Signing certificate.
- **Resolution**: Click **"More info"** → **"Run anyway"**.

### 10.3 YouTube Bot Verification Challenges
- **Symptom**: YouTube throttles anonymous scraping IP addresses.
- **Behavior**: Users can opt in to local browser session probing in **Settings**, or import a standard Netscape `cookies.txt` file. When enabled, OmniDownloader queries local browser profiles (Edge, Chrome, Firefox, Brave) in read-only mode to pass the verification challenge.

### 10.4 Government or Regional Platform Bans (e.g. TikTok)
- **Symptom**: `Connection to www.tiktok.com timed out` in regions where the platform is ISP-blocked.
- **Resolution**: Connect to a VPN (e.g., Cloudflare 1.1.1.1 WARP, ProtonVPN) before fetching details.

### 10.5 High-Resolution Merging (FFmpeg)
- **Status**: FFmpeg is bundled out-of-the-box via `imageio-ffmpeg` within both the portable executable and setup installer. High-resolution stream merging (1080p, 4K) and MP3 conversion are functional immediately without manual installations or PATH modifications.

---

*Authored for the OmniDownloader Project.*  
*Maintained by Aniket Kumar & open-source contributors.*

