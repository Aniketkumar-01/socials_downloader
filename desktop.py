"""
OmniDownloader - Native Windows Desktop PC Application
Launches OmniDownloader as a standalone Windows desktop app without browser tabs or address bars.
Supports PyWebView (native WebView2) or Windows Edge App Shell mode.
"""

import os
import sys
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path

# Setup paths
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OmniDownloader.Desktop")

def cleanup_obsolete_files():
    """Removes development scratch files, obsolete specifications, and test caches."""
    import shutil
    obsolete_files = [
        APP_DIR / "create_icon.py",
        APP_DIR / "iterations_done.md",
        APP_DIR / "SPEC.md",
        APP_DIR / "ARCHITECTURE.md",
        APP_DIR / "backend" / "tests" / "run_1000_iterations.py",
    ]
    for f in obsolete_files:
        if f.is_file():
            try:
                f.unlink()
                logger.info(f"Cleaned obsolete file: {f.name}")
            except Exception:
                pass

    obsolete_dirs = [
        APP_DIR / ".pytest_cache",
        APP_DIR / "tasks",
    ]
    for d in obsolete_dirs:
        if d.is_dir():
            try:
                shutil.rmtree(d)
                logger.info(f"Cleaned obsolete directory: {d.name}")
            except Exception:
                pass

def find_free_port(default_port=8000):
    """Checks if default port is free, or returns a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", default_port)) != 0:
            return default_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def wait_for_server(port, timeout=15):
    """Waits until the local FastAPI server responds on 127.0.0.1:port."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.2)
    return False

def run_uvicorn_server(port):
    """Runs uvicorn server in a background thread."""
    import uvicorn
    from app.main import app
    from app.config import SERVER_HOST

    config = uvicorn.Config(
        app=app,
        host=SERVER_HOST,
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

def find_windows_browser_app_executable():
    """Finds Microsoft Edge or Chrome executable on Windows for --app standalone window mode."""
    candidates = [
        # Edge on Windows 10 & 11 (preinstalled on 100% of systems)
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

def launch_desktop():
    cleanup_obsolete_files()
    port = find_free_port(8000)
    os.environ["PORT"] = str(port)

    # 1. Start server in background thread
    server_thread = threading.Thread(target=run_uvicorn_server, args=(port,), daemon=True)
    server_thread.start()

    logger.info(f"Starting OmniDownloader Desktop background server on port {port}...")
    if not wait_for_server(port, timeout=12):
        logger.error("Failed to connect to local server in time.")
        sys.exit(1)

    app_url = f"http://127.0.0.1:{port}"
    logger.info(f"Local server ready at {app_url}")

    # 2. Try PyWebView first if available
    try:
        import webview
        logger.info("Launching native WebView2 desktop window via PyWebView...")
        window = webview.create_window(
            title="OmniDownloader",
            url=app_url,
            width=1120,
            height=820,
            min_size=(860, 620),
            resizable=True,
            confirm_close=False
        )
        webview.start()
        logger.info("Desktop window closed. Exiting.")
        return
    except ImportError:
        logger.info("pywebview not installed; using Windows Native Edge App Shell...")
    except Exception as e:
        logger.warning(f"pywebview failed ({e}), falling back to Windows App Shell...")

    # 3. Windows Native Standalone App Window Mode
    browser_exe = find_windows_browser_app_executable()
    if browser_exe:
        logger.info(f"Launching standalone Windows PC application window via: {browser_exe}")
        cmd = [
            browser_exe,
            f"--app={app_url}",
            "--window-size=1120,820",
            "--app-id=OmniDownloader",
            f"--user-data-dir={os.path.expandvars(r'%LOCALAPPDATA%\OmniDownloader\DesktopProfile')}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        # Start and block until user closes the desktop application window
        proc = subprocess.Popen(cmd)
        proc.wait()
        logger.info("Desktop application window closed by user. Shutting down server.")
    else:
        # Fallback to default browser
        import webbrowser
        logger.info("Opening default browser...")
        webbrowser.open(app_url)
        # Keep process alive until user presses Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")

if __name__ == "__main__":
    launch_desktop()
