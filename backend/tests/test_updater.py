import io
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app, API_TOKEN
from app.config import APP_VERSION, GITHUB_REPO, UPDATES_DIR
from app.updater import parse_semver, is_version_newer, AppUpdater

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. Semver Comparison Unit Tests
# ---------------------------------------------------------------------------
def test_parse_semver():
    assert parse_semver("v1.2.4") == (1, 2, 4)
    assert parse_semver("1.2.5") == (1, 2, 5)
    assert parse_semver("v2.0.0-beta.1") == (2, 0, 0, 1)
    assert parse_semver("") == (0, 0, 0)
    assert parse_semver(None) == (0, 0, 0)

def test_is_version_newer():
    # Newer remote
    assert is_version_newer("v1.2.5", "1.2.4") is True
    assert is_version_newer("2.0.0", "1.9.9") is True
    assert is_version_newer("1.4.0", "1.3.0") is True
    assert is_version_newer("v1.2.4.1", "1.2.4") is True

    # Same or older remote
    assert is_version_newer("1.2.4", "1.2.4") is False
    assert is_version_newer("v1.2.4", "1.2.4") is False
    assert is_version_newer("1.2.3", "1.2.4") is False
    assert is_version_newer("1.0.0", "1.2.4") is False

# ---------------------------------------------------------------------------
# 2. API Endpoints Tests
# ---------------------------------------------------------------------------
def test_get_app_version():
    response = client.get("/api/app/version", headers={"X-Auth-Token": API_TOKEN})
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == APP_VERSION
    assert data["repository"] == GITHUB_REPO

def test_check_update_endpoint_newer_version():
    mock_github_response = {
        "tag_name": "v1.4.0",
        "name": "OmniDownloader v1.4.0 - Performance Release",
        "body": "### Changes\n- Faster downloads\n- Updated engine",
        "html_url": "https://github.com/Aniketkumar-01/socials_downloader/releases/tag/v1.4.0",
        "published_at": "2026-10-06T12:00:00Z",
        "assets": [
            {
                "name": "OmniDownloader-Setup.exe",
                "browser_download_url": "https://github.com/Aniketkumar-01/socials_downloader/releases/download/v1.4.0/OmniDownloader-Setup.exe",
                "size": 50123456
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_github_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        response = client.get("/api/app/update/check?force=true", headers={"X-Auth-Token": API_TOKEN})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["update_available"] is True
        assert data["latest_version"] == "1.4.0"
        assert data["current_version"] == APP_VERSION
        assert data["download_url"] == "https://github.com/Aniketkumar-01/socials_downloader/releases/download/v1.4.0/OmniDownloader-Setup.exe"
        assert data["file_size"] == 50123456

def test_check_update_endpoint_already_up_to_date():
    mock_github_response = {
        "tag_name": f"v{APP_VERSION}",
        "name": f"OmniDownloader v{APP_VERSION}",
        "body": "Current release notes",
        "html_url": f"https://github.com/Aniketkumar-01/socials_downloader/releases/tag/v{APP_VERSION}",
        "assets": []
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_github_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        response = client.get("/api/app/update/check?force=true", headers={"X-Auth-Token": API_TOKEN})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["update_available"] is False
        assert data["current_version"] == APP_VERSION

def test_update_download_progress_endpoint():
    response = client.get("/api/app/update/download-progress", headers={"X-Auth-Token": API_TOKEN})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "percent" in data

def test_updater_apply_security_rejects_arbitrary_path(tmp_path):
    # An installer path outside UPDATES_DIR or without .exe must be rejected
    updater = AppUpdater()
    arbitrary_file = tmp_path / "malicious.bat"
    arbitrary_file.write_text("echo hacked")

    with pytest.raises(FileNotFoundError):
        updater.apply_update(installer_path=str(arbitrary_file))
