"""
OmniDownloader - Standalone Desktop Launcher
Launches OmniDownloader as a standalone Windows desktop application window (no browser tabs, no cmd console).
"""

import os
import sys
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path

# Add backend directory to sys.path so modules import seamlessly
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundle_dir = Path(sys._MEIPASS).resolve()
    sys.path.insert(0, str(bundle_dir / "backend"))
    sys.path.insert(0, str(bundle_dir))
else:
    root_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(root_dir / "backend"))
    sys.path.insert(0, str(root_dir))

    # Auto-switch to local virtual environment if dependencies are missing from current python
    for venv_candidate in [root_dir / "venv" / "Scripts" / "python.exe", root_dir / ".venv" / "Scripts" / "python.exe"]:
        if venv_candidate.is_file() and Path(sys.executable).resolve() != venv_candidate.resolve():
            try:
                import fastapi
                import uvicorn
            except ImportError:
                sys.exit(subprocess.call([str(venv_candidate)] + sys.argv))

import uvicorn
from app.main import app

NO_WINDOW_FLAG = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0

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
        # Microsoft Edge (present on all Windows 10 & 11 PCs)
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

def run_server(port: int):
    """Runs uvicorn in a background thread."""
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

def wait_for_server(port: int, timeout: float = 12.0) -> bool:
    """Waits until local server responds on 127.0.0.1:port."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.15)
    return False

def main():
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"
    os.environ["PORT"] = str(port)

    # 1. Start Uvicorn backend in background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # 2. Wait until server is listening
    if not wait_for_server(port):
        sys.exit(1)

    # 3. Launch Standalone Native PC Desktop App Window
    # Option A: Try PyWebView if available
    try:
        import webview
        window = webview.create_window(
            title="OmniDownloader",
            url=url,
            width=1180,
            height=840,
            min_size=(880, 640),
            resizable=True
        )
        webview.start()
        return
    except ImportError:
        pass
    except Exception:
        pass

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
        # Run windowed process and wait until user closes the desktop application window
        proc = subprocess.Popen(cmd, creationflags=NO_WINDOW_FLAG)
        proc.wait()
    else:
        # Fallback only if no Edge/Chrome found
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass

if __name__ == "__main__":
    main()
