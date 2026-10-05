import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app, API_TOKEN

@pytest.fixture
def auth_headers():
    """Provides valid session auth headers for API calls."""
    return {"X-Omni-Token": API_TOKEN}

@pytest.fixture
def auth_client():
    """Provides a TestClient pre-configured with valid session auth and host headers."""
    return TestClient(app, base_url="http://127.0.0.1", headers={"X-Omni-Token": API_TOKEN})

@pytest.fixture
def client():
    """Standard unauthenticated client fixture with valid 127.0.0.1 Host header."""
    return TestClient(app, base_url="http://127.0.0.1")
