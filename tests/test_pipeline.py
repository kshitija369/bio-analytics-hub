import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import BiometricDatabase
import pandas as pd
from datetime import datetime, timezone

client = TestClient(app)

# 1. Integration Test: Webhook Ingestion (Apple Health)
def test_apple_health_webhook_ingestion():
    db = BiometricDatabase()
    test_payload = {
        "data": {
            "metrics": [{
                "name": "heart_rate",
                "units": "count/min",
                "data": [{"date": "2026-04-10T12:00:00Z", "qty": 80.0}]
            }]
        }
    }
    response = client.post("/webhook/biometric-log", json=test_payload)
    
    assert response.status_code == 200
    assert response.json()["processed_data_points"] == 1
    
    # Verify the data actually landed in SQLite
    start = datetime(2026, 4, 10, 11, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc)
    data = db.get_data(start, end, metrics=["heart_rate"])
    
    assert len(data) > 0
    # The ts in DB is stored as ISO string from the payload
    assert any(d['val'] == 80.0 for d in data)

# 2. Unit Test: Normalization & Interpolation Logic
def test_normalization_interpolation():
    from app.core.normalization import BiometricNormalizer
    
    # Mock data with a 5 min gap
    raw_data = [
        {"ts": "2026-04-10T10:00:00Z", "metric": "heart_rate", "val": 60.0, "source": "MockWatch", "tag": "test"},
        {"ts": "2026-04-10T10:05:00Z", "metric": "heart_rate", "val": 70.0, "source": "MockWatch", "tag": "test"}
    ]
    
    df = BiometricNormalizer.normalize_to_timeseries(raw_data, resample_rate='1min')
    
    # Check if we have 6 minutes (0, 1, 2, 3, 4, 5)
    assert len(df) == 6
    # Check if the 10:02:00 minute was filled via linear interpolation
    # 60 + (70-60)*(2/5) = 64.0
    val_at_2min = df.loc[pd.to_datetime("2026-04-10T10:02:00Z"), "heart_rate"]
    assert val_at_2min == 64.0
