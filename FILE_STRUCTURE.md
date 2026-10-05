# 📁 OmniDownloader — Project File & Directory Structure

```
OmniDownloader/
├── .github/
│   └── workflows/
│       └── release.yml                    # Automated GitHub Actions CI/CD (PyInstaller + Inno Setup build matrix)
├── backend/
│   ├── app/
│   │   ├── __init__.py                    # Python package initializer
│   │   ├── config.py                      # App configuration, frozen paths (_MEIPASS), sanitization, WinError 448 mitigation
│   │   ├── downloader.py                  # yt-dlp core, platform detection, format matrix, auto browser probing, FFmpeg muxer
│   │   ├── main.py                        # FastAPI REST API, CORS security, SSE endpoints, folder picker, Explorer reveal
│   │   ├── models.py                      # Pydantic v2 data validation schemas (requests, responses, task models)
│   │   └── task_manager.py                # Thread-safe task state machine, ThreadPoolExecutor, SSE pub/sub queue, cancellation
│   ├── tests/
│   │   ├── conftest.py                    # Pytest test fixtures and loopback environment setup
│   │   ├── test_downloader.py             # Unit tests for platform detection, format parsing, and extraction logic
│   │   ├── test_hardening.py              # Security tests: path traversal, command injection, Win32 quoting, sanitization
│   │   └── test_quality.py                # Tests for resolution tiering, audio extraction, and bitrate calculation
│   └── requirements.txt                   # Backend Python dependencies (FastAPI, Uvicorn, yt-dlp, Pydantic, etc.)
├── frontend/
│   ├── css/
│   │   └── styles.css                     # Cyber-Obsidian UI design system, CSS variables, glassmorphism, animations
│   ├── js/
│   │   ├── api.js                         # Fetch API client, REST endpoints wrapper, error handling
│   │   ├── app.js                         # Primary frontend controller, DOM manipulation, format selector, event dispatching
│   │   └── progress.js                    # Server-Sent Events (SSE) listener, live progress smoothing, ETA/speed formatting
│   └── index.html                         # Semantic HTML5 desktop single-page application shell
├── .gitignore                             # Git ignore rules for virtualenvs, caches, media files, and build artifacts
├── build_exe.bat                          # Local batch script to compile standalone portable OmniDownloader.exe
├── build_installer.bat                    # Local batch script to compile OmniDownloader-Setup.exe using Inno Setup
├── cookies.txt.example                    # Example Netscape format cookies template for manual authentication
├── create_desktop_shortcut.vbs            # VBScript helper to create desktop shortcut pointing to launcher
├── create_icon.py                         # Generates multi-resolution Windows app.ico from vector graphics
├── DOCUMENTATION.md                       # Comprehensive architecture manual, API specifications, and threat model
├── FILE_STRUCTURE.md                      # Complete annotated repository tree and component index (this file)
├── installer.iss                          # Inno Setup 6 compiler script for non-admin per-user Windows Setup wizard
├── launcher.py                            # Standalone desktop bootstrap launcher (port discovery, Edge WebView2, logging)
├── LICENSE                                # MIT open-source license
├── omnidownloader.spec                    # PyInstaller bundle specification (hidden imports, datas, windowed mode)
├── OmniDownloader.bat                     # Windows double-click quick launcher
├── OmniDownloader.vbs                     # Silent VBScript wrapper to launch without background console windows
├── publish_release.bat                    # Windows batch script to stage, commit, tag, and push release to GitHub
├── publish_release.ps1                    # PowerShell script to stage, commit, tag, and push release to GitHub
├── push_to_github.bat                     # Batch script helper to push latest branch commits
├── push.bat                               # Quick alias batch script to push release
├── push.ps1                               # Quick alias PowerShell script to run publish_release.ps1
├── README.md                              # Public GitHub repository landing page, features, and quick start guide
├── start.bat                              # 1-Click developer bootstrap script (creates venv, installs deps, runs launcher)
└── start.ps1                              # 1-Click PowerShell developer bootstrap script
```

---

## Detailed Directory Breakdown

