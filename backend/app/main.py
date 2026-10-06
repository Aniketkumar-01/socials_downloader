import os
import sys
import re
import time
import threading
import asyncio
import logging
import secrets
import shutil
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from app.config import (
    BASE_DIR,
    DOWNLOADS_DIR,
    FRONTEND_DIR,
    SERVER_HOST,
    SERVER_PORT,
    USER_DATA_DIR,
    COOKIES_FILE,
    ENGINE_DIR,
    MAX_COOKIE_SIZE,
    APP_VERSION,
    GITHUB_REPO,
    get_default_download_dir,
    set_download_dir
)
from app.models import (
    InfoRequest,
    MediaInfoResponse,
    DownloadRequest,
    DownloadTaskStatus,
    SetDownloadDirRequest,
    UpdateDownloadRequest,
    UpdateApplyRequest
)
from app.downloader import extract_media_info, MediaExtractionError, map_ytdlp_error
from app.task_manager import task_manager
from app.updater import updater

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Startup random token for local API protection
API_TOKEN = secrets.token_urlsafe(32)

# Windows process creation flag to prevent console/cmd windows from popping up
NO_WINDOW_FLAG = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0

# --------------------------------------------------------------------------
# Automatic Process Lifetime & Heartbeat Watchdog
# --------------------------------------------------------------------------
_last_heartbeat_time = time.time()
_startup_time = time.time()
_heartbeat_seen = False
_watchdog_active = True
_shutdown_timer: Optional[threading.Timer] = None

def record_heartbeat():
    global _last_heartbeat_time, _heartbeat_seen, _shutdown_timer
    _last_heartbeat_time = time.time()
    _heartbeat_seen = True
    # Cancel pending shutdown timer if frontend reconnected (e.g. after refresh/F5)
    if _shutdown_timer is not None:
        try:
            _shutdown_timer.cancel()
            logger.info("Cancelled pending shutdown; frontend heartbeat restored.")
        except Exception:
            pass
        _shutdown_timer = None

def _watchdog_monitor():
    """
    Background daemon thread that monitors frontend connectivity.
    Safely shuts down the background process if no frontend has communicated
    for more than 120 seconds AND no active downloads are currently running.
    """
    time.sleep(60.0)  # Generous startup grace period
    while _watchdog_active:
        time.sleep(5.0)
        now = time.time()
        # Never terminate if any task is actively downloading or converting
        has_active = any(
            t.status not in ("completed", "failed", "cancelled")
            for t in getattr(task_manager, "tasks", {}).values()
        )
        if has_active:
            continue

        # If client connected and then stopped heartbeats for > 120 seconds:
        if _heartbeat_seen and (now - _last_heartbeat_time > 120.0):
            logger.info("Frontend window closed/disconnected (heartbeat lost for >120s). Terminating background server.")
            os._exit(0)
        # If client never connected after 180 seconds total:
        if not _heartbeat_seen and (now - _startup_time > 180.0):
            logger.warning("No frontend connected within 180s of startup. Terminating orphaned background server.")
            os._exit(0)

# Start watchdog in background daemon thread
threading.Thread(target=_watchdog_monitor, daemon=True).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    task_manager.set_loop(loop)
    from app.downloader import get_ffmpeg_path
    ff = get_ffmpeg_path()
    if ff:
        logger.info(f"FFmpeg binary detected and ready at: {ff}")
    else:
        logger.warning("No FFmpeg binary found! High-res (1080p/720p) stream merging will be unavailable.")

    logger.info(f"FastAPI Server started on {SERVER_HOST}:{SERVER_PORT} with TaskManager initialized.")
    yield
    logger.info("FastAPI Server shutting down.")

app = FastAPI(
    title="OmniDownloader Web App",
    description="Hardened universal video and playlist downloader with real-time SSE progress",
    version=APP_VERSION,
    lifespan=lifespan
)

