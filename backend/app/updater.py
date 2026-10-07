import os
import sys
import re
import json
import time
import shutil
import logging
import urllib.request
import urllib.error
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from app.config import APP_VERSION, GITHUB_REPO, UPDATES_DIR

logger = logging.getLogger("OmniDownloader.Updater")

# --------------------------------------------------------------------------
# Version Parsing and Comparison Helpers
# --------------------------------------------------------------------------
def parse_semver(version_str: str) -> Tuple[int, ...]:
    """
    Extracts numerical version components from strings like 'v1.2.4', '1.2.4-beta', or '2026.1'.
    Returns a tuple of integers for reliable sorting/comparison.
    """
    if not version_str:
        return (0, 0, 0)
    # Strip leading 'v' / 'V' and split off prerelease info
    clean = version_str.strip().lstrip("vV")
    # Extract digit sequences
    parts = re.findall(r"\d+", clean)
    if not parts:
        return (0, 0, 0)
    return tuple(int(p) for p in parts)

def is_version_newer(remote_version: str, local_version: str) -> bool:
    """Returns True if remote_version is strictly higher than local_version."""
    remote_tuple = parse_semver(remote_version)
    local_tuple = parse_semver(local_version)
    
    # Pad tuples to matching lengths for comparison
    max_len = max(len(remote_tuple), len(local_tuple))
    r_padded = remote_tuple + (0,) * (max_len - len(remote_tuple))
    l_padded = local_tuple + (0,) * (max_len - len(local_tuple))
    
    return r_padded > l_padded

