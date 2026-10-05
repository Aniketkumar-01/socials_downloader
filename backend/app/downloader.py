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

def get_format_resolution(f: Dict[str, Any]) -> int:
    """Returns effective resolution dimension (shorter side for orientation neutrality)."""
    h = f.get('height')
    w = f.get('width')
    if h and w and h > 0 and w > 0:
        return min(int(h), int(w))
    return int(h) if (h and h > 0) else (int(w) if (w and w > 0) else 0)

def estimate_quality_sizes(info: Dict[str, Any]) -> tuple[Dict[str, Optional[int]], Dict[str, str], List[str]]:
    """Calculates approximate file sizes and dynamically determines available quality options."""
    formats = info.get('formats') or []
    duration = info.get('duration')

    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    best_audio_size = 0
    if audio_formats:
        audio_formats.sort(key=lambda f: f.get('abr') or f.get('tbr') or 0, reverse=True)
        best_audio_size = estimate_format_bytes(audio_formats[0], duration) or 0
    elif duration and duration > 0:
        best_audio_size = int((128 * 1000 / 8) * float(duration))

    video_formats = [f for f in formats if f.get('vcodec') != 'none']

    def get_best_video_size(target_dim: Optional[int]) -> Optional[int]:
        if not video_formats:
            return None

        if target_dim is None:
            matching = list(video_formats)
        else:
            matching = [f for f in video_formats if get_format_resolution(f) <= target_dim]
            if not matching:
                # If slightly above (e.g. 724p for 720p target)
                matching = [f for f in video_formats if get_format_resolution(f) <= target_dim * 1.05]
            if not matching:
                return None

        def format_score(f: Dict[str, Any]) -> tuple:
            res = get_format_resolution(f)
            vc = (f.get('vcodec') or '').lower()
            # Prioritize efficient modern streams that yt-dlp actually downloads (AV1 > VP9 > H.264)
            codec_rank = 3 if 'av01' in vc else (2 if 'vp9' in vc or 'vp09' in vc else (1 if 'avc' in vc or 'h264' in vc else 0))
            size = f.get('filesize') or f.get('filesize_approx') or 0
            bitrate = f.get('tbr') or f.get('vbr') or 0
            # For 4K, avoid inflated peak bitrate containers, target realistic VBR ~6000kbps
            bitrate_metric = -abs(bitrate - 6000) if res >= 2000 and bitrate > 0 else bitrate
            return (res, codec_rank, size > 0, bitrate_metric)

        matching.sort(key=format_score, reverse=True)
        chosen = matching[0]
        v_size = estimate_format_bytes(chosen, duration)
        if not v_size and duration and duration > 0:
            target_res = target_dim or get_format_resolution(chosen) or 720
            # Realistic average VBR bitrates (in kbps): 4K ~6000k, 2K ~3800k, 1080p ~2500k, 720p ~1400k
            typical_kbps = {2160: 6000, 1440: 3800, 1080: 2500, 720: 1400, 480: 750, 360: 450}.get(target_res, 1200)
            v_size = int((typical_kbps * 1000 / 8) * float(duration))

        if not v_size:
            return None

        if chosen.get('acodec') == 'none' and best_audio_size:
            return v_size + best_audio_size
        return v_size

    # Dynamically determine available video qualities from actual formats
    resolutions = [get_format_resolution(f) for f in video_formats if get_format_resolution(f) > 0]
    max_res = max(resolutions) if resolutions else 0

    available_qualities: List[str] = ["best"]
    if any(r >= 2000 for r in resolutions):
        available_qualities.append("2160p")
    if any(1400 <= r < 2000 for r in resolutions):
        available_qualities.append("1440p")
    if any(1000 <= r < 1400 for r in resolutions):
        available_qualities.append("1080p")
    if any(700 <= r < 1000 for r in resolutions):
        available_qualities.append("720p")
    if any(450 <= r < 700 for r in resolutions):
        available_qualities.append("480p")
    if any(300 <= r < 450 for r in resolutions) and (max_res <= 480 or not any(450 <= r < 700 for r in resolutions)):
        available_qualities.append("360p")

    # If formats exist but didn't match standard bins, add closest tier to max_res
    if len(available_qualities) == 1 and max_res > 0:
        if max_res >= 1000:
            available_qualities.append("1080p")
        elif max_res >= 700:
            available_qualities.append("720p")
        elif max_res >= 450:
            available_qualities.append("480p")
        else:
            available_qualities.append("360p")

    available_qualities.append("audio_mp3")

    tier_targets = {
        "2160p": 2160,
        "1440p": 1440,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
        "360p": 360,
    }

    quality_sizes: Dict[str, Optional[int]] = {}
    quality_sizes_formatted: Dict[str, str] = {}

    # Calculate best video size
    best_v_size = get_best_video_size(None)
    if best_v_size and best_v_size > 0:
        quality_sizes["best"] = best_v_size
        quality_sizes_formatted["best"] = f"~{format_size_bytes(best_v_size)}"
    else:
        g_size = info.get('filesize') or info.get('filesize_approx')
        if g_size:
            quality_sizes["best"] = int(g_size)
            quality_sizes_formatted["best"] = f"~{format_size_bytes(g_size)}"

    # Calculate sizes for each available specific tier
    for q_key in available_qualities:
        if q_key in ("best", "audio_mp3"):
            continue
        max_dim = tier_targets.get(q_key)
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

    return quality_sizes, quality_sizes_formatted, available_qualities

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
    Standardized mapping of yt-dlp exceptions to layman-friendly {code, message, hint, source}.
    Clearly identifies whether the issue originates from the Platform (YouTube/host),
    Network (internet connection), System (local computer setup), or Application.
    """
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(err)).strip()
    clean = re.sub(r'https?://\S+', '', clean).strip()
    clean = re.sub(r'\s{2,}', ' ', clean)
    clean_lower = clean.lower()

    if "private video" in clean_lower or "this video is private" in clean_lower:
        return ErrorDetail(
            code="PRIVATE_VIDEO",
            message="This video is marked private by the owner on YouTube.",
            hint="Only the video creator and invited users can access private videos. If you have permission, select your signed-in browser from the Cookies dropdown.",
            source="platform"
        )
    if "age-restricted" in clean_lower or "confirm your age" in clean_lower or "sign in to view" in clean_lower:
        return ErrorDetail(
            code="AGE_RESTRICTED",
            message="This video is age-restricted on YouTube and requires an account over 18.",
            hint="Select your logged-in browser (Chrome or Edge) from the 'Cookies / Auth' dropdown to authenticate locally.",
            source="platform"
        )
    if "not a bot" in clean_lower or "bot verification" in clean_lower or "sign in to confirm" in clean_lower or "confirm you" in clean_lower:
        return ErrorDetail(
            code="BOT_CHECK",
            message="YouTube requested bot verification to confirm you are human.",
            hint="This is a standard YouTube security challenge, not an app error. Select your browser (Edge or Chrome) from the 'Cookies / Auth' dropdown to authenticate directly on your PC.",
            source="platform"
        )
    if "available in your country" in clean_lower or "not available in your country" in clean_lower or "geo-restricted" in clean_lower or "blocked it in your country" in clean_lower:
        return ErrorDetail(
            code="GEO_BLOCKED",
            message="This video is not available in your geographical country or region.",
            hint="The content owner restricted this video geographically. Connect through a VPN to an authorized country and try again.",
            source="platform"
        )
    if "members-only" in clean_lower or "members only" in clean_lower or "join this channel" in clean_lower:
        return ErrorDetail(
            code="MEMBERS_ONLY",
            message="This video is restricted to paid channel members only.",
            hint="Only channel members can access this video. If you are a member, select your signed-in browser from the Cookies dropdown.",
            source="platform"
        )
    if "http error 429" in clean_lower or "too many requests" in clean_lower or "rate-limit" in clean_lower:
        return ErrorDetail(
            code="RATE_LIMITED",
            message="The video platform is temporarily rate-limiting requests.",
            hint="Too many requests were sent in a short window. Wait 2–3 minutes before trying again or authenticate with cookies.",
            source="network"
        )
    if "is a live stream" in clean_lower or "live event will begin" in clean_lower or "premieres in" in clean_lower or "live event has ended" in clean_lower:
        return ErrorDetail(
            code="LIVE_STREAM",
            message="This media is currently streaming live or is an upcoming premiere.",
            hint="Live broadcasts cannot be downloaded while streaming. Wait until the live event concludes and the full recording is published.",
            source="platform"
        )
    if "ffmpeg is not installed" in clean_lower or "ffprobe not found" in clean_lower or "ffmpeg not found" in clean_lower or "avprobe not found" in clean_lower or ("ffprobe" in clean_lower and "not found" in clean_lower) or ("ffmpeg" in clean_lower and "not found" in clean_lower):
        return ErrorDetail(
            code="FFMPEG_MISSING",
            message="FFmpeg media processing software was not found on your computer.",
            hint="Click the '1-Click Install FFmpeg' banner at the top of the app to install it automatically.",
            source="system"
        )
    if "unable to extract" in clean_lower or "http error 403" in clean_lower or "signature extraction failed" in clean_lower or "n challenge solving failed" in clean_lower:
        return ErrorDetail(
            code="ENGINE_OUTDATED",
            message="The video platform recently updated its website layout or stream signature.",
            hint="The download engine needs to be refreshed. Update the download engine using POST /api/engine/update.",
            source="app"
        )
    if "connection timed out" in clean_lower or "timed out" in clean_lower or "timeout" in clean_lower or "transporterror" in clean_lower or "connection refused" in clean_lower:
        return ErrorDetail(
            code="CONNECTION_TIMEOUT",
            message="Connection to the media host timed out or was refused.",
            hint="Please check your internet connection. If this platform (e.g. TikTok) is restricted in your region, you may need a VPN.",
            source="network"
        )
    if "untrusted mount point" in clean_lower or "winerror 448" in clean_lower:
        return ErrorDetail(
            code="UNTRUSTED_MOUNT_POINT",
            message="Windows security policy blocked path traversal due to an untrusted mount point in system PATH.",
            hint="Reset NVM with 'nvm use <version>' as Administrator or check for broken junction links in your system PATH.",
            source="system"
        )

    return ErrorDetail(
        code="UNKNOWN",
        message=clean or "Could not fetch media information from this link.",
        hint="Please verify that the link works in your browser and check your internet connection.",
        source="platform"
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
    Builds baseline configuration for yt-dlp, configuring User-Agent and cookies
    without restricting YouTube format availability or stripping webpage configs.
    """
    from app.config import COOKIES_FILE, BASE_DIR
    opts: Dict[str, Any] = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    # 1. Determine active cookies (temp task file > user-data cookies.txt > workspace cookies.txt > browser)
    active_cookie = None
    if cookie_file and Path(cookie_file).exists():
        active_cookie = Path(cookie_file)
    elif COOKIES_FILE.exists():
        active_cookie = COOKIES_FILE
    elif (BASE_DIR / "cookies.txt").exists():
        active_cookie = BASE_DIR / "cookies.txt"

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
    Includes automated local PC browser fallback and emergency fallback for YouTube challenges.
    """
    platform = detect_platform(url)
    ydl_opts = get_base_ydl_opts(platform, cookie_browser, cookie_file)
    ydl_opts['extract_flat'] = 'in_playlist'
    ydl_opts['skip_download'] = True

    info = None
    last_error = None

    # Step 1: Attempt extraction with base options (full web client formats)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        last_error = e
        logger.warning(f"Standard extraction notice: {clean_error_message(str(last_error))}")

    # Step 2: Auto-probe local browsers on user's PC for YouTube if blocked
    from app.config import COOKIES_FILE, BASE_DIR
    has_cookies = (cookie_file and Path(cookie_file).exists()) or COOKIES_FILE.exists() or (BASE_DIR / "cookies.txt").exists()
    if not info and platform == "youtube" and not has_cookies:
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

    # Step 3: Emergency fallback for YouTube if still blocked and no cookies worked
    if not info and platform == "youtube":
        try:
            logger.info("Attempting emergency fallback client extraction for YouTube...")
            fallback_opts = dict(ydl_opts)
            fallback_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['tv_embedded', 'ios', 'android', 'web']
                }
            }
            with yt_dlp.YoutubeDL(fallback_opts) as fb_ydl:
                info = fb_ydl.extract_info(url, download=False)
                if info:
                    logger.info("Successfully extracted metadata using emergency fallback client!")
        except Exception as fb_err:
            logger.debug(f"Emergency fallback failed: {fb_err}")

    if not info:
        detail = map_ytdlp_error(last_error or 'Unknown extraction error')
        raise MediaExtractionError(detail)

    # Check if this is a playlist
    is_playlist = info.get('_type') == 'playlist' or 'entries' in info

    if is_playlist:
        entries = info.get('entries', []) or []
        items: List[VideoItem] = []
        total_playlist_bytes = 0
        MAX_PLAYLIST_ITEMS = 500

        for entry in entries:
            if len(items) >= MAX_PLAYLIST_ITEMS:
                logger.warning(f"Playlist entry count capped at {MAX_PLAYLIST_ITEMS} items to protect system resources.")
                break
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

        quality_sizes, quality_sizes_formatted, available_qualities = estimate_quality_sizes(info)
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

        if quality in ("2160p", "4k"):
            opts['format'] = (
                'bestvideo[height<=?2160]+bestaudio/'
                'bestvideo[width<=?2160]+bestaudio/'
                'best[height<=?2160]/best[width<=?2160]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:2160', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        elif quality in ("1440p", "2k"):
            opts['format'] = (
                'bestvideo[height<=?1440]+bestaudio/'
                'bestvideo[width<=?1440]+bestaudio/'
                'best[height<=?1440]/best[width<=?1440]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:1440', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        elif quality == "1080p":
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
        elif quality == "360p":
            opts['format'] = (
                'bestvideo[height<=?360]+bestaudio/'
                'bestvideo[width<=?360]+bestaudio/'
                'best[height<=?360]/best[width<=?360]/'
                'bestvideo+bestaudio/best'
            )
            opts['format_sort'] = ['res:360', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
        else:  # "best"
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['format_sort'] = ['res', 'fps', 'vcodec:h264:vp9:av01', 'ext:mp4:m4a']
    else:
        # Fallback when FFmpeg is not installed: single container pre-muxed progressive streams only
        logger.warning(f"FFmpeg not available on system. Falling back to pre-muxed stream for quality={quality}")
        if quality in ("2160p", "4k"):
            opts['format'] = 'best[height<=?2160]/best[width<=?2160]/best'
        elif quality in ("1440p", "2k"):
            opts['format'] = 'best[height<=?1440]/best[width<=?1440]/best'
        elif quality == "1080p":
            opts['format'] = 'best[height<=?1080]/best'
        elif quality == "720p":
            opts['format'] = 'best[height<=?720]/best'
        elif quality == "480p":
            opts['format'] = 'best[height<=?480]/best'
        elif quality == "360p":
            opts['format'] = 'best[height<=?360]/best'
        else:  # "best"
            opts['format'] = 'best'

    return opts
