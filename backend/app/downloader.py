import os
import re
import shutil
import logging
from typing import Dict, Any, Callable, Optional, List, Union
from pathlib import Path
import yt_dlp

from app.config import DOWNLOADS_DIR, sanitize_filename
from app.models import MediaInfoResponse, VideoItem, ErrorDetail

logger = logging.getLogger(__name__)

def format_seconds(seconds: Optional[Union[int, float]]) -> Optional[str]:
    """Convert duration in seconds to HH:MM:SS or MM:SS."""
    if seconds is None:
        return None
    seconds = int(round(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_size_bytes(num_bytes: Optional[Union[int, float]]) -> Optional[str]:
    """Formats byte counts into clean human-readable strings (e.g. '142 MB', '1.2 GB')."""
    if num_bytes is None or num_bytes <= 0:
        return None
    num = float(num_bytes)
    if num >= 1024 ** 3:
        return f"{num / (1024 ** 3):.2f} GB"
    elif num >= 1024 ** 2:
        return f"{num / (1024 ** 2):.1f} MB"
    elif num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{int(num)} B"

def estimate_format_bytes(fmt: Dict[str, Any], duration: Optional[Union[int, float]]) -> Optional[int]:
    """Estimates byte size of a stream format from filesize, filesize_approx, or bitrate * duration."""
    size = fmt.get('filesize') or fmt.get('filesize_approx')
    if size and size > 0:
        return int(size)
    dur = duration or fmt.get('duration')
    if dur and dur > 0:
        tbr = fmt.get('tbr')
        vbr = fmt.get('vbr') or 0
        abr = fmt.get('abr') or 0
        bitrate_kbps = tbr if (tbr and tbr > 0) else (vbr + abr)
        if bitrate_kbps and bitrate_kbps > 0:
            return int((bitrate_kbps * 1000 / 8) * float(dur))
    return None

def estimate_quality_sizes(info: Dict[str, Any]) -> tuple[Dict[str, Optional[int]], Dict[str, str]]:
    """Calculates approximate file sizes for each available quality option."""
    formats = info.get('formats') or []
    duration = info.get('duration')

    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    best_audio_size = 0
    if audio_formats:
        audio_formats.sort(key=lambda f: f.get('abr') or f.get('tbr') or 0, reverse=True)
        best_audio_size = estimate_format_bytes(audio_formats[0], duration) or 0
    elif duration and duration > 0:
        best_audio_size = int((128 * 1000 / 8) * float(duration))

    def get_best_video_size(max_dim: Optional[int]) -> Optional[int]:
        matching = []
        for f in formats:
            if f.get('vcodec') == 'none':
                continue
            h = f.get('height')
            w = f.get('width')
            dim = h if (h and h > 0) else w
            if max_dim is None or (dim and dim <= max_dim):
                matching.append(f)

        if not matching:
            all_video = [f for f in formats if f.get('vcodec') != 'none']
            if all_video:
                matching = all_video
            else:
                return None

        matching.sort(
            key=lambda f: (
                f.get('height') or f.get('width') or 0,
                f.get('tbr') or f.get('vbr') or 0
            ),
            reverse=True
        )
        chosen = matching[0]
        v_size = estimate_format_bytes(chosen, duration)
        if not v_size:
            return None

        if chosen.get('acodec') == 'none' and best_audio_size:
            return v_size + best_audio_size
        return v_size

    targets = {
        "best": None,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
    }

    quality_sizes: Dict[str, Optional[int]] = {}
    quality_sizes_formatted: Dict[str, str] = {}

    for q_key, max_dim in targets.items():
        v_size = get_best_video_size(max_dim)
        if v_size and v_size > 0:
            quality_sizes[q_key] = v_size
            quality_sizes_formatted[q_key] = f"~{format_size_bytes(v_size)}"
        else:
            g_size = info.get('filesize') or info.get('filesize_approx')
            if g_size:
                quality_sizes[q_key] = int(g_size)
                quality_sizes_formatted[q_key] = f"~{format_size_bytes(g_size)}"

    mp3_size = best_audio_size
    if not mp3_size and duration:
        mp3_size = int((192 * 1000 / 8) * float(duration))
    if mp3_size and mp3_size > 0:
        quality_sizes["audio_mp3"] = mp3_size
        quality_sizes_formatted["audio_mp3"] = f"~{format_size_bytes(mp3_size)}"

    return quality_sizes, quality_sizes_formatted

def detect_platform(url: str) -> str:
    """Detects social platform from URL."""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
        return 'bilibili'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    elif 'reddit.com' in url_lower:
        return 'reddit'
    return 'universal'

class MediaExtractionError(Exception):
    """Raised when metadata or stream extraction fails."""
    def __init__(self, detail: ErrorDetail):
        super().__init__(detail.message)
        self.detail = detail

def map_ytdlp_error(err: Any) -> ErrorDetail:
    """
    Standardized mapping of yt-dlp exceptions to {code, message, hint}.
    Supported codes:
    PRIVATE_VIDEO, AGE_RESTRICTED, GEO_BLOCKED, MEMBERS_ONLY,
    RATE_LIMITED, LIVE_STREAM, BOT_CHECK, FFMPEG_MISSING, ENGINE_OUTDATED, UNKNOWN.
    """
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(err)).strip()
    # Strip any external website or wiki URLs from the error message
    clean = re.sub(r'https?://\S+', '', clean).strip()
    clean = re.sub(r'\s{2,}', ' ', clean)
    clean_lower = clean.lower()

    if "private video" in clean_lower or "this video is private" in clean_lower:
        return ErrorDetail(
            code="PRIVATE_VIDEO",
            message="This video is marked private by the owner.",
            hint="Select your logged-in browser from the Cookies selector or upload a cookies file."
        )
    if "age-restricted" in clean_lower or "confirm your age" in clean_lower or "sign in to view" in clean_lower:
        return ErrorDetail(
            code="AGE_RESTRICTED",
            message="This video is age-restricted and requires account verification.",
            hint="Select your logged-in browser (Chrome or Edge) from the Cookies dropdown to authenticate locally."
        )
    if "not a bot" in clean_lower or "bot verification" in clean_lower or "sign in to confirm" in clean_lower or "confirm you" in clean_lower:
        return ErrorDetail(
            code="BOT_CHECK",
            message="YouTube requested bot verification for this video.",
            hint="Select your browser (Edge or Chrome) from the 'Cookies / Auth' dropdown to authenticate directly on your PC."
        )
    if "available in your country" in clean_lower or "not available in your country" in clean_lower or "geo-restricted" in clean_lower or "blocked it in your country" in clean_lower:
        return ErrorDetail(
            code="GEO_BLOCKED",
            message="This video is not available in your geographical region.",
            hint="Use a VPN or proxy in an authorized region."
        )
    if "members-only" in clean_lower or "members only" in clean_lower or "join this channel" in clean_lower:
        return ErrorDetail(
            code="MEMBERS_ONLY",
            message="This video is restricted to channel members only.",
            hint="Authenticate with a local browser session subscribed to this channel."
        )
    if "http error 429" in clean_lower or "too many requests" in clean_lower or "rate-limit" in clean_lower:
        return ErrorDetail(
            code="RATE_LIMITED",
            message="Too many requests sent to the media host.",
            hint="Wait a few moments before trying again or authenticate with cookies."
        )
    if "is a live stream" in clean_lower or "live event will begin" in clean_lower or "premieres in" in clean_lower or "live event has ended" in clean_lower:
        return ErrorDetail(
            code="LIVE_STREAM",
            message="This media is a live stream or upcoming premiere and cannot be processed.",
            hint="Wait until the live broadcast concludes and the VOD is published."
        )
    if "ffmpeg is not installed" in clean_lower or "ffprobe not found" in clean_lower or "ffmpeg not found" in clean_lower or "avprobe not found" in clean_lower or ("ffprobe" in clean_lower and "not found" in clean_lower) or ("ffmpeg" in clean_lower and "not found" in clean_lower):
        return ErrorDetail(
            code="FFMPEG_MISSING",
            message="FFmpeg binary was not found or failed execution.",
            hint="Install FFmpeg into PATH or select lower quality (720p/480p) pre-muxed stream."
        )
    if "unable to extract" in clean_lower or "http error 403" in clean_lower or "signature extraction failed" in clean_lower or "n challenge solving failed" in clean_lower:
        return ErrorDetail(
            code="ENGINE_OUTDATED",
            message="Site layout changed or stream token extraction failed.",
            hint="Update the download engine using POST /api/engine/update."
        )
    if "connection timed out" in clean_lower or "timed out" in clean_lower or "timeout" in clean_lower or "transporterror" in clean_lower or "connection refused" in clean_lower:
        return ErrorDetail(
            code="CONNECTION_TIMEOUT",
            message="Connection to media host timed out or was refused.",
            hint="If this platform (e.g. TikTok) is restricted in your area, you may need a VPN."
        )

    return ErrorDetail(
        code="UNKNOWN",
        message=clean or "An unexpected extraction error occurred.",
        hint="Check the URL and your local network connection."
    )

def clean_error_message(err_msg: str) -> str:
    """Strips terminal ANSI color codes, URLs, and formats readable errors."""
    s = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(err_msg)).strip()
    s = re.sub(r'https?://\S+', '', s).strip()
    return re.sub(r'\s{2,}', ' ', s)

