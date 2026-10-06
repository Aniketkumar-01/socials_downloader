# Specification: OmniDownloader In-App Update System

## 1. Objective
Enable OmniDownloader desktop users to easily discover, verify, download, and install application updates directly within the application without needing to manually search GitHub releases.

### User Flow
1. **Discovery / Onboarding**:
   - The user sees a modern "Check for Updates" button in the top navigation/utility bar next to the server status node.
   - On startup (after a non-blocking 3.5-second initial delay), the app silently checks for new releases. If a newer release exists, a subtle pulsing glowing badge appears on the update button.
2. **Checking**:
   - The user clicks "Check for Updates".
   - The button shows a sleek spinner / "Checking..." state.
3. **Up to Date**:
   - If the current installed version is greater than or equal to the latest GitHub release, a toast or notification appears:
     `"You're up to date! OmniDownloader v{version} is the latest version."`
4. **Update Available**:
   - An elegant modal appears showing:
     - New version badge (`v1.2.4` → `v1.2.5`)
     - Release title, publish date, and installer size (~48 MB)
     - Formatted release notes and highlights
     - Action buttons:
       - **"Download & Install"** (Primary action)
       - **"View on GitHub"** (Opens release in browser)
       - **"Later"** (Dismisses modal)
5. **Download & Installation**:
   - Clicking "Download & Install" transitions the modal to an active download state with an animated progress bar, downloaded size readout, and cancel button.
   - The backend downloads `OmniDownloader-Setup.exe` into `%LOCALAPPDATA%\OmniDownloader\updates\` with chunk verification.
   - Upon completion, the installer is executed with `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS` (with fallback to interactive mode if needed).
   - The current application gracefully initiates shutdown so Inno Setup cleanly updates the files and relaunches the upgraded OmniDownloader.

---

## 2. Architecture & Components

```
┌────────────────────────────────────────────────────────┐
│                   Frontend (SPA)                       │
│  - #btn-check-updates (Header Utility Bar)             │
│  - #app-update-modal (Cyber-Obsidian Dialog)           │
│  - api.js (check, download, status, apply, cancel)     │
│  - app.js (UI state machine, polling, notifications)   │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP REST
┌──────────────────────────▼─────────────────────────────┐
│                 Backend (FastAPI)                      │
│  - GET  /api/app/version                               │
│  - GET  /api/app/update/check                          │
│  - POST /api/app/update/download                       │
│  - GET  /api/app/update/download-progress              │
│  - POST /api/app/update/apply                          │
│  - POST /api/app/update/cancel                         │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│             Update Engine (updater.py)                 │
│  - GitHub Releases API parser (rate-limit cached)      │
│  - Semver comparison logic (v1.2.4 vs v1.2.5)          │
│  - Background downloader with byte-stream tracking     │
│  - Inno Setup runner with auto-shutdown hook           │
└────────────────────────────────────────────────────────┘
```

---

## 3. Data Contracts & API Schemas

### `GET /api/app/update/check`
Query parameters: `force: bool = False`

Response JSON:
```json
{
  "status": "success",
  "current_version": "1.2.4",
  "latest_version": "1.2.5",
  "update_available": true,
  "release_name": "OmniDownloader Release v1.2.5",
  "release_notes": "### Changes\n- Improved format extraction\n- Faster downloads",
  "release_url": "https://github.com/Aniketkumar-01/socials_downloader/releases/tag/v1.2.5",
  "download_url": "https://github.com/Aniketkumar-01/socials_downloader/releases/download/v1.2.5/OmniDownloader-Setup.exe",
  "file_size": 48234496,
  "published_at": "2026-10-06T12:00:00Z"
}
```

### `POST /api/app/update/download`
Starts the background download of the setup executable.
Response:
```json
{
  "status": "started",
  "message": "Update download initiated."
}
```

### `GET /api/app/update/download-progress`
Response:
```json
{
  "status": "downloading",
  "percent": 45.2,
  "downloaded_bytes": 21800000,
  "total_bytes": 48234496,
  "speed_str": "4.2 MB/s",
  "file_path": "C:\\Users\\...\\AppData\\Local\\OmniDownloader\\updates\\OmniDownloader-Setup-v1.2.5.exe",
  "error": null
}
```

### `POST /api/app/update/apply`
Payload: `{"silent": true}`
Response:
```json
{
  "status": "applying",
  "message": "Setup executable launched. Application restarting..."
}
```

---

## 4. Acceptance Criteria
1. Header contains a responsive, accessible "Check for Updates" button matching cyber-obsidian design.
2. Clicking button queries the backend and displays either a friendly "Up to date" toast or opens the update modal.
3. If an update is available, modal accurately parses and displays version, release notes, release date, and installer size.
4. Download progress tracks real-time progress smoothly in the modal.
5. On download completion, "Install & Restart" launches the setup executable and cleanly shuts down the application so Inno Setup can update files.
6. Error handling for network dropouts, rate limiting, and missing assets.
7. Background startup check gently highlights button without annoying popups.
