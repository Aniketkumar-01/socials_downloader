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
    parsed = urlparse(v)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must have an http or https scheme.")
    return v

class InfoRequest(BaseModel):
    url: str = Field(..., description="Media URL (http/https only)")
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

class DownloadRequest(BaseModel):
    url: str
    is_playlist: bool = False
    selected_video_ids: Optional[List[str]] = None
    quality: str = "best"  # "best", "1080p", "720p", "480p", "audio_mp3"
    save_to_local_folder: bool = True
    cookie_browser: Optional[CookieBrowserEnum] = Field(default=CookieBrowserEnum.none)
    auto_probe_browsers: bool = False

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return validate_http_url(v)

class ErrorDetail(BaseModel):
    code: str
    message: str
    hint: str

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

