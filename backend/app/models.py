from enum import Enum
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

class CookieBrowserEnum(str, Enum):
    none = "none"
    firefox = "firefox"
    chrome = "chrome"
    edge = "edge"
    brave = "brave"

def validate_http_url(v: str) -> str:
    if not v or not isinstance(v, str):
        raise ValueError("URL cannot be empty.")
    v = v.strip()
    if len(v) > 2048:
        raise ValueError("URL exceeds maximum length of 2048 characters.")
    parsed = urlparse(v)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must have an http or https scheme.")
    return v

class InfoRequest(BaseModel):
    url: str = Field(..., max_length=2048, description="Media URL (http/https only)")
    cookie_browser: Optional[CookieBrowserEnum] = Field(default=CookieBrowserEnum.none)

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return validate_http_url(v)

class VideoItem(BaseModel):
    id: str
    title: str
    url: str
    duration: Optional[Union[int, float]] = None
    duration_string: Optional[str] = None
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    filesize: Optional[int] = None
    filesize_formatted: Optional[str] = None

class MediaInfoResponse(BaseModel):
    url: str
    is_playlist: bool
    title: str
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    platform: str = "universal"
    item_count: int = 1
    items: List[VideoItem] = []
    available_qualities: List[str] = ["best", "1080p", "720p", "480p", "audio_mp3"]
    quality_sizes: Dict[str, Optional[int]] = Field(default_factory=dict)
    quality_sizes_formatted: Dict[str, str] = Field(default_factory=dict)
    estimated_filesize: Optional[int] = None
    filesize_formatted: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str = Field(..., max_length=2048, description="Media URL (http/https only)")
    is_playlist: bool = False
    selected_video_ids: Optional[List[str]] = None
    quality: str = Field(default="best", max_length=50)  # "best", "1080p", "720p", "480p", "audio_mp3"
    save_to_local_folder: bool = True
    cookie_browser: Optional[CookieBrowserEnum] = Field(default=CookieBrowserEnum.none)
    auto_probe_browsers: bool = False
    download_dir: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return validate_http_url(v)

class SetDownloadDirRequest(BaseModel):
    download_dir: str = Field(..., min_length=1, max_length=1000)

class ErrorDetail(BaseModel):
    code: str
    message: str
    hint: str
    source: str = "platform"  # "platform" (YouTube/host), "network" (internet), "system" (computer/ffmpeg), "app" (OmniDownloader)

class DownloadTaskStatus(BaseModel):
    task_id: str
    status: str = "queued"  # queued, fetching, downloading, merging, completed, failed, cancelled
    progress: float = 0.0
    downloaded_bytes: Optional[float] = None
    total_bytes: Optional[float] = None
    speed_str: Optional[str] = None
    eta_str: Optional[str] = None
    current_item: Optional[str] = None
    total_items: int = 1
    completed_items: int = 0
    output_files: List[str] = []
    error_message: Optional[str] = None
    error_detail: Optional[ErrorDetail] = None

