"""
OmniDownloader - Standalone Desktop Launcher
Robust, self-healing launcher for OmniDownloader Windows desktop application.
Ensures visible feedback, persistent logging, native standalone app shell, and zero silent failures.
"""

import os
import sys
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path

# --------------------------------------------------------------------------
# Windows Mount Point and Symlink Hardening (WinError 448 Mitigation)
# --------------------------------------------------------------------------
_orig_realpath = getattr(os.path, '_orig_realpath', os.path.realpath)
os.path._orig_realpath = _orig_realpath

def _safe_realpath(path, *args, **kwargs):
    try:
        return _orig_realpath(path, *args, **kwargs)
    except OSError:
        try:
            return os.path.abspath(path)
        except Exception:
            return str(path)

os.path.realpath = _safe_realpath

def sanitize_system_path():
    if os.name != 'nt':
        return
    path_env = os.environ.get("PATH", "")
    if not path_env:
        return
    cleaned = []
    seen = set()
    for entry in path_env.split(os.pathsep):
        entry_clean = entry.strip().strip('"\'')
        if not entry_clean:
            continue
        normed = os.path.normcase(entry_clean)
        if normed in seen:
            continue
        seen.add(normed)
        try:
            _orig_realpath(entry_clean)
            cleaned.append(entry_clean)
        except OSError:
            replacement = None
            try:
                target = os.readlink(entry_clean)
                if not os.path.isabs(target):
                    target = os.path.join(os.path.dirname(entry_clean), target)
                if os.path.exists(target):
                    replacement = target
            except Exception:
                replacement = None
            if replacement:
                cleaned.append(replacement)
    os.environ["PATH"] = os.pathsep.join(cleaned)

sanitize_system_path()

# --------------------------------------------------------------------------
# Step 1: Immediate Directory & Logging Initialization
# --------------------------------------------------------------------------
def get_user_data_dir() -> Path:
    if os.name == 'nt':
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        d = Path(appdata) / "OmniDownloader" if appdata else Path.home() / ".omnidownloader"
    else:
        d = Path.home() / ".local" / "share" / "OmniDownloader"
    d.mkdir(parents=True, exist_ok=True)
    return d

USER_DATA_DIR = get_user_data_dir()
LOG_FILE = USER_DATA_DIR / "launcher.log"

# Configure file + console logging immediately so all early events are saved
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8", mode="a"),
        logging.StreamHandler(sys.stdout) if sys.stdout else logging.NullHandler()
    ]
)
logger = logging.getLogger("OmniDownloader.Launcher")

logger.info("=" * 65)
logger.info("OmniDownloader launcher started")
logger.info(f"Executable: {sys.executable}")
logger.info(f"Python: {sys.version.split()[0]}")
logger.info(f"Is Frozen (PyInstaller): {getattr(sys, 'frozen', False)}")

# Native Windows error and notification dialog helper
def show_native_message(title: str, message: str, is_error: bool = False):
    """Displays a native Windows message box so user is never left in the dark."""
    if os.name == 'nt':
        try:
            import ctypes
            icon = 0x10 if is_error else 0x40  # MB_ICONERROR or MB_ICONINFORMATION
            ctypes.windll.user32.MessageBoxW(0, message, title, icon | 0x0)
        except Exception as e:
            logger.warning(f"Failed to display native message box: {e}")

# --------------------------------------------------------------------------
# Step 2: System Path and Module Resolution
# --------------------------------------------------------------------------
try:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = Path(sys._MEIPASS).resolve()
        logger.info(f"PyInstaller bundle directory: {bundle_dir}")
        sys.path.insert(0, str(bundle_dir / "backend"))
        sys.path.insert(0, str(bundle_dir))
    else:
        root_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(root_dir / "backend"))
        sys.path.insert(0, str(root_dir))

        # Auto-switch to virtual environment if local python lacks fastapi/uvicorn
        for venv_candidate in [root_dir / "venv" / "Scripts" / "python.exe", root_dir / ".venv" / "Scripts" / "python.exe"]:
            if venv_candidate.is_file() and Path(sys.executable).resolve() != venv_candidate.resolve():
                try:
                    import fastapi
                    import uvicorn
                except ImportError:
                    logger.info(f"Re-launching inside virtualenv: {venv_candidate}")
                    sys.exit(subprocess.call([str(venv_candidate)] + sys.argv))

    import uvicorn
    from app.main import app
    logger.info("FastAPI backend and Uvicorn imported successfully.")
except Exception as e:
    err_msg = (
        f"OmniDownloader failed during initial module startup.\n\n"
        f"Error: {e}\n\n"
        f"A detailed diagnostic log was saved to:\n{LOG_FILE}"
    )
    logger.critical(err_msg, exc_info=True)
    show_native_message("OmniDownloader Startup Error", err_msg, is_error=True)
    sys.exit(1)

