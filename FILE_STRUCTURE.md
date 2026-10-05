# 📂 OmniDownloader — File Structure & Architecture Map

> **Current Version:** v1.3.0  
> **Target OS:** Windows 10 / 11 (x64)  
> **Status:** Production Ready  

---

```
d:\AG\yt\
├── .github/
│   └── workflows/
│       └── release.yml                        # Automated CI/CD release workflow (Ruff, Pytest, Inno Setup, PyInstaller)
├── assets/
│   ├── app.ico                                # Official multi-resolution Windows executable icon (16x16 to 256x256)
│   └── app.png                                # High-res application logo (256x256)
├── backend/
│   ├── app/
│   │   ├── __init__.py                        # Python package marker
│   │   ├── config.py                          # Paths, Windows mount point/symlink hardening, and persistent settings
│   │   ├── downloader.py                      # yt-dlp wrapper, format sorting, size estimation, and FFmpeg detection
│   │   ├── main.py                            # FastAPI application, security token & host header middleware, and API endpoints
│   │   ├── models.py                          # Pydantic schemas (media info, requests, settings, errors, status)
│   │   └── task_manager.py                    # Thread-pool download worker queue and real-time SSE progress telemetry
│   ├── tests/
│   │   ├── conftest.py                        # Shared test fixtures (auth_headers, auth_client, client) and sys.path setup
│   │   ├── test_downloader.py                 # Unit tests for filename sanitization, duration formatting, and model schemas
│   │   ├── test_hardening.py                  # Security test suite (tokens, Host/Origin rebinding, traversal, cancellation)
│   │   └── test_quality.py                    # Stream selection, format sorting, FFmpeg discovery, and size tests
│   └── requirements.txt                       # Core Python runtime and backend dependencies
├── examples/
│   └── cookies.txt.example                    # Netscape format cookies template for authenticated media extraction
├── frontend/
│   ├── css/
│   │   └── styles.css                         # Cyber-Obsidian design system stylesheet (variables, glassmorphism, animations)
│   ├── fonts/                                 # 100% offline bundled Google fonts (Outfit, JetBrains Mono)
│   │   ├── JetBrainsMono-Medium.ttf
│   │   ├── JetBrainsMono-Regular.ttf
│   │   ├── JetBrainsMono-SemiBold.ttf
│   │   ├── Outfit-Bold.ttf
│   │   ├── Outfit-ExtraBold.ttf
│   │   ├── Outfit-Medium.ttf
│   │   ├── Outfit-Regular.ttf
│   │   └── Outfit-SemiBold.ttf
│   ├── js/
│   │   └── app.js                             # Client application controller, SSE progress listener, and settings modal
│   └── index.html                             # Cyber-Obsidian responsive desktop UI layout and control dashboard
├── scripts/
│   ├── build.ps1                              # Unified local compilation script (PyInstaller EXE and Inno Setup installer)
│   ├── release.ps1                            # Unified release publisher (stages, commits, tags, and pushes to GitHub)
│   └── start.ps1                              # 1-Click developer quickstart and virtual environment bootstrap script
├── tools/
│   ├── create_icon.py                         # Standalone asset generator for app.ico and app.png
│   └── download_fonts.py                      # Offline font downloader for Outfit and JetBrains Mono
├── .gitignore                                 # Git exclusions (venv, binaries, downloads, temporary cookies, caches)
├── DOCUMENTATION.md                           # Comprehensive architecture manual, API specifications, and operational runbook
├── FILE_STRUCTURE.md                          # Annotated repository layout tree and component map (this file)
├── installer.iss                              # Inno Setup 6 compiler script for non-admin per-user Windows Setup wizard
├── launcher.py                                # Standalone desktop bootstrap launcher (port 0, Edge WebView2, logging)
├── LICENSE                                    # MIT open-source license
├── omnidownloader.spec                        # PyInstaller bundle specification (windowed mode, data bundling, upx=False)
├── pyproject.toml                             # Ruff linter rules and Pytest configuration
└── README.md                                  # Repository landing page, feature highlights, and user guide
```

---

## 📌 Component Directory Index

| Directory / File | Description |
| :--- | :--- |
| **`backend/app/`** | Core FastAPI microservice providing REST and real-time SSE streaming for media downloads. |
| **`backend/tests/`** | Complete Pytest suite covering security hardening, stream quality, and downloader logic. |
| **`frontend/`** | Vanilla JS and Cyber-Obsidian UI with zero external CDN dependencies (bundled fonts and CSS). |
| **`scripts/`** | Consolidated PowerShell automation scripts (`start.ps1`, `build.ps1`, `release.ps1`). |
| **`tools/`** | Asset creation and offline font bundling helpers (`create_icon.py`, `download_fonts.py`). |
| **`launcher.py`** | Desktop shell bootstrap: assigns ephemeral port, sets up `X-Omni-Token`, and opens native window. |
| **`installer.iss`** | Inno Setup 6 script generating `dist/OmniDownloader-Setup.exe` with Start Menu & Search integration. |
| **`omnidownloader.spec`** | PyInstaller bundle spec generating portable standalone `dist/OmniDownloader.exe`. |
