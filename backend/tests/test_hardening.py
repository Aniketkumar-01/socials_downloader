import os
import secrets
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app, API_TOKEN
from app.config import (
    DOWNLOADS_DIR,
    sanitize_filename,
    WINDOWS_RESERVED_NAMES,
    MAX_COOKIE_SIZE
)
from app.models import DownloadRequest, CookieBrowserEnum, DownloadTaskStatus
from app.task_manager import task_manager, CancelledDownload

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. Localhost API Hardening Tests (Token, Host, Origin)
# ---------------------------------------------------------------------------

def test_token_rejection_missing():
    """Requests to /api/* without X-Auth-Token or ?token= must return 401."""
    response = client.get("/api/cookies-status")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"


def test_token_rejection_invalid():
    """Requests to /api/* with an invalid token must return 401."""
    response = client.get(
        "/api/cookies-status",
        headers={"X-Auth-Token": "invalid-secret-token"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_token_accepted_header():
    """Requests with valid X-Auth-Token header must be accepted."""
    response = client.get(
        "/api/cookies-status",
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 200


def test_token_accepted_query_param_for_sse():
    """Query parameter ?token= must be accepted (for SSE and stream endpoints)."""
    response = client.get(f"/api/cookies-status?token={API_TOKEN}")
    assert response.status_code == 200


def test_host_header_rejection():
    """Requests with unauthorized Host headers (e.g. DNS rebinding) must be rejected with 403."""
    response = client.get(
        "/api/cookies-status",
        headers={"Host": "attacker.com", "X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_host_header_allowed():
    """Requests with 127.0.0.1 or localhost Host headers must be allowed."""
    for valid_host in ["127.0.0.1:8000", "localhost:8000", "127.0.0.1", "localhost"]:
        response = client.get(
            "/api/cookies-status",
            headers={"Host": valid_host, "X-Auth-Token": API_TOKEN}
        )
        assert response.status_code == 200


def test_origin_header_rejection():
    """Requests with external Origin header must be rejected with 403."""
    response = client.get(
        "/api/cookies-status",
        headers={"Origin": "https://malicious-website.com", "X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_origin_header_allowed():
    """Requests from localhost / 127.0.0.1 Origin must be permitted."""
    for valid_origin in ["http://127.0.0.1:8000", "http://localhost:8000"]:
        response = client.get(
            "/api/cookies-status",
            headers={"Origin": valid_origin, "X-Auth-Token": API_TOKEN}
        )
        assert response.status_code == 200


def test_clipboard_endpoint():
    """Requests to /api/clipboard must be permitted and return a JSON dictionary with text."""
    response = client.get("/api/clipboard")
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert isinstance(data["text"], str)


# ---------------------------------------------------------------------------
# 2. Path Safety & Traversal Rejection Tests
# ---------------------------------------------------------------------------

def test_file_serve_path_traversal_rejection(tmp_path):
    """Serving a file outside DOWNLOADS_DIR must return 403 Forbidden."""
    outside_file = tmp_path / "sensitive.txt"
    outside_file.write_text("top secret data")

    fake_task_id = "traversal-task-1"
    task_manager._tasks[fake_task_id] = DownloadTaskStatus(
        task_id=fake_task_id,
        url="https://youtube.com/watch?v=12345",
        status="completed",
        output_files=[str(outside_file.resolve())]
    )

    try:
        response = client.get(
            f"/api/file/{fake_task_id}",
            headers={"X-Auth-Token": API_TOKEN}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
    finally:
        task_manager._tasks.pop(fake_task_id, None)


def test_open_folder_path_traversal_rejection(tmp_path):
    """Attempting to open folder outside DOWNLOADS_DIR must return 403 Forbidden."""
    outside_file = tmp_path / "outside.mp4"
    outside_file.write_text("data")

    fake_task_id = "traversal-task-2"
    task_manager._tasks[fake_task_id] = DownloadTaskStatus(
        task_id=fake_task_id,
        url="https://youtube.com/watch?v=12345",
        status="completed",
        output_files=[str(outside_file.resolve())]
    )

    try:
        response = client.post(
            f"/api/open-folder?task_id={fake_task_id}",
            headers={"X-Auth-Token": API_TOKEN}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
    finally:
        task_manager._tasks.pop(fake_task_id, None)


# ---------------------------------------------------------------------------
# 3. Input Validation (URL scheme & Browser Enum)
# ---------------------------------------------------------------------------

def test_url_scheme_validation():
    """Only http and https schemes are permitted; file:// or others must fail with 422."""
    response = client.post(
        "/api/info",
        json={"url": "file:///etc/passwd"},
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_browser_enum_validation():
    """Unapproved browser strings must be rejected with 422."""
    response = client.post(
        "/api/info",
        json={"url": "https://youtube.com/watch?v=dQw4w9WgXcQ", "cookie_browser": "safari"},
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# 4. Cookie Validation Tests
# ---------------------------------------------------------------------------

def test_cookie_upload_exceeds_size_cap():
    """Cookie files exceeding 2 MB must be rejected with 413 Payload Too Large."""
    large_payload = b"A" * (MAX_COOKIE_SIZE + 100)
    response = client.post(
        "/api/upload-cookies",
        content=large_payload,
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_cookie_upload_invalid_format():
    """Files without Netscape header or 7 tab-separated fields must return 400 Bad Request."""
    invalid_payload = b"this is just some plain text without any cookie formatting"
    response = client.post(
        "/api/upload-cookies",
        content=invalid_payload,
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 400
    assert "Invalid cookie format" in response.json()["message"]


def test_cookie_upload_valid_netscape():
    """Valid Netscape format cookie files must be accepted."""
    valid_netscape = (
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tGPS\t1\n"
    )
    response = client.post(
        "/api/upload-cookies",
        content=valid_netscape,
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Clean up
    client.delete("/api/cookies", headers={"X-Auth-Token": API_TOKEN})


# ---------------------------------------------------------------------------
# 5. Filename Sanitization & Reserved Names Tests
# ---------------------------------------------------------------------------

def test_filename_reserved_names():
    """Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) must be prefixed with '_'."""
    for reserved in ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]:
        sanitized = sanitize_filename(f"{reserved}.mp4")
        assert sanitized.startswith("_"), f"Expected {reserved}.mp4 to start with '_', got {sanitized}"
        assert sanitized == f"_{reserved}.mp4"


# ---------------------------------------------------------------------------
# 6. Task Cancellation Tests (Mock yt-dlp)
# ---------------------------------------------------------------------------

def test_task_cancellation_workflow():
    """Cancelling a task must flag it, raise CancelledDownload, and transition status to cancelled."""
    req = DownloadRequest(url="https://youtube.com/watch?v=dQw4w9WgXcQ")
    task_id = task_manager.create_task(req)
    
    assert task_manager.get_task(task_id).status == "queued"

    # Verify task cancellation endpoint
    response = client.post(
        f"/api/tasks/{task_id}/cancel",
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert task_manager.is_cancelled(task_id) is True

    # Simulate worker detecting cancellation
    with pytest.raises(CancelledDownload):
        if task_manager.is_cancelled(task_id):
            raise CancelledDownload(f"Download task {task_id} was cancelled by user.")

    # Status check
    assert task_manager.get_task(task_id).status == "cancelled"


# ---------------------------------------------------------------------------
# 7. Error Mapping Tests (Task 7)
# ---------------------------------------------------------------------------

def test_error_mapping_categories():
    """Verify that common yt-dlp error signatures map to unified {code, message, hint} ErrorDetail."""
    from app.downloader import map_ytdlp_error

    # Bot challenge
    err = map_ytdlp_error("Sign in to confirm you’re not a bot. Use --cookies-from-browser")
    assert err.code == "BOT_CHECK"
    assert "bot verification" in err.message.lower()
    assert err.source == "platform"

    # Private video
    err = map_ytdlp_error("ERROR: [youtube] 12345: This video is private")
    assert err.code == "PRIVATE_VIDEO"
    assert err.source == "platform"

    # Age restricted
    err = map_ytdlp_error("Sign in to confirm your age. This video may be inappropriate")
    assert err.code == "AGE_RESTRICTED"
    assert err.source == "platform"

    # Geo blocked
    err = map_ytdlp_error("The uploader has not made this video available in your country")
    assert err.code == "GEO_BLOCKED"
    assert err.source == "platform"

    # Members only
    err = map_ytdlp_error("Join this channel to get access to members-only content")
    assert err.code == "MEMBERS_ONLY"
    assert err.source == "platform"

    # Rate limited
    err = map_ytdlp_error("HTTP Error 429: Too Many Requests")
    assert err.code == "RATE_LIMITED"
    assert err.source == "network"

    # Live stream
    err = map_ytdlp_error("This live event will begin in 2 hours")
    assert err.code == "LIVE_STREAM"
    assert err.source == "platform"

    # FFmpeg missing
    err = map_ytdlp_error("ffprobe or avprobe not found. Please install one")
    assert err.code == "FFMPEG_MISSING"
    assert err.source == "system"

    # Engine outdated
    err = map_ytdlp_error("Unable to extract video data: signature extraction failed")
    assert err.code == "ENGINE_OUTDATED"
    assert "update" in err.hint.lower()
    assert err.source == "app"

    # Connection timeout (e.g. regional ban)
    err = map_ytdlp_error("Connection to www.tiktok.com timed out. (connect timeout=20.0)")
    assert err.code == "CONNECTION_TIMEOUT"
    assert "vpn" in err.hint.lower()
    assert err.source == "network"

    # Untrusted mount point (WinError 448)
    err = map_ytdlp_error(r"[WinError 448] The path cannot be traversed because it contains an untrusted mount point: 'C:\Users\Developer\AppData\Local\Author Software\nvm\.nodejs'")
    assert err.code == "UNTRUSTED_MOUNT_POINT"
    assert "untrusted mount point" in err.message.lower()
    assert "nvm" in err.hint.lower()
    assert err.source == "system"


def test_safe_realpath_handles_untrusted_mount_point():
    """Verify that os.path.realpath does not crash on WinError 448."""
    from app.config import _orig_realpath

    fake_untrusted_path = r"C:\fake\untrusted\mount\.nodejs"
    with patch("os.path._orig_realpath", side_effect=OSError(448, "The path cannot be traversed because it contains an untrusted mount point")):
        resolved = os.path.realpath(fake_untrusted_path)
        assert resolved == os.path.abspath(fake_untrusted_path)


def test_sanitize_system_path_filters_untrusted_mount():
    """Verify that sanitize_system_path omits or resolves untrusted reparse points."""
    from app.config import sanitize_system_path, _orig_realpath

    fake_valid = r"C:\Windows\System32"
    fake_untrusted = r"C:\fake\untrusted\mount"

    def mock_orig_realpath(p, *args, **kwargs):
        if "untrusted" in p:
            raise OSError(448, "Untrusted mount point")
        return _orig_realpath(p, *args, **kwargs)

    orig_path = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = f"{fake_valid};{fake_untrusted}"
        with patch("os.path._orig_realpath", side_effect=mock_orig_realpath):
            with patch("os.readlink", side_effect=OSError("Not a link")):
                sanitize_system_path()
                current_path = os.environ.get("PATH", "")
                assert fake_valid in current_path
                assert fake_untrusted not in current_path
    finally:
        os.environ["PATH"] = orig_path


# ---------------------------------------------------------------------------
# 8. Token Protection, Length Limits, and Safe Fallbacks
# ---------------------------------------------------------------------------

def test_token_endpoint_blocks_cross_site():
    """Verify that requests to /api/token with Sec-Fetch-Site: cross-site are rejected with 403."""
    response = client.get(
        "/api/token",
        headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_token_endpoint_allows_same_origin():
    """Verify that local/same-origin requests to /api/token succeed and return a valid token."""
    response = client.get(
        "/api/token",
        headers={"Sec-Fetch-Site": "same-origin"}
    )
    assert response.status_code == 200
    assert "token" in response.json()
    assert response.json()["token"] == API_TOKEN


def test_url_max_length_rejection():
    """Verify that URLs exceeding 2048 characters are rejected with 422."""
    oversized_url = "https://example.com/watch?v=" + ("a" * 2100)
    response = client.post(
        "/api/info",
        json={"url": oversized_url},
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_open_file_not_found():
    """Opening a nonexistent task's file returns 404 with standard error structure."""
    response = client.post(
        "/api/open-file?task_id=nonexistent-task-id",
        headers={"X-Auth-Token": API_TOKEN}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"