def get_base_ydl_opts(
    platform: str, 
    cookie_browser: Optional[str] = None,
    cookie_file: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Builds baseline configuration for yt-dlp, configuring User-Agent, cookies,
    and client extractors (e.g. Android/iOS clients for YouTube to bypass bot verification).
    """
    from app.config import COOKIES_FILE
    opts: Dict[str, Any] = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    # YouTube: Use mobile and TV client extraction to bypass web-only PoToken bot verification
    if platform == "youtube":
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android', 'ios', 'tv_embedded', 'web'],
                'player_skip': ['configs', 'webpage']
            }
        }

    # 1. Determine active cookies (temp task file > user-data cookies.txt > browser)
    active_cookie = cookie_file if cookie_file and cookie_file.exists() else (COOKIES_FILE if COOKIES_FILE.exists() else None)

    if active_cookie:
        opts['cookiefile'] = str(active_cookie)
        logger.info(f"Loaded cookies from: {active_cookie}")
    elif cookie_browser and str(cookie_browser).lower() not in ("none", ""):
        browser_val = getattr(cookie_browser, "value", str(cookie_browser)).lower()
        if browser_val != "none":
            opts['cookiesfrombrowser'] = (browser_val, None, None, None)
            logger.info(f"Using cookies from browser: {browser_val}")

    return opts

def extract_media_info(
    url: str, 
    cookie_browser: Optional[str] = None,
    auto_probe_browsers: bool = True,
    cookie_file: Optional[Path] = None
) -> MediaInfoResponse:
    """
    Extracts metadata from YouTube, Instagram, TikTok, Twitter, Bilibili, and other platforms without downloading.
    Includes automated local PC browser fallback for YouTube bot challenge.
    """
    platform = detect_platform(url)
    ydl_opts = get_base_ydl_opts(platform, cookie_browser, cookie_file)
    ydl_opts['extract_flat'] = 'in_playlist'
    ydl_opts['skip_download'] = True

    info = None
    last_error = None

    # Step 1: Attempt extraction with base options (including android/ios player clients)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        last_error = e
        logger.warning(f"Standard extraction notice: {clean_error_message(str(last_error))}")

    # Step 2: Auto-probe local browsers on user's PC for YouTube if blocked
    from app.config import COOKIES_FILE
    if not info and platform == "youtube" and not (cookie_file and cookie_file.exists()) and not COOKIES_FILE.exists():
        for candidate in ['edge', 'chrome', 'firefox', 'brave']:
            try:
                logger.info(f"Attempting bot bypass with local PC {candidate} browser session...")
                retry_opts = dict(ydl_opts)
                retry_opts['cookiesfrombrowser'] = (candidate, None, None, None)
                with yt_dlp.YoutubeDL(retry_opts) as retry_ydl:
                    info = retry_ydl.extract_info(url, download=False)
                    if info:
                        logger.info(f"Successfully extracted metadata using local {candidate} cookies!")
                        break
            except Exception as b_err:
                logger.debug(f"{candidate} cookie attempt failed: {b_err}")
                continue

    if not info:
        detail = map_ytdlp_error(last_error or 'Unknown extraction error')
        raise MediaExtractionError(detail)

    # Check if this is a playlist
    is_playlist = info.get('_type') == 'playlist' or 'entries' in info

    if is_playlist:
        entries = info.get('entries', []) or []
        items: List[VideoItem] = []
        total_playlist_bytes = 0

        for entry in entries:
            if not entry:
                continue
            entry_id = str(entry.get('id', ''))
            video_url = entry.get('url') or entry.get('webpage_url') or url
            duration = entry.get('duration')
            title = entry.get('title') or entry.get('description', '').split('\n')[0][:80] or f"Item {len(items)+1}"
            
            # File size estimation for playlist item
            item_bytes = entry.get('filesize') or entry.get('filesize_approx')
            if not item_bytes and duration:
                item_bytes = int((2000 * 1000 / 8) * float(duration))
            if item_bytes:
                total_playlist_bytes += int(item_bytes)

            items.append(
                VideoItem(
                    id=entry_id or str(len(items)+1),
                    title=title,
                    url=video_url,
                    duration=duration,
                    duration_string=format_seconds(duration),
                    thumbnail=entry.get('thumbnail') or (entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None),
                    channel=entry.get('uploader') or entry.get('channel') or platform.title(),
                    filesize=item_bytes,
                    filesize_formatted=f"~{format_size_bytes(item_bytes)}" if item_bytes else None
                )
            )

        playlist_title = info.get('title') or f"{platform.title()} Playlist"
        thumbnail = info.get('thumbnail') or (items[0].thumbnail if items else None)
        channel = info.get('uploader') or info.get('channel') or platform.title()

        playlist_quality_sizes = {}
        playlist_quality_sizes_formatted = {}
        if total_playlist_bytes > 0:
            playlist_quality_sizes = {
                "best": total_playlist_bytes,
                "1080p": total_playlist_bytes,
                "720p": int(total_playlist_bytes * 0.65),
                "480p": int(total_playlist_bytes * 0.35),
                "audio_mp3": int(total_playlist_bytes * 0.15),
            }
            playlist_quality_sizes_formatted = {
                k: f"~{format_size_bytes(v)}" for k, v in playlist_quality_sizes.items()
            }

        return MediaInfoResponse(
            url=url,
            is_playlist=True,
            title=playlist_title,
            thumbnail=thumbnail,
            channel=channel,
            platform=platform,
            item_count=len(items),
            items=items,
            available_qualities=["best", "1080p", "720p", "480p", "audio_mp3"],
            quality_sizes=playlist_quality_sizes,
            quality_sizes_formatted=playlist_quality_sizes_formatted,
            estimated_filesize=total_playlist_bytes or None,
            filesize_formatted=f"~{format_size_bytes(total_playlist_bytes)}" if total_playlist_bytes else None
        )
    else:
        # Single video
        duration = info.get('duration')
        video_id = str(info.get('id', 'video'))
        raw_title = info.get('title')
        if not raw_title or raw_title.strip() == "":
            desc = info.get('description', '')
            raw_title = desc.split('\n')[0][:80] if desc else f"{platform.title()} Video"
        title = raw_title.strip()

        thumbnail = info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None)
        channel = info.get('uploader') or info.get('channel') or info.get('uploader_id') or platform.title()

        quality_sizes, quality_sizes_formatted = estimate_quality_sizes(info)
        best_size = quality_sizes.get("best") or info.get('filesize') or info.get('filesize_approx')
        best_formatted = quality_sizes_formatted.get("best") or (f"~{format_size_bytes(best_size)}" if best_size else None)

        single_item = VideoItem(
            id=video_id,
            title=title,
            url=info.get('webpage_url') or url,
            duration=duration,
            duration_string=format_seconds(duration),
            thumbnail=thumbnail,
            channel=channel,
            filesize=best_size,
            filesize_formatted=best_formatted
        )

        available_qualities = ["best", "1080p", "720p", "480p", "audio_mp3"]

        return MediaInfoResponse(
            url=url,
            is_playlist=False,
            title=title,
            thumbnail=thumbnail,
            channel=channel,
            platform=platform,
            item_count=1,
            items=[single_item],
            available_qualities=available_qualities,
            quality_sizes=quality_sizes,
            quality_sizes_formatted=quality_sizes_formatted,
            estimated_filesize=best_size,
            filesize_formatted=best_formatted
        )

import os
import shutil

def ensure_ffmpeg_in_path(ffmpeg_exe: str) -> None:
    """
    Prepends FFmpeg executable directory to process PATH and clears yt-dlp version caches
    so external downloaders, postprocessors, and subprocesses locate ffmpeg natively.
    """
    try:
        ffmpeg_dir = str(Path(ffmpeg_exe).parent.resolve())
        current_path = os.environ.get("PATH", "")
        path_parts = [p.strip() for p in current_path.split(os.pathsep) if p.strip()]
        if ffmpeg_dir not in path_parts:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
            logger.info(f"Added FFmpeg directory to PATH: {ffmpeg_dir}")

        # Clear yt-dlp version cache if already loaded
        try:
            from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
            FFmpegPostProcessor._version_cache.clear()
            FFmpegPostProcessor._features_cache.clear()
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Failed to update PATH with FFmpeg directory: {e}")

def get_ffmpeg_path() -> Optional[str]:
    """
    Locates FFmpeg executable from system PATH, bundled imageio-ffmpeg, or standard locations.
    Ensures a canonical 'ffmpeg.exe' is available in USER_DATA_DIR and registered in process PATH.
    """
    from app.config import BASE_DIR, BACKEND_DIR, USER_DATA_DIR

    # 1. Canonical ffmpeg.exe in USER_DATA_DIR
    canonical_ffmpeg = USER_DATA_DIR / "ffmpeg.exe"
    if canonical_ffmpeg.is_file():
        ensure_ffmpeg_in_path(str(canonical_ffmpeg))
        return str(canonical_ffmpeg)

    # 2. System PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        ensure_ffmpeg_in_path(sys_ffmpeg)
        return sys_ffmpeg

    discovered: Optional[str] = None

    # 3. Bundled imageio-ffmpeg binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            discovered = exe
        elif not discovered:
            pkg_bin = Path(imageio_ffmpeg.__file__).resolve().parent / "binaries"
            if pkg_bin.exists():
                for cand in pkg_bin.glob("ffmpeg*"):
                    if cand.is_file() and cand.suffix.lower() in (".exe", ""):
                        discovered = str(cand.resolve())
                        break
    except Exception as e:
        logger.debug(f"imageio_ffmpeg binary search: {e}")

    # 5. Standard local or Windows directories
    if not discovered:
        for cand in [
            BASE_DIR / "ffmpeg.exe",
            BACKEND_DIR / "ffmpeg.exe",
            USER_DATA_DIR / "engine" / "bin" / "ffmpeg.exe",
            BASE_DIR / "venv" / "Scripts" / "ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        ]:
            if cand.is_file():
                discovered = str(cand.resolve())
                break

    if discovered:
        try:
            if not canonical_ffmpeg.exists():
                shutil.copy2(discovered, canonical_ffmpeg)
                logger.info(f"Initialized canonical FFmpeg binary at: {canonical_ffmpeg}")
            ensure_ffmpeg_in_path(str(canonical_ffmpeg))
            return str(canonical_ffmpeg)
        except Exception:
            ensure_ffmpeg_in_path(discovered)
            return discovered

    return None

def build_ydl_download_options(
    quality: str,
    output_dir: Path,
    is_playlist: bool,
    playlist_title: Optional[str] = None,
    platform: str = "youtube",
    cookie_browser: Optional[str] = None,
    cookie_file: Optional[Path] = None,
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    postprocessor_hook: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Constructs the yt-dlp download configuration dictionary based on requested quality and platform.
    Ensures exact requested resolution (1080p, 720p, 480p, best) is downloaded without dropping
    to 360p, handles portrait/landscape aspect ratios, and merges into MP4 via FFmpeg.
    """
    ffmpeg_bin = get_ffmpeg_path()
    has_ffmpeg = bool(ffmpeg_bin)

    opts = get_base_ydl_opts(platform, cookie_browser, cookie_file)
    opts['windowsfilenames'] = True  # Ensures OS-safe naming while keeping original title
    opts['outtmpl'] = {}

    if ffmpeg_bin:
        opts['ffmpeg_location'] = ffmpeg_bin
        logger.info(f"Using FFmpeg at: {ffmpeg_bin}")
    else:
        logger.warning("FFmpeg not detected. Stream merging will fall back to pre-muxed single-container formats.")

    if progress_hook:
        opts['progress_hooks'] = [progress_hook]

    if postprocessor_hook:
        opts['postprocessor_hooks'] = [postprocessor_hook]

    # Task 8: Set output templates with .150B truncation and reserved name safety
    if is_playlist and playlist_title:
        clean_playlist_name = sanitize_filename(playlist_title)
        target_folder = output_dir / clean_playlist_name
        target_folder.mkdir(parents=True, exist_ok=True)
        # Template: /downloads/<PlaylistName>/%(playlist_index)03d - %(title).150B [%(id)s].%(ext)s
        opts['outtmpl']['default'] = str(target_folder / '%(playlist_index)03d - %(title).150B [%(id)s].%(ext)s')
    else:
        # Template: /downloads/%(title).150B [%(id)s].%(ext)s
        opts['outtmpl']['default'] = str(output_dir / '%(title).150B [%(id)s].%(ext)s')

    # Format selection according to requested quality and FFmpeg availability
    if quality == "audio_mp3":
        opts['format'] = 'bestaudio/best'
        if has_ffmpeg:
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
    elif has_ffmpeg:
        # Full separate video + audio stream extraction and container merging into MP4
        opts['merge_output_format'] = 'mp4'

        if quality == "1080p":
            opts['format'] = (
                'bestvideo[height<=?1080]+bestaudio/'
                'bestvideo[width<=?1080]+bestaudio/'
                'best[height<=?1080]/best[width<=?1080]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:1080', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        elif quality == "720p":
            opts['format'] = (
                'bestvideo[height<=?720]+bestaudio/'
                'bestvideo[width<=?720]+bestaudio/'
                'best[height<=?720]/best[width<=?720]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:720', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        elif quality == "480p":
            opts['format'] = (
                'bestvideo[height<=?480]+bestaudio/'
                'bestvideo[width<=?480]+bestaudio/'
                'best[height<=?480]/best[width<=?480]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:480', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        else:  # "best"
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['format_sort'] = ['res', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
    else:
        # Fallback when FFmpeg is not installed: single container pre-muxed progressive streams only
        logger.warning(f"FFmpeg not available on system. Falling back to pre-muxed stream for quality={quality}")
        if quality == "1080p":
            opts['format'] = 'best[height<=?1080]/best'
        elif quality == "720p":
            opts['format'] = 'best[height<=?720]/best'
        elif quality == "480p":
            opts['format'] = 'best[height<=?480]/best'
        else:  # "best"
            opts['format'] = 'best'

    return opts