# --------------------------------------------------------------------------
# Step 3: Network & Helper Functions
# --------------------------------------------------------------------------
def is_port_in_use(port: int) -> bool:
    """Checks if a local TCP port is already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Finds the first available port on localhost."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    return start_port

def find_windows_browser_app_executable() -> str | None:
    """Finds Microsoft Edge or Chrome executable on Windows for standalone desktop window mode."""
    candidates = [
        # Microsoft Edge (pre-installed on 100% of Windows 10 & 11 PCs)
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # Brave
        os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return None

server_exception: Exception | None = None

def run_server(port: int):
    """Runs uvicorn in background thread with explicit, stable configurations."""
    global server_exception
    try:
        logger.info(f"Configuring Uvicorn server on 127.0.0.1:{port}...")
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_level="info",
            access_log=False,
            loop="asyncio",
            http="h11",
            ws="none",
            lifespan="on",
            log_config=None
        )
        server = uvicorn.Server(config)
        logger.info("Uvicorn server is now running.")
        server.run()
        logger.info("Uvicorn server exited cleanly.")
    except Exception as e:
        server_exception = e
        logger.error(f"Uvicorn server encountered an unexpected error: {e}", exc_info=True)

def wait_for_server(port: int, server_thread: threading.Thread, timeout: float = 15.0) -> bool:
    """Waits until local server responds on 127.0.0.1:port, checking thread health constantly."""
    start = time.time()
    while time.time() - start < timeout:
        if server_exception is not None:
            logger.error(f"Server thread reported exception: {server_exception}")
            return False
        if not server_thread.is_alive():
            logger.error("Server thread terminated prematurely.")
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.2)
    return False

def keep_server_alive(port: int, server_thread: threading.Thread):
    """Keeps the process alive while the background server is active."""
    logger.info(f"OmniDownloader active at http://127.0.0.1:{port}. Waiting for shutdown.")
    try:
        while server_thread.is_alive():
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")

# --------------------------------------------------------------------------
# Step 4: Main Application Lifecycle
# --------------------------------------------------------------------------
def main():
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"
    os.environ["PORT"] = str(port)
    logger.info(f"Selected port {port} for application.")

    # 1. Start Uvicorn backend in background daemon thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # 2. Wait until server is listening
    logger.info(f"Waiting for backend to initialize on {url}...")
    if not wait_for_server(port, server_thread, timeout=15.0):
        err_msg = (
            f"OmniDownloader was unable to start the background server on port {port}.\n\n"
            f"Details: {server_exception or 'Server thread did not respond in time.'}\n\n"
            f"Please check the log file for more information:\n{LOG_FILE}"
        )
        logger.critical(err_msg)
        show_native_message("OmniDownloader Startup Error", err_msg, is_error=True)
        sys.exit(1)

    logger.info(f"Backend is ready and listening at {url}")

    # 3. Launch Standalone Native PC Desktop App Window
    # Option A: Try PyWebView if available
    try:
        import webview
        logger.info("Attempting to open native WebView2 window via PyWebView...")
        window = webview.create_window(
            title="OmniDownloader",
            url=url,
            width=1180,
            height=840,
            min_size=(880, 640),
            resizable=True
        )
        webview.start()
        logger.info("WebView2 window closed by user.")
        return
    except ImportError:
        logger.info("pywebview not available; checking native Edge/Chrome app shell mode...")
    except Exception as e:
        logger.warning(f"pywebview startup failed ({e}), continuing to native browser shell...")

    # Option B: Windows Native App Shell Mode (Edge/Chrome in standalone window with no browser tabs/search bar)
    browser_exe = find_windows_browser_app_executable()
    if browser_exe:
        app_profile = os.path.expandvars(r"%LOCALAPPDATA%\OmniDownloader\AppShellProfile")
        cmd = [
            browser_exe,
            f"--app={url}",
            "--window-size=1180,840",
            "--app-id=OmniDownloader",
            f"--user-data-dir={app_profile}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        logger.info(f"Launching standalone app window via: {browser_exe}")
        try:
            # NOTE: DO NOT pass CREATE_NO_WINDOW! Edge is a GUI application.
            proc = subprocess.Popen(cmd)
            
            # Check if process exits immediately due to browser session delegation/handoff
            try:
                proc.wait(timeout=3.0)
                logger.info(f"Browser launcher process completed early (code {proc.returncode}). Session handed off to browser.")
                keep_server_alive(port, server_thread)
                return
            except subprocess.TimeoutExpired:
                # Browser is running as child process; wait until user closes the window
                proc.wait()
                logger.info("Desktop application window closed by user.")
                return
        except Exception as e:
            logger.warning(f"Failed to launch standalone app window: {e}")

    # Option C / Fallback: Open in default browser and keep server alive
    logger.info("Opening OmniDownloader in default browser...")
    import webbrowser
    webbrowser.open(url)
    keep_server_alive(port, server_thread)

if __name__ == "__main__":
    main()
