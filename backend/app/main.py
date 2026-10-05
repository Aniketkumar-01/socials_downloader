import os
import sys
import re
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
    MAX_COOKIE_SIZE
)
from app.models import (
    InfoRequest,
    MediaInfoResponse,
    DownloadRequest,
    DownloadTaskStatus
)
from app.downloader import extract_media_info, MediaExtractionError, map_ytdlp_error
from app.task_manager import task_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Startup random token for local API protection
API_TOKEN = secrets.token_urlsafe(32)

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
    version="1.1.0",
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
                    "hint": "API requests must originate from the local application."
                }
            )

    # 3. Require X-Auth-Token on every /api/* request (or ?token= query param for SSE)
    if request.url.path.startswith("/api/"):
        token = request.headers.get("x-auth-token")
        if not token:
            token = request.query_params.get("token")

        if not token or not secrets.compare_digest(token, API_TOKEN):
            return JSONResponse(
                status_code=401,
                content={
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid authentication token.",
                    "hint": "Provide valid token in X-Auth-Token header or ?token= query parameter."
                }
            )

    response = await call_next(request)
    return response

# --------------------------------------------------------------------------
# Task 7: Standardized Error Shape Exception Handlers
# --------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "HTTP_ERROR"
    hint = "Verify your request parameters and try again."
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
        content={"code": code, "message": str(exc.detail), "hint": hint}
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
            "hint": "Check field types, values, and allowable choices."
        }
    )

@app.exception_handler(MediaExtractionError)
async def media_extraction_handler(request: Request, exc: MediaExtractionError):
    return JSONResponse(
        status_code=400,
        content={"code": exc.detail.code, "message": exc.detail.message, "hint": exc.detail.hint}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    detail = map_ytdlp_error(exc)
    return JSONResponse(
        status_code=500,
        content={"code": detail.code, "message": detail.message, "hint": detail.hint}
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
    """Fetches title, thumbnails, format options, and playlist entries."""
    loop = asyncio.get_running_loop()
    cookie_browser_val = request.cookie_browser.value if request.cookie_browser else None
    info = await loop.run_in_executor(task_manager.executor, extract_media_info, request.url, cookie_browser_val)
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
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already in terminal state.")
    return {"status": "success", "task_id": task_id, "message": "Task cancellation requested."}

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
    downloads_root = DOWNLOADS_DIR.resolve()

    try:
        file_path.relative_to(downloads_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path is outside downloads directory.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server disk")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )

@app.post("/api/open-folder")
async def open_downloads_folder(task_id: Optional[str] = None):
    """
    Task 2: Opens Windows Explorer using safe argument lists with strict path verification.
    """
    try:
        downloads_root = DOWNLOADS_DIR.resolve()
        target_path = downloads_root

        if task_id:
            task = task_manager.get_task(task_id)
            if task and task.output_files:
                cand = Path(task.output_files[0]).resolve()
                if cand.exists():
                    target_path = cand

        # Path traversal guard
        try:
            target_path.relative_to(downloads_root)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: path is outside downloads directory.")

        if os.name == 'nt':
            if target_path.is_file():
                subprocess.Popen(["explorer", f"/select,{str(target_path)}"])
            else:
                subprocess.Popen(["explorer", str(target_path)])

        return {"status": "success", "opened_path": str(target_path)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
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

# Mount static frontend assets (css, js) with html=False so index.html hits token injector
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)