### 1. Root Application Shell & Launchers
- **`launcher.py`**: The primary Python desktop entry point. Discovers an open port starting at `8000`, starts Uvicorn in a daemon thread, monitors backend health, and launches a native standalone desktop window via **PyWebView** or **Microsoft Edge WebView2 App Mode** (`--app=http://127.0.0.1:{port}`).
- **`OmniDownloader.bat` / `OmniDownloader.vbs`**: User-facing launch shortcuts for Windows that invoke `launcher.py` silently without showing a terminal window.
- **`start.bat` / `start.ps1`**: 1-Click automated developer scripts that check Python version, create `venv/`, install `backend/requirements.txt`, and start the desktop app.

### 2. Backend Service (`backend/app/`)
- **`backend/app/main.py`**: FastAPI REST API and routing gateway. Manages static asset serving (`/` -> `frontend/`), CORS policies, directory containment checks, native folder selection (`/api/choose-folder`), and Windows Explorer highlighting (`/api/open-folder`).
- **`backend/app/downloader.py`**: The media processing engine. Wraps `yt-dlp` with platform identification, format tier matching (4K, 1080p, 720p, 480p, MP3), background browser cookie auto-probing, and FFmpeg multiplexing.
- **`backend/app/task_manager.py`**: Concurrency controller. Manages task states (`queued`, `downloading`, `merging`, `completed`, `cancelled`), runs background downloads in a `ThreadPoolExecutor`, publishes real-time telemetry to per-task SSE queues, and manages isolated cookie files.
- **`backend/app/config.py`**: Central environment configuration. Determines execution mode (frozen PyInstaller `_MEIPASS` vs. development), defines storage paths in `%LOCALAPPDATA%\OmniDownloader`, mitigates Windows `WinError 448` mount-point issues, and provides `sanitize_filename()`.
- **`backend/app/models.py`**: Pydantic v2 schemas validating request inputs (`InfoRequest`, `DownloadRequest`) and serializing response models (`MediaInfoResponse`, `DownloadTaskStatus`).

### 3. Frontend Client (`frontend/`)
- **`frontend/index.html`**: Accessible, semantic HTML5 single-page application structure. Contains the Omni-Search hero bar, Inspection Bay, adaptive format pills, playlist checklist, download drawer, and settings modal.
- **`frontend/css/styles.css`**: Complete vanilla CSS3 design system built on custom CSS variables (`--bg-core`, `--accent-primary`, `--accent-glow`). Implements modern cyber-obsidian aesthetics, glassmorphism, responsive grid layouts, and micro-interactions.
- **`frontend/js/app.js`**: Core UI logic controller. Coordinates user input, invokes API endpoints, displays toast alerts, toggles playlist items, and drives state transitions.
- **`frontend/js/api.js`**: Lightweight asynchronous REST client wrapping `fetch()` with timeout and error parsing.
- **`frontend/js/progress.js`**: Server-Sent Events (SSE) client. Connects to `/api/progress/{task_id}`, handles reconnection backoff, and smoothly animates the download progress bar, speed tracker, and ETA counter.

### 4. Build, Packaging & Distribution
- **`omnidownloader.spec`**: PyInstaller configuration defining runtime hooks, binary datas (`frontend/` and `backend/app/`), UPX compression, hidden imports for FastAPI/Uvicorn, and `console=False` windowed mode.
- **`installer.iss`**: Inno Setup 6 Windows Installer compiler script. Creates a modern, per-user setup wizard (`OmniDownloader-Setup.exe`) that installs to `%LOCALAPPDATA%\Programs\OmniDownloader`, registers Start Menu & Windows Search shortcuts, adds Desktop icons, and configures clean uninstallation.
- **`build_exe.bat` / `build_installer.bat`**: Local Windows batch scripts for building the portable executable and setup installer locally.
- **`.github/workflows/release.yml`**: Automated GitHub Actions workflow triggered on git tags (`v*`). Builds both `OmniDownloader-Setup.exe` and `OmniDownloader.exe` on `windows-latest` runners and uploads them directly to GitHub Releases.

### 5. Automated Testing (`backend/tests/`)
- **`test_hardening.py`**: Comprehensive security tests validating path traversal immunity, filename sanitization, DOS device name safety (`CON`, `PRN`, `NUL`), Win32 quoting bug prevention, and error masking.
- **`test_downloader.py`**: Functional tests verifying extractor options, base yt-dlp configurations, and cancellation handling.
- **`test_quality.py`**: Tests for resolution tier resolution, adaptive bitrate calculation, and audio-only MP3 conversion routines.
