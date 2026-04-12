import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta, date
import os
import shutil
import sqlite3
from unittest.mock import patch, MagicMock

# --- [CONFIGURATION] ---
TEST_DIR = "/tmp/somatic_test"
WORKING_DB = f"{TEST_DIR}/working.sqlite"
PERSISTENT_DB = f"{TEST_DIR}/persistent.sqlite"

mock_db_instance = None

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
            conn.execute("CREATE TABLE IF NOT EXISTS experiment_results (experiment_id TEXT, ts TEXT, metric TEXT, val REAL, metadata TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS research_results (experiment_id TEXT, morning_date TEXT, independent_value REAL, dependent_value REAL, z_score_deviation REAL, circadian_alignment REAL, subjective_rating INTEGER)")
        self._initialized = True

    def _flush_to_persistence(self):
        if os.path.exists(self.working_db):
            shutil.copy2(self.working_db, self.persistent_db)

    def insert_biometrics(self, entries):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("INSERT INTO biometrics VALUES (:ts, :metric, :val, :unit, :source, :tag)", entries)
        self._flush_to_persistence()

    def insert_experiment_results(self, entries):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("INSERT INTO experiment_results VALUES (:experiment_id, :ts, :metric, :val, :metadata)", entries)
        self._flush_to_persistence()

    def insert_research_results(self, entries):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("INSERT INTO research_results VALUES (:experiment_id, :morning_date, :independent_value, :dependent_value, :z_score_deviation, :circadian_alignment, :subjective_rating)", entries)
        self._flush_to_persistence()

    def get_data(self, start, end, metrics=None):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM biometrics").fetchall()
            return [dict(row) for row in rows]

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    global mock_db_instance
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    # Mock environment variables
    monkeypatch.setenv("OURA_PAT", "mock_oura_token")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "mock_user")
    monkeypatch.setenv("PUSHOVER_API_TOKEN", "mock_token")
    
    # Patch the DATABASE singleton
    import app.api.routes as routes
    import importlib
    import app.engine.narc_evaluator
    importlib.reload(app.engine.narc_evaluator)
    
    mock_db_instance = MockSomaticDatabase()
    monkeypatch.setattr(routes, "get_db", lambda: mock_db_instance)
    
    from app.core.alerts import SomaticTriggerEngine
    real_engine = SomaticTriggerEngine()
    real_engine._last_alerts = {}
    monkeypatch.setattr(routes, "get_trigger_engine", lambda: real_engine)

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
    """
    Simulates a full Oura sync cycle. Patches both requests.get and Session.get.
    """
    def mock_get(url, *args, **kwargs):
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

    with patch("requests.get", side_effect=mock_get), \
         patch("requests.Session.get", side_effect=mock_get):
        response = client.get("/sync")
        assert response.status_code == 200
        status = client.get("/db-status").json()
        assert "heart_rate" in status["record_counts"]
        assert "experiment_counts" in status

def test_experiment_hub_ui():
    response = client.get("/experiments/")
    assert response.status_code == 200
    assert "Witness Research Hub" in response.text

def test_experiment_detail_ui():
    # Insert mock result first
    mock_db_instance.insert_research_results([{
        "experiment_id": "EXP-NARC-001",
        "morning_date": "2026-04-11",
        "independent_value": 50.0,
        "dependent_value": 60.0,
        "z_score_deviation": 1.5,
        "circadian_alignment": -1.0,
        "subjective_rating": 5
    }])
    response = client.get("/experiments/EXP-NARC-001")
    assert response.status_code == 200
    assert "NARC: Nocturnal Autonomic Recovery" in response.text

def test_experiment_api_list():
    response = client.get("/api/v1/experiments/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    ids = [e["id"] for e in data]
    assert "EXP-NARC-001" in ids

def test_evaluate_endpoint_days_back():
    # Insert some data for yesterday
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    # NARC needs HR and HRV. We use UTC 'Z' to avoid naive/aware issues.
    mock_db_instance.insert_biometrics([{
        "ts": f"{yesterday}T23:00:00Z",
        "metric": "heart_rate_variability", "val": 55.0,
        "unit": "ms", "source": "Mock", "tag": "baseline"
    }, {
        "ts": f"{yesterday}T23:30:00Z",
        "metric": "heart_rate", "val": 50.0,
        "unit": "bpm", "source": "Mock", "tag": "baseline"
    }, {
        "ts": f"{date.today().isoformat()}T00:00:00Z",
        "metric": "readiness_score", "val": 80.0,
        "unit": "score", "source": "Mock", "tag": "daily_insight"
    }])
    
    today_str = date.today().isoformat()
    response = client.get(f"/experiments/evaluate?experiment_id=EXP-NARC-001&target_date={today_str}&days_back=0")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_alert_engine_trigger():
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "data": { "metrics": [{"name": "heart_rate", "data": [{"date": now_iso, "qty": 150.0}]}] }
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