# --------------------------------------------------------------------------
# Task 1: Host, Origin, and Auth Token Validation Middleware
# --------------------------------------------------------------------------
@app.middleware("http")
async def security_and_auth_middleware(request: Request, call_next):
    # 1. Host header validation: allow only 127.0.0.1, localhost, or testserver (with optional numeric port)
    host = request.headers.get("host", "").strip().lower()
    valid_host = bool(re.match(r"^(127\.0\.0\.1|localhost|testserver)(:\d+)?$", host))
    if not valid_host:
        return JSONResponse(
            status_code=403,
            content={
                "code": "FORBIDDEN",
                "message": f"Rejected request with unauthorized Host header: '{host}'",
                "hint": "Requests must be addressed to 127.0.0.1 or localhost."
            }
        )

    # 2. Origin validation: if Origin header is present, ensure it matches our origin
    origin = request.headers.get("origin")
    if origin:
        origin_clean = origin.strip().lower()
        allowed_origins = {
            f"http://127.0.0.1:{SERVER_PORT}",
            f"http://localhost:{SERVER_PORT}",
            "http://127.0.0.1",
            "http://localhost",
        }
        if origin_clean not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={
                    "code": "FORBIDDEN",
                    "message": f"Cross-origin request from '{origin}' rejected.",
                    "hint": "API requests must originate from the local application.",
                    "source": "app"
                }
            )

    # 3. Require X-Auth-Token on every /api/* request (except /api/token, /api/heartbeat, and /api/shutdown)
    if request.url.path.startswith("/api/") and request.url.path not in ("/api/token", "/api/heartbeat", "/api/shutdown"):
        token = request.headers.get("x-auth-token")
        if not token:
            token = request.query_params.get("token")

        if not token or not secrets.compare_digest(token, API_TOKEN):
            return JSONResponse(
                status_code=401,
                content={
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid authentication token.",
                    "hint": "Provide valid token in X-Auth-Token header or ?token= query parameter.",
                    "source": "app"
                }
            )

    record_heartbeat()
    response = await call_next(request)
    return response

# --------------------------------------------------------------------------
# Task 7: Standardized Error Shape Exception Handlers
# --------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "HTTP_ERROR"
    hint = "Verify your request parameters and try again."
    source = "app"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
        hint = "Provide valid token in X-Auth-Token header or ?token= query parameter."
    elif exc.status_code == 403:
        code = "FORBIDDEN"
        hint = "Action forbidden: resource is restricted or path is outside downloads directory."
    elif exc.status_code == 404:
        code = "NOT_FOUND"
        hint = "The requested resource or task does not exist."
    elif exc.status_code == 413:
        code = "PAYLOAD_TOO_LARGE"
        hint = f"Uploaded content exceeds size limit ({MAX_COOKIE_SIZE // (1024*1024)} MB)."
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"
        hint = "Ensure all request parameters conform to required schema."

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": str(exc.detail), "hint": hint, "source": source}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0].get("msg", "Validation error") if errors else "Invalid request data"
    loc = " -> ".join(str(l) for l in errors[0].get("loc", [])) if errors else ""
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": f"{loc}: {msg}" if loc else msg,
            "hint": "Check field types, values, and allowable choices.",
            "source": "app"
        }
    )

@app.exception_handler(MediaExtractionError)
async def media_extraction_handler(request: Request, exc: MediaExtractionError):
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.detail.code,
            "message": exc.detail.message,
            "hint": exc.detail.hint,
            "source": exc.detail.source
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    detail = map_ytdlp_error(exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": detail.code,
            "message": detail.message,
            "hint": detail.hint,
            "source": detail.source
        }
    )

# --------------------------------------------------------------------------
# Task 1: Token Injection at Serve Time
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index():
    """Serves frontend index.html with authentication token injected."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found.")
    html = index_path.read_text(encoding="utf-8")
    injection = f'<script>window.__AUTH_TOKEN__ = "{API_TOKEN}";</script>'
    if "</head>" in html:
        html = html.replace("</head>", f"  {injection}\n</head>", 1)
    else:
        html = f"{injection}\n{html}"
    return HTMLResponse(content=html, status_code=200)

# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------
@app.post("/api/info", response_model=MediaInfoResponse)
async def get_media_info(request: InfoRequest):
    """Fetches title, thumbnails, format options, and playlist entries with auto browser cookie fallback."""
    loop = asyncio.get_running_loop()
    cookie_browser_val = request.cookie_browser.value if request.cookie_browser else None
    info = await loop.run_in_executor(
        task_manager.executor,
        extract_media_info,
        request.url,
        cookie_browser_val,
        True
    )
    return info

@app.post("/api/download")
async def start_download(request: DownloadRequest):
    """Initiates background download task."""
    task_id = task_manager.create_task(request)
    task_manager.start_download(task_id, request)
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Download task queued successfully."
    }

@app.get("/api/progress/{task_id}")
async def get_download_progress(task_id: str):
    """Server-Sent Events endpoint streaming real-time download progress."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return EventSourceResponse(task_manager.subscribe(task_id))

