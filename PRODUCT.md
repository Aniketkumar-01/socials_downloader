# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Everyday users and consumers seeking to save online videos, Reels, Shorts, and songs for offline viewing, archiving personal favorites across multi-platform feeds without ad-ridden spam tools or subscription walls.

## Product Purpose
OmniDownloader is a local-first, friction-free universal downloader that extracts media from YouTube, Instagram, TikTok, X (Twitter), Bilibili, Facebook, and Reddit directly onto the user's PC with original titles, full quality, and live SSE progress tracking.

## Positioning
A zero-clutter, privacy-respecting desktop utility running locally on the user's machine (backed by FastAPI and yt-dlp) that bypasses web ad bloat, avoids cloud tracking, handles YouTube bot verification via local cookie injection, and integrates directly with the Windows filesystem.

## Operating Context
- Local Windows 10/11 environment running as a clean standalone desktop app (via PyWebView or Edge App Shell) or local browser tab at `localhost:8000`.
- Media workflow: paste URL -> auto-fetch metadata -> pick format/quality (or select playlist items) -> download with real-time speed & ETA -> reveal directly in Windows Explorer or browser download.
- Operating constraints: regional ISP restrictions/bans (requires VPN for restricted services like TikTok in certain jurisdictions) and YouTube bot checks requiring cookie management.

## Capabilities and Constraints
- Multi-platform media extraction (YouTube videos/Shorts/playlists, Instagram Reels/posts, TikTok, Twitter/X, Bilibili, Facebook, Reddit).
- Real-time download progress tracking via Server-Sent Events (SSE) and polling fallback (percentage, speed in MB/s, ETA).
- Safe filename sanitization preserving original title strings for Windows filesystem compatibility.
- Cookie authentication support (upload `cookies.txt` or select browser profile) to bypass bot verification challenges.
- Direct filesystem storage to local `downloads/` directory plus single-click "Show in Folder" Explorer hook and browser fallback.
- Technical constraint: FFmpeg dependency required for merging 1080p+ separated audio/video streams and MP3 conversions.
- Scope constraint: Preserved as a streamlined, single-window utility rather than an expansive media library manager or multi-URL background queue.

## Brand Commitments
- Name: OmniDownloader (Universal Video & Playlist Downloader).
- Voice & Tone: Clear, utilitarian, responsive, and trustworthy without hype or artificial complexity.
- Visual Foundation: Premium dark theme with glowing accents and modern typography (`Outfit`).

## Evidence on Hand
- Working FastAPI backend (`backend/app/main.py`, `downloader.py`, `task_manager.py`).
- Functional frontend UI (`frontend/index.html`, `frontend/css/styles.css`, `frontend/js/app.js`, `api.js`, `progress.js`).
- Windows desktop launchers (`desktop.py`, `OmniDownloader.vbs`, `start.bat`, `start.ps1`).
- Working test suite (`backend/tests/test_downloader.py`).
- Absences: No remote cloud servers, no user accounts/authentication required, and no telemetry/tracking.

## Product Principles
- **Friction-Free Utility**: Minimize distance between pasting a link and having the file on disk; avoid unnecessary steps, menus, or modals.
- **Local-First & Transparent**: Runs entirely on the user's machine, keeping user data and downloads private, with visible local progress.
- **Resilient & Communicative**: Handle platform blocks, format ambiguities, and bot challenges gracefully with actionable instructions (e.g. cookie upload, VPN warnings) rather than silent timeouts.
- **Fidelity Preservation**: Always strive for authentic media titles, original metadata, and the highest available stream quality without artificial downscaling.
