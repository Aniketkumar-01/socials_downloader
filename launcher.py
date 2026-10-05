"""
OmniDownloader - Standalone Desktop Launcher
Boots the local FastAPI engine and automatically launches the user interface in the default web browser.
"""

import os
import sys
import time
import socket
import webbrowser
import threading
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

import uvicorn
from app.main import app

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

def open_browser_delayed(url: str, delay_seconds: float = 1.2):
    """Opens the local browser once the server has had a moment to initialize."""
    time.sleep(delay_seconds)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Notice: Could not automatically open browser: {e}")

def main():
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"

    print("=" * 64)
    print("  OmniDownloader - Universal Media & Playlist Downloader")
    print(f"  Running locally on: {url}")
    print("=" * 64)

    # Launch browser in a background daemon thread
    browser_thread = threading.Thread(
        target=open_browser_delayed,
        args=(url,),
        daemon=True
    )
    browser_thread.start()

    # Start Uvicorn server (blocking main thread)
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except (KeyboardInterrupt, SystemExit):
        print("\nOmniDownloader shutting down cleanly.")

if __name__ == "__main__":
    main()