@app.get("/api/status/{task_id}", response_model=DownloadTaskStatus)
async def get_task_status(task_id: str):
    """Status endpoint for polling fallback."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_download_task(task_id: str):
    """Task 5: Cancels an active download task."""
    success = task_manager.cancel_task(task_id)
    task = task_manager.get_task(task_id)
    if not success and not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {
        "status": "success",
        "task_id": task_id,
        "message": "Task cancellation requested.",
        "state": task.status if task else "cancelled"
    }

@app.get("/api/file/{task_id}")
async def download_file_browser(task_id: str):
    """
    Task 2: Directly serves the downloaded file as a browser attachment.
    Enforces strict path traversal checks against DOWNLOADS_DIR.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "completed" or not task.output_files:
        raise HTTPException(status_code=400, detail="File is not yet ready or download failed")

    file_path = Path(task.output_files[0]).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found on server disk")

    # Strict path traversal validation
    allowed_dirs = [DOWNLOADS_DIR.resolve(), get_default_download_dir().resolve()]
    if hasattr(task, "download_dir") and task.download_dir:
        allowed_dirs.append(Path(task.download_dir).resolve())
    if not any(file_path == d or file_path.is_relative_to(d) for d in allowed_dirs if d.exists()):
        raise HTTPException(status_code=403, detail="Access denied: path is outside downloads directory.")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )

