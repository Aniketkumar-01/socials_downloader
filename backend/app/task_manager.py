import asyncio
import uuid
import logging
import re
import time
import shutil
from typing import Dict, Optional, List, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from yt_dlp.utils import DownloadCancelled

from app.config import MAX_DOWNLOAD_WORKERS, USER_DATA_DIR, COOKIES_FILE, get_default_download_dir
from app.models import DownloadRequest, DownloadTaskStatus
from app.downloader import build_ydl_download_options, extract_media_info, map_ytdlp_error

logger = logging.getLogger(__name__)

class CancelledDownload(Exception):
    """Raised when a download task is cancelled by user request."""
    pass

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, DownloadTaskStatus] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.cancelled_tasks: Set[str] = set()
        self.last_emit_time: Dict[str, float] = {}
        self.executor = ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS)
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    @property
    def _tasks(self) -> Dict[str, DownloadTaskStatus]:
        return self.tasks

    @_tasks.setter
    def _tasks(self, val: Dict[str, DownloadTaskStatus]):
        self.tasks = val

    def get_task(self, task_id: str) -> Optional[DownloadTaskStatus]:
        return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Flags a task for cancellation and immediately updates state if active."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status not in ("completed", "failed", "cancelled"):
                self.cancelled_tasks.add(task_id)
                self.update_task_from_thread(
                    task_id,
                    force_notify=True,
                    status="cancelled",
                    current_item="Download cancelled by user.",
                    speed_str="--",
                    eta_str="--"
                )
                logger.info(f"Task {task_id} marked as cancelled.")
                return True
        return False

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self.cancelled_tasks

    def create_task(self, request: DownloadRequest) -> str:
        task_id = str(uuid.uuid4())[:8]
        effective_dir = request.download_dir.strip().strip('"\'') if request.download_dir else str(get_default_download_dir())
        status = DownloadTaskStatus(
            task_id=task_id,
            status="queued",
            progress=0.0,
            current_item="Queued for download...",
            total_items=1,
            completed_items=0,
            output_files=[],
            download_dir=effective_dir
        )
        self.tasks[task_id] = status
        self.subscribers[task_id] = []
        return task_id

    def notify_subscribers(self, task_id: str):
        """Pushes current task status to all registered SSE subscriber queues thread-safely."""
        task = self.tasks.get(task_id)
        if not task:
            return
            
        data = task.model_dump_json()
        queues = list(self.subscribers.get(task_id, []))
        for q in queues:
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(q.put_nowait, data)
            else:
                try:
                    q.put_nowait(data)
                except Exception:
                    pass

    def update_task_from_thread(self, task_id: str, force_notify: bool = False, **kwargs):
        """
        Thread-safe task state update with rate-limited subscriber notifications (max 5 events/sec).
        """
        task = self.tasks.get(task_id)
        if not task:
            return
            
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        now = time.time()
        last = self.last_emit_time.get(task_id, 0.0)
        # Throttle downloading events to at most 5/sec (0.2s interval) unless force_notify is set
        is_throttled = (kwargs.get("status") == "downloading" and (now - last < 0.20) and not force_notify)

        if not is_throttled:
            self.last_emit_time[task_id] = now
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.notify_subscribers, task_id)
            else:
                self.notify_subscribers(task_id)

    async def subscribe(self, task_id: str) -> AsyncGenerator[Dict[str, str], None]:
        """Async generator yielding SSE events for the given task_id."""
        task = self.tasks.get(task_id)
        if not task:
            yield {"data": '{"error": "Task not found"}'}
            return

        # Send initial status
        yield {"data": task.model_dump_json()}

        # If already completed or failed, close connection immediately
        if task.status in ("completed", "failed", "cancelled"):
            return

        queue = asyncio.Queue()
        if task_id not in self.subscribers:
            self.subscribers[task_id] = []
        self.subscribers[task_id].append(queue)

        try:
            while True:
                data = await queue.get()
                yield {"data": data}
                
                # If terminal state reached, close stream
                status = self.tasks.get(task_id)
                if status and status.status in ("completed", "failed", "cancelled"):
                    break
        finally:
            if task_id in self.subscribers and queue in self.subscribers[task_id]:
                self.subscribers[task_id].remove(queue)

    def run_download_worker(self, task_id: str, request: DownloadRequest):
        """Background worker executing yt-dlp download with cancellation and cookie isolation."""
        temp_cookie_path: Optional[Path] = None
        try:
            if self.is_cancelled(task_id):
                raise CancelledDownload("Task cancelled before execution started.")

            # Create per-task isolated cookie copy so yt-dlp writebacks cannot corrupt shared jar
            if COOKIES_FILE.exists():
                try:
                    temp_cookie_path = USER_DATA_DIR / f"cookie_task_{task_id}.txt"
                    shutil.copy2(COOKIES_FILE, temp_cookie_path)
                except Exception as c_err:
                    logger.warning(f"Failed to copy cookies for task {task_id}: {c_err}")
                    temp_cookie_path = None

            # 1. Fetch info
            self.update_task_from_thread(task_id, force_notify=True, status="fetching", current_item="Fetching media info...")
            
            cookie_browser_val = request.cookie_browser.value if hasattr(request.cookie_browser, "value") else request.cookie_browser
            media_info = extract_media_info(
                request.url,
                cookie_browser=cookie_browser_val,
                auto_probe_browsers=request.auto_probe_browsers,
                cookie_file=temp_cookie_path
            )

            if self.is_cancelled(task_id):
                raise CancelledDownload("Task cancelled after info extraction.")
            
            playlist_title = media_info.title if media_info.is_playlist else None
            items_to_download = media_info.items

            if request.is_playlist and request.selected_video_ids:
                selected_set = set(request.selected_video_ids)
                items_to_download = [item for item in items_to_download if item.id in selected_set]

            total_items = len(items_to_download)
            self.update_task_from_thread(
                task_id,
                force_notify=True,
                status="downloading",
                total_items=total_items,
                completed_items=0,
                current_item=f"Starting download of {total_items} item(s)..."
            )

            downloaded_files: List[str] = []

            # Progress hook callback
            def progress_hook(d: Dict):
                if self.is_cancelled(task_id):
                    raise DownloadCancelled("Download cancelled by user.")

                status = d.get('status')
                if status == 'downloading':
                    downloaded = float(d.get('downloaded_bytes') or 0)
                    total = float(d.get('total_bytes') or d.get('total_bytes_estimate') or 1)
                    percent = min(100.0, max(0.0, (downloaded / total) * 100)) if total > 0 else 0.0
                    
                    raw_speed = d.get('_speed_str', '')
                    raw_eta = d.get('_eta_str', '')
                    speed = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(raw_speed)).strip()
                    eta = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(raw_eta)).strip()
                    filename = Path(d.get('filename', '')).name

                    self.update_task_from_thread(
                        task_id,
                        status="downloading",
                        progress=round(percent, 1),
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        speed_str=speed or "--",
                        eta_str=eta or "--",
                        current_item=filename or "Downloading media..."
                    )
                elif status == 'finished':
                    final_path = d.get('filename')
                    if final_path:
                        downloaded_files.append(str(final_path))

            # Postprocessor hook callback for "merging" status
            def postprocessor_hook(d: Dict):
                if self.is_cancelled(task_id):
                    raise DownloadCancelled("Download cancelled by user.")

                pp_name = d.get('postprocessor', '')
                pp_status = d.get('status', '')
                if pp_status == 'started' or 'merg' in pp_name.lower() or 'remux' in pp_name.lower():
                    self.update_task_from_thread(
                        task_id,
                        force_notify=True,
                        status="merging",
                        current_item=f"Merging audio and video streams ({pp_name or 'ffmpeg'})..."
                    )
                elif pp_status == 'finished':
                    final_fp = d.get('filepath') or (d.get('info_dict') or {}).get('_filename') or (d.get('info_dict') or {}).get('filepath')
                    if final_fp:
                        downloaded_files.append(str(final_fp))

            clean_target = request.download_dir.strip().strip('"\'') if request.download_dir else None
            target_out_dir = Path(clean_target).expanduser().resolve() if clean_target else get_default_download_dir()
            target_out_dir.mkdir(parents=True, exist_ok=True)

            ydl_opts = build_ydl_download_options(
                quality=request.quality,
                output_dir=target_out_dir,
                is_playlist=request.is_playlist,
                playlist_title=playlist_title,
                platform=media_info.platform,
                cookie_browser=cookie_browser_val,
                cookie_file=temp_cookie_path,
                progress_hook=progress_hook,
                postprocessor_hook=postprocessor_hook
            )

            # Perform download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if request.is_playlist and request.selected_video_ids:
                    for idx, item in enumerate(items_to_download, 1):
                        if self.is_cancelled(task_id):
                            raise DownloadCancelled("Download cancelled by user.")
                        self.update_task_from_thread(
                            task_id,
                            current_item=f"({idx}/{total_items}) {item.title}",
                            completed_items=idx - 1
                        )
                        info = ydl.extract_info(item.url, download=True)
                        if info:
                            if 'requested_downloads' in info and info['requested_downloads']:
                                for req_d in info['requested_downloads']:
                                    fp = req_d.get('filepath') or req_d.get('_filename')
                                    if fp:
                                        downloaded_files.append(str(fp))
                            elif info.get('filepath'):
                                downloaded_files.append(str(info['filepath']))
                            elif info.get('_filename'):
                                downloaded_files.append(str(info['_filename']))
                            else:
                                downloaded_files.append(str(ydl.prepare_filename(info)))
                else:
                    self.update_task_from_thread(task_id, current_item=media_info.title)
                    info = ydl.extract_info(request.url, download=True)
                    if info:
                        if 'requested_downloads' in info and info['requested_downloads']:
                            for req_d in info['requested_downloads']:
                                fp = req_d.get('filepath') or req_d.get('_filename')
                                if fp:
                                    downloaded_files.append(str(fp))
                        elif info.get('filepath'):
                            downloaded_files.append(str(info['filepath']))
                        elif info.get('_filename'):
                            downloaded_files.append(str(info['_filename']))
                        else:
                            downloaded_files.append(str(ydl.prepare_filename(info)))

            # Resolve actual downloaded files on disk safely without bracket-glob syntax issues
            resolved_files = []
            valid_exts = ('.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.wav', '.opus', '.flac')
            for f in downloaded_files:
                p = Path(f)
                if p.exists() and p.is_file() and p.suffix.lower() in valid_exts:
                    resolved_files.append(str(p.resolve()))
                else:
                    # Strip temporary format markers like .f137, .f248, .temp
                    clean_stem = re.sub(r'(\.f[0-9]+|\.temp)$', '', p.stem)
                    if p.parent.exists() and p.parent.is_dir():
                        matches = [
                            m for m in p.parent.iterdir()
                            if m.is_file() and m.suffix.lower() in valid_exts and (m.stem == clean_stem or m.stem.startswith(clean_stem[:30]))
                        ]
                        if matches:
                            resolved_files.append(str(matches[0].resolve()))

            # If resolved_files is still empty, fallback to the newest media file created in target_out_dir
            if not resolved_files and target_out_dir.exists():
                recent_files = [
                    f for f in target_out_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in valid_exts
                ]
                if recent_files:
                    recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    resolved_files.append(str(recent_files[0].resolve()))

            # Deduplicate preserving order
            resolved_files = list(dict.fromkeys(resolved_files))

            # Mark task completed
            self.update_task_from_thread(
                task_id,
                force_notify=True,
                status="completed",
                progress=100.0,
                completed_items=total_items,
                speed_str="Complete",
                eta_str="00:00",
                current_item="Download completed successfully!",
                output_files=resolved_files
            )
            logger.info(f"Task {task_id} completed successfully. Output files: {resolved_files}")

        except (CancelledDownload, DownloadCancelled) as ce:
            logger.info(f"Task {task_id} cancelled: {ce}")
            self.update_task_from_thread(
                task_id,
                force_notify=True,
                status="cancelled",
                error_message="Download was cancelled by user.",
                current_item="Download was cancelled.",
                speed_str="--",
                eta_str="--"
            )
        except Exception as e:
            if self.is_cancelled(task_id) or "Download cancelled" in str(e):
                logger.info(f"Task {task_id} was cancelled during execution: {e}")
                self.update_task_from_thread(
                    task_id,
                    force_notify=True,
                    status="cancelled",
                    error_message="Download was cancelled by user.",
                    current_item="Download was cancelled.",
                    speed_str="--",
                    eta_str="--"
                )
                return

            logger.error(f"Error executing download task {task_id}: {e}", exc_info=True)
            detail = map_ytdlp_error(e)
            self.update_task_from_thread(
                task_id,
                force_notify=True,
                status="failed",
                error_message=detail.message,
                error_detail=detail,
                current_item=f"Failed: {detail.message}"
            )
        finally:
            # Clean up per-task temp cookie file
            if temp_cookie_path and temp_cookie_path.exists():
                try:
                    temp_cookie_path.unlink()
                except Exception:
                    pass

    def start_download(self, task_id: str, request: DownloadRequest):
        """Dispatches the worker onto the bounded thread pool executor."""
        self.executor.submit(self.run_download_worker, task_id, request)

# Global task manager instance
task_manager = TaskManager()

