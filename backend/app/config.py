import os
import sys
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
FRONTEND_DIR = BASE_DIR / "frontend"

# User Data Directory (platformdirs with robust fallback)
try:
    import platformdirs
    USER_DATA_DIR = Path(platformdirs.user_data_dir("OmniDownloader", appauthor=False))
except Exception:
    if os.name == 'nt':
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        USER_DATA_DIR = Path(appdata) / "OmniDownloader" if appdata else Path.home() / ".omnidownloader"
    else:
        USER_DATA_DIR = Path.home() / ".local" / "share" / "OmniDownloader"

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Engine directory for isolated yt-dlp runtime updates
ENGINE_DIR = USER_DATA_DIR / "engine"
ENGINE_DIR.mkdir(parents=True, exist_ok=True)
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

# Persistent Cookie Jar in User Data directory
COOKIES_FILE = USER_DATA_DIR / "cookies.txt"

# Settings (Localhost binding only)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = int(os.getenv("PORT", "8000"))
MAX_DOWNLOAD_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
MAX_COOKIE_SIZE = 2 * 1024 * 1024  # 2 MB limit

# Windows device reserved names
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def sanitize_filename(title: str, max_length: int = 150) -> str:
    """
    Sanitizes filenames and folder names for Windows filesystem safety:
    strips illegal characters, escapes Windows device reserved names (CON, PRN, etc.),
    and enforces maximum length bounds.
    """
    if not title:
        return "untitled_video"
        
    # Replace illegal characters on Windows: < > : " / \ | ? * with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', str(title))
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized).strip('. ')
    
    # Handle Windows reserved device names (e.g., CON, AUX.mp4)
    stem = sanitized.split('.')[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        sanitized = f"_{sanitized}"
        
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('. ')
        
    return sanitized or "untitled_video"

