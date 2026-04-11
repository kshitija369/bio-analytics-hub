import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import os
import shutil
import sqlite3
from unittest.mock import patch, MagicMock

# --- [CONFIGURATION] ---
TEST_DIR = "/tmp/somatic_test"
WORKING_DB = f"{TEST_DIR}/working.sqlite"
PERSISTENT_DB = f"{TEST_DIR}/persistent.sqlite"

class MockSomaticDatabase:
    def __init__(self, db_path=None):
        self.working_db = WORKING_DB
        self.persistent_db = PERSISTENT_DB
        self.db_path = WORKING_DB
        self._initialized = False
        self._db_path_override = None

    def _ensure_initialized(self):
        if self._initialized: return
        with sqlite3.connect(self.working_db) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS biometrics (ts TEXT, metric TEXT, val REAL, unit TEXT, source TEXT, tag TEXT)")
        self._initialized = True

    def _flush_to_persistence(self):
        if os.path.exists(self.working_db):
            shutil.copy2(self.working_db, self.persistent_db)

    def insert_biometrics(self, entries):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("INSERT INTO biometrics VALUES (:ts, :metric, :val, :unit, :source, :tag)", entries)
        self._flush_to_persistence()

    def get_data(self, start, end, metrics=None):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM biometrics").fetchall()
            return [dict(row) for row in rows]

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    # Mock environment variables
    monkeypatch.setenv("OURA_PAT", "mock_oura_token")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "mock_user")
    monkeypatch.setenv("PUSHOVER_API_TOKEN", "mock_token")
    
    # Create the global mock instance
    mock_db_instance = MockSomaticDatabase()
    
    # Patch the DATABASE singleton in routes AND the class itself globally
    import app.api.routes as routes
    monkeypatch.setattr(routes, "get_db", lambda: mock_db_instance)
    
    # Force the trigger engine to be real but with cooldowns disabled
    from app.core.alerts import SomaticTriggerEngine
    real_engine = SomaticTriggerEngine()
    real_engine._last_alerts = {}
    monkeypatch.setattr(routes, "get_trigger_engine", lambda: real_engine)

    # Patch the class wherever it is instantiated (like in run_pipeline)
    with patch("app.core.database.SomaticDatabase", return_value=mock_db_instance):
        yield
        
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

from app.main import app
client = TestClient(app)

def test_cloud_survival_endpoints():
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200

def test_two_tier_persistence_flush():
    payload = {
        "data": { "metrics": [{"name": "heart_rate", "data": [{"date": "2026-04-11T12:00:00Z", "qty": 70.0}]}] }
    }
    response = client.post("/webhook/somatic-log", json=payload)
    assert response.status_code == 200
    assert os.path.exists(PERSISTENT_DB)

def test_sync_with_mock_oura():
    def mock_session_get(self, url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "heartrate" in url:
            mock_resp.json.return_value = {"data": [{"timestamp": "2026-04-11T10:00:00Z", "bpm": 65}]}
        elif "sleep" in url and "daily_" not in url:
            mock_resp.json.return_value = {"data": [{"day": "2026-04-11", "hrv": {"timestamp": "2026-04-11T02:00:00Z", "items": [60]}}]}
        elif "daily_sleep" in url:
            mock_resp.json.return_value = {"data": [{"day": "2026-04-11", "score": 85, "contributors": {}}]}
        elif "daily_readiness" in url:
            mock_resp.json.return_value = {"data": [{"day": "2026-04-11", "score": 90, "contributors": {"hrv_balance": 88}}]}
        elif "daily_activity" in url:
            mock_resp.json.return_value = {"data": [{"day": "2026-04-11", "steps": 10000}]}
        elif "daily_stress" in url:
            mock_resp.json.return_value = {"data": [{"day": "2026-04-11", "stress_high": 30}]}
        else:
            mock_resp.json.return_value = {"data": []}
        return mock_resp

    with patch("requests.Session.get", mock_session_get):
        response = client.get("/sync")
        assert response.status_code == 200
        status = client.get("/db-status").json()
        assert "heart_rate" in status["record_counts"]

def test_alert_engine_trigger():
    payload = {
        "data": { "metrics": [{"name": "heart_rate", "data": [{"date": "2026-04-11T12:00:00Z", "qty": 150.0}]}] }
    }
    with patch("app.core.alerts.send_to_watch", return_value=True) as mock_send:
        response = client.post("/webhook/somatic-log", json=payload)
        assert response.status_code == 200
        assert mock_send.called

def test_dashboard_rendering_logic():
    client.post("/webhook/somatic-log", json={
        "data": {"metrics": [{"name": "heart_rate", "data": [{"date": "2026-04-11T12:00:00Z", "qty": 60}]}]}
    })
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