@app.post("/api/open-folder")
async def open_downloads_folder(task_id: Optional[str] = None):
    """
    Opens Windows Explorer highlighting the downloaded file, or opening the download folder.
    """
    try:
        current_dir = get_default_download_dir().resolve()
        target_path = None

        if task_id:
            task = task_manager.get_task(task_id)
            if task:
                # 1. Output files from task
                if task.output_files:
                    for f in task.output_files:
                        cand = Path(f).resolve()
                        if cand.exists() and cand.is_file():
                            target_path = cand
                            current_dir = cand.parent
                            break
                        elif cand.parent.exists():
                            target_path = cand.parent
                            current_dir = cand.parent
                            break

                # Path traversal check on requested task path
                if target_path:
                    allowed_dirs = [DOWNLOADS_DIR.resolve(), get_default_download_dir().resolve()]
                    if hasattr(task, "download_dir") and task.download_dir:
                        allowed_dirs.append(Path(task.download_dir).resolve())
                    if not any(target_path == d or target_path.is_relative_to(d) for d in allowed_dirs if d.exists()):
                        raise HTTPException(status_code=403, detail="Access denied: path is outside downloads directory.")

                # 2. Task recorded download_dir
                if not target_path and hasattr(task, "download_dir") and task.download_dir:
                    t_dir = Path(task.download_dir).resolve()
                    if t_dir.exists():
                        target_path = t_dir
                        current_dir = t_dir

        if not target_path:
            target_path = current_dir

        # 3. If target_path is a directory, look for recently downloaded media in it
        if target_path.is_dir() and target_path.exists():
            valid_exts = ('.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.wav', '.opus', '.flac')
            candidates = [f for f in target_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            if candidates:
                candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                target_path = candidates[0]

        if not target_path.exists():
            target_path = current_dir
            target_path.mkdir(parents=True, exist_ok=True)

        norm_path = os.path.normpath(str(target_path))
        logger.info(f"Opening in Explorer: {norm_path}")

        if os.name == 'nt':
            if target_path.is_file():
                # Windows Explorer syntax: explorer.exe /select,"C:\path\file.mp4"
                # Single formatted string prevents Python list2cmdline from quoting "/select," which breaks Explorer switch parsing
                subprocess.Popen(f'explorer.exe /select,"{norm_path}"', creationflags=NO_WINDOW_FLAG)
            else:
                subprocess.Popen(f'explorer.exe "{norm_path}"', creationflags=NO_WINDOW_FLAG)
        elif sys.platform == 'darwin':
            if target_path.is_file():
                subprocess.Popen(["open", "-R", norm_path])
            else:
                subprocess.Popen(["open", norm_path])
        else:
            folder = norm_path if target_path.is_dir() else str(target_path.parent)
            subprocess.Popen(["xdg-open", folder])

        return {"status": "success", "opened_path": norm_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening folder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to open downloads folder.")

@app.post("/api/open-file")
async def open_downloaded_file(task_id: str):
    """
    Directly opens/plays the downloaded file in the user's default system player with guaranteed resolution.
    """
    task = task_manager.get_task(task_id)
    file_to_open: Optional[Path] = None

    if task and task.output_files:
        for f in task.output_files:
            cand = Path(f).resolve()
            if cand.exists() and cand.is_file():
                file_to_open = cand
                break

    # Robust fallback: look in task's download dir or default download dir for the newest media file
    if not file_to_open:
        valid_exts = ('.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.wav', '.opus', '.flac')
        search_dirs = [get_default_download_dir().resolve()]
        if task and hasattr(task, "download_dir") and task.download_dir:
            search_dirs.insert(0, Path(task.download_dir).resolve())

        for sdir in search_dirs:
            if sdir.exists() and sdir.is_dir():
                candidates = [f for f in sdir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
                if candidates:
                    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    file_to_open = candidates[0]
                    break

    if not file_to_open or not file_to_open.exists():
        raise HTTPException(status_code=404, detail="Downloaded media file could not be located on disk.")

    norm_path = os.path.normpath(str(file_to_open))
    logger.info(f"Launching media file: {norm_path}")
    try:
        if os.name == 'nt':
            try:
                os.startfile(norm_path)
            except Exception as e:
                logger.warning(f"os.startfile failed ({e}), attempting fallback: {norm_path}")
                subprocess.Popen(["explorer.exe", norm_path], creationflags=NO_WINDOW_FLAG)
        elif sys.platform == 'darwin':
            subprocess.Popen(["open", norm_path])
        else:
            subprocess.Popen(["xdg-open", norm_path])
        return {"status": "success", "file": norm_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching file {norm_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to launch downloaded media file.")

@app.get("/api/token")
async def get_session_token(request: Request):
    """Allows local application clients to retrieve or synchronize active session token."""
    # Defend against cross-site token exfiltration via Sec-Fetch-Site
    fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
    if fetch_site == "cross-site":
        logger.warning(f"Rejected cross-site request for session token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=403, detail="Cross-site access denied.")
    return {"token": API_TOKEN}

@app.get("/api/download-dir")
async def get_download_directory():
    """Returns the current active download directory."""
    dir_path = get_default_download_dir()
    return {"download_dir": str(dir_path)}

@app.post("/api/download-dir")
async def update_download_directory(request: SetDownloadDirRequest):
    """Sets and persists a custom download directory, safely stripping surrounding quotes."""
    try:
        raw = request.download_dir.strip().strip('"\'')
        if not raw:
            raw = str(get_default_download_dir())
        new_path = Path(raw).expanduser().resolve()
        saved = set_download_dir(new_path)
        return {"status": "success", "download_dir": str(saved)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set download directory '{request.download_dir}': {e}")
        raise HTTPException(status_code=400, detail="Invalid directory path provided.")

@app.post("/api/choose-folder")
async def trigger_folder_picker():
    """
    Opens native Windows folder selection dialog and returns the chosen folder.
    Guarantees exactly ONE dialog is shown; closing or cancelling immediately returns
    status='cancelled' without falling back to secondary or tertiary popups.
    """
    curr = str(get_default_download_dir())
    if os.name != 'nt':
        return {"status": "error", "message": "Folder picker only supported on Windows.", "download_dir": curr, "path": curr}

    loop = asyncio.get_running_loop()

    # Method 1: Python Tkinter in threadpool executor (no shell spawn needed)
    def _tk_ask() -> tuple[str, Optional[str]]:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            res = filedialog.askdirectory(
                parent=root,
                title="Select Download Destination Folder",
                initialdir=curr
            )
            root.destroy()
            if res:
                return ("OK", str(res).strip())
            else:
                return ("CANCEL", None)
        except Exception as e:
            logger.debug(f"Tkinter folder picker not available: {e}")
            return ("ERROR", None)

    try:
        status, tk_res = await loop.run_in_executor(None, _tk_ask)
        if status == "OK" and tk_res and Path(tk_res).is_dir():
            saved = set_download_dir(Path(tk_res))
            return {"status": "success", "download_dir": str(saved), "path": str(saved)}
        elif status == "CANCEL":
            # User explicitly closed or cancelled the dialog. Never open secondary popups!
            return {"status": "cancelled", "download_dir": curr, "path": curr}
    except Exception as e:
        logger.debug(f"Tkinter method error: {e}")

    # Method 2: Fallback ONLY if Tkinter itself was missing/failed to load
    # Single dialog that exits immediately whether OK or Cancelled.
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = 'Select download destination folder for OmniDownloader'
$f.ShowNewFolderButton = $true
$f.SelectedPath = '{curr}'
$res = $f.ShowDialog()
if ($res -eq [System.Windows.Forms.DialogResult]::OK -and $f.SelectedPath) {{
    [Console]::Out.Write($f.SelectedPath)
}}
exit 0
"""
    try:
        import base64
        encoded = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-STA", "-EncodedCommand", encoded,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=NO_WINDOW_FLAG
        )
        stdout, stderr = await proc.communicate()
        chosen = stdout.decode("utf-8", errors="replace").strip().strip('"\'')
        if chosen and Path(chosen).is_dir():
            saved = set_download_dir(Path(chosen))
            return {"status": "success", "download_dir": str(saved), "path": str(saved)}
        return {"status": "cancelled", "download_dir": curr, "path": curr}
    except Exception as e:
        logger.warning(f"PowerShell folder picker error: {e}")

    return {"status": "cancelled", "download_dir": curr, "path": curr}

@app.get("/api/system-status")
async def get_system_status():
    """
    Returns system readiness status including FFmpeg availability,
    recommended resolution options, and installation instructions.
    """
    from app.downloader import get_ffmpeg_path
    ff_path = get_ffmpeg_path()
    has_ffmpeg = bool(ff_path and Path(ff_path).is_file())
    
    return {
        "status": "ready" if has_ffmpeg else "warning",
        "ffmpeg_installed": has_ffmpeg,
        "ffmpeg_path": ff_path if has_ffmpeg else None,
        "recommended_winget": "winget install Gyan.FFmpeg",
        "official_download_url": "https://www.gyan.dev/ffmpeg/builds/",
        "message": (
            "FFmpeg is ready. High-resolution stream merging (1080p, 4K) and MP3 conversion are active."
            if has_ffmpeg else
            "FFmpeg is required for 1080p/4K video merging and MP3 audio conversion."
        )
    }

@app.post("/api/install-ffmpeg")
async def auto_install_ffmpeg():
    """
    Attempts automated 1-click installation of FFmpeg for Windows:
    1. Try running `winget install Gyan.FFmpeg`
    2. Fallback to downloading standalone binaries from official builds into USER_DATA_DIR / 'ffmpeg.exe'.
    """
    import urllib.request
    import zipfile
    import io
    from app.downloader import get_ffmpeg_path, ensure_ffmpeg_in_path
    from app.config import USER_DATA_DIR

    curr = get_ffmpeg_path()
    if curr and Path(curr).is_file():
        return {"status": "success", "message": "FFmpeg is already installed and ready.", "ffmpeg_path": curr}

    # 1. Try winget if on Windows
    if os.name == 'nt':
        try:
            logger.info("Attempting automated winget installation of Gyan.FFmpeg...")
            proc = await asyncio.create_subprocess_exec(
                "winget", "install", "Gyan.FFmpeg", "--accept-package-agreements", "--accept-source-agreements", "--silent",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=NO_WINDOW_FLAG
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=35.0)
                ff = get_ffmpeg_path()
                if ff and Path(ff).is_file():
                    return {"status": "success", "message": "FFmpeg installed successfully via winget!", "ffmpeg_path": ff}
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Winget install attempt notice: {e}")

    # 2. Try direct download of standalone ffmpeg.exe into USER_DATA_DIR
    target_exe = USER_DATA_DIR / "ffmpeg.exe"
    download_urls = [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ]

    loop = asyncio.get_running_loop()

    def _download_and_extract():
        for url in download_urls:
            try:
                logger.info(f"Downloading FFmpeg from {url}...")
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for filename in z.namelist():
                        if filename.endswith("ffmpeg.exe"):
                            with z.open(filename) as src, open(target_exe, "wb") as dst:
                                dst.write(src.read())
                            ensure_ffmpeg_in_path(str(target_exe))
                            return str(target_exe)
            except Exception as ex:
                logger.warning(f"Download attempt from {url} failed: {ex}")
        return None

    try:
        installed = await loop.run_in_executor(None, _download_and_extract)
        if installed and Path(installed).is_file():
            return {
                "status": "success",
                "message": "FFmpeg successfully installed and registered!",
                "ffmpeg_path": installed
            }
    except Exception as e:
        logger.error(f"Automated FFmpeg download failed: {e}")

    raise HTTPException(
        status_code=500,
        detail="Automated install failed. Please open PowerShell and run 'winget install Gyan.FFmpeg' or visit https://www.gyan.dev/ffmpeg/builds/"
    )

# --------------------------------------------------------------------------
# Task 3: Cookie Validation & Lifecycle
# --------------------------------------------------------------------------
def is_valid_netscape_cookie_file(content: bytes) -> bool:
    """Validates that bytes match Netscape cookie file standards."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    if any(line.startswith("# Netscape HTTP Cookie File") or line.startswith("# HTTP Cookie File") for line in lines[:5]):
        return True

    valid_records = 0
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 7:
            valid_records += 1

    return valid_records > 0

@app.get("/api/cookies-status")
async def get_cookies_status():
    """Returns whether cookies.txt is currently installed and active in user data dir."""
    exists = COOKIES_FILE.exists()
    return {
        "has_cookies_file": exists,
        "size_bytes": COOKIES_FILE.stat().st_size if exists else 0,
        "path": str(COOKIES_FILE) if exists else None
    }

@app.post("/api/upload-cookies")
async def upload_cookies(request: Request):
    """
    Task 3: Validates and saves cookies.txt into user data directory.
    Enforces 2 MB size cap and Netscape format validation.
    """
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded cookie file is empty.")

    if len(content) > MAX_COOKIE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Cookie file exceeds maximum allowed size of {MAX_COOKIE_SIZE // (1024*1024)} MB."
        )

    if not is_valid_netscape_cookie_file(content):
        raise HTTPException(
            status_code=400,
            detail="Invalid cookie format. File must be Netscape format (# Netscape HTTP Cookie File or 7 tab-separated fields)."
        )

    COOKIES_FILE.write_bytes(content)
    logger.info(f"Saved cookies.txt to {COOKIES_FILE} ({len(content)} bytes)")
    return {"status": "success", "message": "cookies.txt successfully loaded and active!"}

@app.delete("/api/cookies")
async def delete_cookies():
    """Deletes existing cookies.txt file from user data directory."""
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
        logger.info(f"Deleted {COOKIES_FILE}")
    return {"status": "success", "message": "cookies.txt removed."}

# --------------------------------------------------------------------------
# Task 6: Engine Updater Endpoints
# --------------------------------------------------------------------------
@app.get("/api/engine/version")
async def get_engine_version():
    """Returns currently loaded yt-dlp version."""
    import yt_dlp
    return {
        "installed_version": getattr(yt_dlp.version, "__version__", "unknown"),
        "engine_dir": str(ENGINE_DIR)
    }

@app.post("/api/engine/update")
async def update_engine():
    """
    Task 6: Installs/updates yt-dlp into isolated user data engine directory.
    Maintains backup for rollback if installation fails.
    """
    import yt_dlp
    import importlib
    prev_version = getattr(yt_dlp.version, "__version__", "unknown")
    backup_dir = USER_DATA_DIR / "engine_backup"

    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if ENGINE_DIR.exists():
            shutil.copytree(ENGINE_DIR, backup_dir)

        # Execute pip install -U yt-dlp into ENGINE_DIR
        cmd = [
            sys.executable, "-m", "pip", "install", "-U", "yt-dlp",
            "--target", str(ENGINE_DIR),
            "--no-warn-script-location"
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, creationflags=NO_WINDOW_FLAG)
        if proc.returncode != 0:
            raise RuntimeError(f"pip install failed: {proc.stderr or proc.stdout}")

        # Invalidate module cache and reload
        importlib.invalidate_caches()
        importlib.reload(yt_dlp)
        new_version = getattr(yt_dlp.version, "__version__", "unknown")

        return {
            "status": "success",
            "previous_version": prev_version,
            "current_version": new_version
        }
    except Exception as e:
        logger.error(f"Engine update failed, rolling back: {e}")
        if backup_dir.exists():
            if ENGINE_DIR.exists():
                shutil.rmtree(ENGINE_DIR)
            shutil.copytree(backup_dir, ENGINE_DIR)
        raise HTTPException(
            status_code=500,
            detail=f"Engine update failed: {str(e)}. Previous version {prev_version} retained."
        )
    finally:
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except Exception:
                pass

# --------------------------------------------------------------------------
# Application Updater Endpoints
# --------------------------------------------------------------------------
@app.get("/api/app/version")
async def get_app_version():
    """Returns current OmniDownloader application version and repository."""
    return {
        "version": APP_VERSION,
        "repository": GITHUB_REPO
    }

@app.get("/api/app/update/check")
async def check_app_update(force: bool = False):
    """
    Checks GitHub Releases for new OmniDownloader versions.
    Supports force parameter to bypass cache.
    """
    result = await asyncio.to_thread(updater.check_for_updates, force=force)
    return result

@app.post("/api/app/update/download")
async def start_app_update_download(req: UpdateDownloadRequest):
    """Initiates streaming download of the update installer executable in the background."""
    result = await asyncio.to_thread(
        updater.start_download,
        download_url=req.download_url,
        expected_size=req.expected_size or 0,
        version_tag=req.version_tag or "latest"
    )
    return result

@app.get("/api/app/update/download-progress")
async def get_app_update_progress():
    """Returns current status and telemetry of the update download."""
    return updater.get_status()

@app.post("/api/app/update/cancel")
async def cancel_app_update():
    """Cancels active update download."""
    return updater.cancel_download()

@app.post("/api/app/update/apply")
async def apply_app_update(req: UpdateApplyRequest):
    """
    Executes the Inno Setup installer and initiates clean application restart.
    """
    try:
        result = updater.apply_update(
            installer_path=req.installer_path,
            silent=req.silent
        )
        return result
    except Exception as e:
        logger.error(f"Failed to apply update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------
# Process Lifetime Management Endpoints
# --------------------------------------------------------------------------
@app.api_route("/api/heartbeat", methods=["GET", "POST"])
async def api_heartbeat():
    """Receives periodic frontend ping to keep background process alive."""
    record_heartbeat()
    return {"status": "alive"}

@app.api_route("/api/shutdown", methods=["GET", "POST"])
async def api_shutdown():
    """
    Called when frontend window unloads or closes.
    Schedules a 15-second grace shutdown. If the user was just refreshing (F5),
    the reloaded page sends a heartbeat and cancels this timer within ~1 second.
    If the window was actually closed, the process terminates after 15 seconds.
    """
    global _shutdown_timer
    logger.info("Received window unload notification. Scheduling 15s grace termination...")
    if _shutdown_timer is not None:
        try:
            _shutdown_timer.cancel()
        except Exception:
            pass

    def _do_grace_exit():
        # Check if tasks are active before terminating
        has_active = any(
            t.status not in ("completed", "failed", "cancelled")
            for t in getattr(task_manager, "tasks", {}).values()
        )
        if has_active:
            logger.info("Active download in progress; deferring auto-shutdown.")
            return
        logger.info("Window closed and no reconnection within 15s grace period. Terminating process cleanly.")
        os._exit(0)

    _shutdown_timer = threading.Timer(15.0, _do_grace_exit)
    _shutdown_timer.daemon = True
    _shutdown_timer.start()
    return {"status": "scheduled", "grace_seconds": 15}

# Mount static frontend assets (css, js) with html=False so index.html hits token injector
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)

