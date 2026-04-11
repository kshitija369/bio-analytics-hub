import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import os

# We use a test-specific DB file
TEST_DB = "/tmp/test_somatic_log.sqlite"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    # Ensure clean state
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    if os.path.exists("/tmp/Somatic_Log_Working.sqlite"):
        os.remove("/tmp/Somatic_Log_Working.sqlite")
        
    # Patch the database path before any imports
    monkeypatch.setenv("GCS_BUCKET_NAME", "mock-bucket")
    
    # Reload modules to pick up the patch if needed
    import importlib
    import app.core.database
    importlib.reload(app.core.database)
    
    yield
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

# Import app after patching
from app.main import app
client = TestClient(app)

def test_endpoint_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_endpoint_db_status():
    response = client.get("/db-status")
    assert response.status_code == 200
    assert "db_path" in response.json()

def test_endpoint_webhook_and_dashboard():
    # 1. Post mock data
    payload = {
        "data": {
            "metrics": [{
                "name": "heart_rate",
                "data": [{"date": datetime.now(timezone.utc).isoformat(), "qty": 75.0}]
            }]
        }
    }
    response = client.post("/webhook/somatic-log", json=payload)
    assert response.status_code == 200
    
    # 2. Check dashboard serves HTML with data
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Somatic" in response.text
