from app.config import sanitize_filename
from app.models import MediaInfoResponse, VideoItem, DownloadRequest
from app.downloader import format_seconds

def test_sanitize_filename():
    # Test illegal Windows characters removal
    raw_title = 'My Video: Episode 1 <HD> "Must Watch" / test \\ | ? *'
    sanitized = sanitize_filename(raw_title)
    
    for char in '<>:"/\\|?*':
        assert char not in sanitized
        
    assert sanitized == 'My Video_ Episode 1 _HD_ _Must Watch_ _ test _ _ _ _'

def test_sanitize_filename_empty():
    assert sanitize_filename("") == "untitled_video"
    assert sanitize_filename(None) == "untitled_video"
    assert sanitize_filename("   ...  ") == "untitled_video" or sanitize_filename("   ...  ") == "video"

def test_format_seconds():
    assert format_seconds(None) is None
    assert format_seconds(45) == "00:45"
    assert format_seconds(125) == "02:05"
    assert format_seconds(3665) == "01:01:05"
    assert format_seconds(134.65) == "02:15"

def test_models():
    item = VideoItem(
        id="abc12345",
        title="Test Video Title",
        url="https://youtube.com/watch?v=abc12345",
        duration=134.65,
        duration_string="02:15",
        channel="Test Channel"
    )
    assert item.title == "Test Video Title"
    assert item.duration == 134.65
    
    resp = MediaInfoResponse(
        url="https://youtube.com/watch?v=abc12345",
        is_playlist=False,
        title="Test Video Title",
        items=[item]
    )
    assert resp.item_count == 1
    assert resp.items[0].id == "abc12345"

def test_download_request_defaults():
    req = DownloadRequest(url="https://youtube.com/watch?v=abc12345")
    assert req.quality == "best"
    assert req.is_playlist is False
    assert req.save_to_local_folder is True

def test_detect_platform():
    from app.downloader import detect_platform
    assert detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert detect_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    assert detect_platform("https://www.instagram.com/reel/C3abcdef123/") == "instagram"
    assert detect_platform("https://twitter.com/user/status/123456789") == "twitter"
    assert detect_platform("https://x.com/user/status/123456789") == "twitter"
    assert detect_platform("https://www.tiktok.com/@user/video/123456789") == "tiktok"
    assert detect_platform("https://www.bilibili.com/video/BV1xx411c7mD") == "bilibili"
    assert detect_platform("https://example.com/video.mp4") == "universal"
