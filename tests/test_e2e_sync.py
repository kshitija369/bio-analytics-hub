import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import BiometricDatabase
from datetime import datetime, timezone, timedelta

client = TestClient(app)
db = BiometricDatabase()

def test_e2e_apple_health_sync():
    print("\n--- Starting E2E Apple Health Sync Test ---")
    
    # 1. Create a "Recovery Signature" Payload
    # Using a specific timestamp to query later
    test_ts = datetime.now(timezone.utc)
    now_iso = test_ts.isoformat()
    
    test_payload = {
        "data": {
            "metrics": [
                {
                    "name": "heart_rate",
                    "units": "bpm",
                    "data": [{"date": now_iso, "qty": 75.0}]
                },
                {
                    "name": "heart_rate_variability",
                    "units": "ms",
                    "data": [{"date": now_iso, "qty": 85.5}]
                },
                {
                    "name": "mindful_minutes",
                    "units": "min",
                    "data": [{"date": now_iso, "qty": 1.0}]
                }
            ]
        }
    }

    # 2. Simulate the Webhook Post
    print(f"Sending mock payload for timestamp: {now_iso}")
    response = client.post("/webhook/biometric-log", json=test_payload)
    
    # 3. Assertions on Response
    assert response.status_code == 200
    assert response.json()["processed_data_points"] == 3
    
    # 4. Verify DB Persistence & Tagging
    # Query slightly before and after to ensure we catch it
    start = test_ts - timedelta(seconds=1)
    end = test_ts + timedelta(seconds=1)
    
    data = db.get_data(start, end, metrics=["mindful_minutes"])
    
    assert len(data) > 0
    # Verify the tag was automatically converted to 'Recovery' by the provider
    assert data[0]['tag'] == "Recovery", f"Expected tag 'Recovery', got '{data[0]['tag']}'"
    
    print("✅ E2E Sync Validated: Data persisted and tagged correctly.")

if __name__ == "__main__":
    test_e2e_apple_health_sync()