# --------------------------------------------------------------------------
# AppUpdater Class
# --------------------------------------------------------------------------
class AppUpdater:
    def __init__(self):
        self.lock = threading.Lock()
        self.cache_ttl_seconds = 300  # 5 minutes cache
        self.last_check_time: float = 0.0
        self.cached_check_result: Optional[Dict[str, Any]] = None
        
        # Download state tracking
        self.download_thread: Optional[threading.Thread] = None
        self.cancel_requested = False
        self.state: Dict[str, Any] = {
            "status": "idle",  # idle, downloading, completed, cancelled, failed
            "percent": 0.0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "speed_str": "--",
            "file_path": None,
            "error": None,
            "version": None
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the current snapshot of download state."""
        with self.lock:
            return dict(self.state)

    def check_for_updates(self, force: bool = False) -> Dict[str, Any]:
        """
        Queries the GitHub Releases API for the latest published release.
        Caches the response for 5 minutes unless force is True.
        """
        now = time.time()
        with self.lock:
            if not force and self.cached_check_result and (now - self.last_check_time < self.cache_ttl_seconds):
                logger.info("Returning cached GitHub release check result.")
                return dict(self.cached_check_result)

        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"OmniDownloader/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            logger.info(f"Checking for updates against {url}...")
            # 10 second timeout for network requests
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            release_name = data.get("name") or tag_name
            release_notes = data.get("body", "")
            release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")
            published_at = data.get("published_at", "")

            # Locate Windows installer executable in assets
            installer_asset = None
            portable_asset = None
            for asset in data.get("assets", []):
                asset_name = asset.get("name", "")
                if asset_name.lower().endswith("setup.exe"):
                    installer_asset = asset
                    break
                elif asset_name.lower().endswith(".exe") and "setup" not in asset_name.lower():
                    portable_asset = asset

            chosen_asset = installer_asset or portable_asset
            download_url = chosen_asset.get("browser_download_url") if chosen_asset else None
            file_size = chosen_asset.get("size", 0) if chosen_asset else 0
            asset_name = chosen_asset.get("name", "") if chosen_asset else ""

            update_available = is_version_newer(tag_name, APP_VERSION)

            result = {
                "status": "success",
                "current_version": APP_VERSION,
                "latest_version": tag_name.lstrip("vV"),
                "tag_name": tag_name,
                "update_available": update_available,
                "release_name": release_name,
                "release_notes": release_notes,
                "release_url": release_url,
                "download_url": download_url,
                "asset_name": asset_name,
                "file_size": file_size,
                "published_at": published_at
            }

            with self.lock:
                self.cached_check_result = result
                self.last_check_time = now

            logger.info(f"Update check complete: current={APP_VERSION}, latest={tag_name}, available={update_available}")
            return result

        except urllib.error.HTTPError as e:
            logger.warning(f"GitHub API returned HTTP {e.code}: {e.reason}")
            if e.code == 404:
                return {
                    "status": "success",
                    "current_version": APP_VERSION,
                    "latest_version": APP_VERSION,
                    "update_available": False,
                    "message": "No published releases found."
                }
            elif e.code == 403:
                return {
                    "status": "rate_limited",
                    "current_version": APP_VERSION,
                    "latest_version": "unknown",
                    "update_available": False,
                    "message": "GitHub API rate limit reached. Please try again later."
                }
            return {
                "status": "error",
                "current_version": APP_VERSION,
                "update_available": False,
                "message": f"GitHub HTTP Error: {e.code} {e.reason}"
            }
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return {
                "status": "error",
                "current_version": APP_VERSION,
                "update_available": False,
                "message": f"Unable to connect to update server: {str(e)}"
            }

    def start_download(self, download_url: str, expected_size: int = 0, version_tag: str = "") -> Dict[str, Any]:
        """Initiates a background download of the setup executable with byte-level progress."""
        with self.lock:
            if self.state["status"] == "downloading":
                return {"status": "busy", "message": "An update download is already in progress."}

            self.cancel_requested = False
            self.state = {
                "status": "downloading",
                "percent": 0.0,
                "downloaded_bytes": 0,
                "total_bytes": expected_size,
                "speed_str": "Starting...",
                "file_path": None,
                "error": None,
                "version": version_tag or "latest"
            }

        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(download_url, expected_size, version_tag),
            daemon=True
        )
        self.download_thread.start()
        return {"status": "started", "message": "Update download initiated."}

    def cancel_download(self) -> Dict[str, Any]:
        """Requests cancellation of active update download."""
        with self.lock:
            if self.state["status"] == "downloading":
                self.cancel_requested = True
                self.state["status"] = "cancelling"
                return {"status": "cancelling", "message": "Cancellation requested."}
        return {"status": "idle", "message": "No active download to cancel."}

    def _download_worker(self, download_url: str, expected_size: int, version_tag: str):
        """Worker thread executing streaming chunked download."""
        clean_tag = re.sub(r'[^a-zA-Z0-9._-]', '', version_tag) or "latest"
        target_file = UPDATES_DIR / f"OmniDownloader-Setup-{clean_tag}.exe"
        part_file = UPDATES_DIR / f"OmniDownloader-Setup-{clean_tag}.exe.part"

        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": f"OmniDownloader/{APP_VERSION}",
                "Accept": "*/*"
            }
        )

        try:
            logger.info(f"Downloading update from {download_url} to {part_file}...")
            start_time = time.time()
            last_speed_check = start_time
            last_bytes = 0
            speed_str = "Calculating..."

            with urllib.request.urlopen(req, timeout=30.0) as response, open(part_file, "wb") as out_f:
                total_len = response.headers.get("Content-Length")
                total_bytes = int(total_len) if total_len else expected_size
                with self.lock:
                    self.state["total_bytes"] = total_bytes

                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB

                while True:
                    if self.cancel_requested:
                        logger.info("Update download cancelled by user.")
                        try:
                            out_f.close()
                            if part_file.exists():
                                part_file.unlink()
                        except Exception:
                            pass
                        with self.lock:
                            self.state["status"] = "cancelled"
                            self.state["speed_str"] = "--"
                        return

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    elapsed_interval = now - last_speed_check
                    if elapsed_interval >= 0.5:
                        bytes_diff = downloaded - last_bytes
                        speed_bps = bytes_diff / elapsed_interval if elapsed_interval > 0 else 0
                        if speed_bps >= 1024 * 1024:
                            speed_str = f"{speed_bps / (1024 * 1024):.1f} MB/s"
                        elif speed_bps >= 1024:
                            speed_str = f"{speed_bps / 1024:.0f} KB/s"
                        else:
                            speed_str = f"{speed_bps:.0f} B/s"

                        last_bytes = downloaded
                        last_speed_check = now

                        percent = round((downloaded / total_bytes) * 100, 1) if total_bytes > 0 else 0.0
                        with self.lock:
                            self.state["percent"] = percent
                            self.state["downloaded_bytes"] = downloaded
                            self.state["speed_str"] = speed_str

            # Finalize download: Atomic rename part -> target
            if target_file.exists():
                target_file.unlink()
            shutil.move(str(part_file), str(target_file))

            # Validate downloaded binary on Windows (check PE MZ signature)
            with open(target_file, "rb") as f:
                header = f.read(2)
                if header != b"MZ":
                    raise ValueError("Downloaded file does not appear to be a valid Windows executable (missing MZ signature).")

            with self.lock:
                self.state["status"] = "completed"
                self.state["percent"] = 100.0
                self.state["downloaded_bytes"] = downloaded
                self.state["file_path"] = str(target_file.resolve())
                self.state["speed_str"] = "Download Complete"
            logger.info(f"Update downloaded and verified successfully: {target_file}")

        except Exception as e:
            logger.error(f"Error downloading update: {e}", exc_info=True)
            try:
                if part_file.exists():
                    part_file.unlink()
            except Exception:
                pass
            with self.lock:
                self.state["status"] = "failed"
                self.state["error"] = str(e)
                self.state["speed_str"] = "--"

    def apply_update(self, installer_path: Optional[str] = None, silent: bool = True) -> Dict[str, Any]:
        """
        Executes the Inno Setup installer executable.
        If silent is True, passes /SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS flags.
        Schedules clean process termination after 1.5 seconds so Inno Setup can update files.
        """
        path_to_run = None
        if installer_path:
            p = Path(installer_path).resolve()
            # Security check: must reside inside UPDATES_DIR and have .exe extension
            if p.exists() and p.suffix.lower() == ".exe" and UPDATES_DIR.resolve() in p.parents:
                path_to_run = p
        
        if not path_to_run:
            with self.lock:
                fp = self.state.get("file_path")
                if fp:
                    p = Path(fp).resolve()
                    if p.exists() and p.suffix.lower() == ".exe":
                        path_to_run = p

        if not path_to_run or not path_to_run.exists():
            raise FileNotFoundError("Update installer executable not found or invalid path.")

        cmd = [str(path_to_run)]
        if silent:
            # Inno Setup flags for unattended upgrade with application replacement
            cmd.extend(["/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])

        logger.info(f"Applying update with command: {cmd}")

        # Spawn installer process as independent detached process on Windows
        creationflags = 0
        if os.name == 'nt':
            # DETACHED_PROCESS = 0x00000008
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

        subprocess.Popen(cmd, creationflags=creationflags, close_fds=True)

        # Schedule application shutdown to release locks on running files promptly
        def _delayed_exit():
            time.sleep(0.4)
            logger.info("Exiting application for Inno Setup upgrade...")
            # Use os._exit to immediately bypass background thread joins
            os._exit(0)

        shutdown_thread = threading.Thread(target=_delayed_exit, daemon=True)
        shutdown_thread.start()

        return {
            "status": "applying",
            "message": "Update installer started. OmniDownloader will restart shortly."
        }

# Global Singleton Instance
updater = AppUpdater()
