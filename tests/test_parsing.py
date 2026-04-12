import pytest
from app.adapters.oura import OuraProvider
from app.adapters.apple_health import AppleHealthProvider
from datetime import datetime

# --- [OURA PARSING TESTS] ---

def test_oura_heartrate_transformation():
    provider = OuraProvider(pat="test")
    raw_data = [
        {
            "_metric_type": "heartrate",
            "timestamp": "2026-04-11T10:00:00Z",
            "bpm": 75,
            "source": "awake"
        }
    ]
    standardized = provider.transform_to_standard(raw_data)
    assert len(standardized) == 1
    assert standardized[0]["metric"] == "heart_rate"
    assert standardized[0]["val"] == 75.0
    assert standardized[0]["source"] == "Oura_v2"

def test_oura_sleep_hrv_transformation():
    provider = OuraProvider(pat="test")
    raw_data = [
        {
            "_metric_type": "sleep",
            "day": "2026-04-11",
            "hrv": {
                "timestamp": "2026-04-11T02:00:00Z",
                "interval": 300,
                "items": [60.0, 65.0, None, 70.0]
            }
        }
    ]
    standardized = provider.transform_to_standard(raw_data)
    # 3 non-null items
    assert len(standardized) == 3
    assert standardized[0]["metric"] == "heart_rate_variability"
    assert standardized[0]["val"] == 60.0
    assert standardized[0]["source"] == "Oura_v2_sleep"

# --- [APPLE HEALTH PARSING TESTS] ---

def test_apple_health_hr_transformation():
    provider = AppleHealthProvider()
    payload = {
        "data": {
            "metrics": [{
                "name": "heart_rate",
                "units": "bpm",
                "data": [{"date": "2026-04-11T12:00:00Z", "qty": 80.0}]
            }]
        }
    }
    standardized = provider.transform_to_standard(payload)
    assert len(standardized) == 1
    assert standardized[0]["metric"] == "heart_rate"
    assert standardized[0]["val"] == 80.0
    assert standardized[0]["source"] == "AppleWatch_v9"

def test_apple_health_hrv_sdnn_transformation():
    """Validates the newer 'sdnn' specific metric name parsing."""
    provider = AppleHealthProvider()
    payload = {
        "data": {
            "metrics": [{
                "name": "heart_rate_variability_sdnn",
                "units": "ms",
                "data": [{"date": "2026-04-11T12:05:00Z", "qty": 55.0}]
            }]
        }
    }
    standardized = provider.transform_to_standard(payload)
    assert len(standardized) == 1
    # Should be standardized to generic name for dashboard mapping
    assert standardized[0]["metric"] == "heart_rate_variability"
    assert standardized[0]["val"] == 55.0

def test_apple_health_multiple_metrics():
    provider = AppleHealthProvider()
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "heart_rate",
                    "data": [{"date": "2026-04-11T12:00:00Z", "qty": 70}]
                },
                {
                    "name": "mindful_minutes",
                    "data": [{"date": "2026-04-11T12:00:00Z", "qty": 5.0}]
                }
            ]
        }
    }
    standardized = provider.transform_to_standard(payload)
    assert len(standardized) == 2
    # Ensure tagging logic for mindfulness
    mindful_entry = next(e for e in standardized if e["metric"] == "mindful_minutes")
    assert mindful_entry["tag"] == "Recovery"

def test_apple_health_sleep_analysis_transformation():
    provider = AppleHealthProvider()
    payload = {
        "data": {
            "metrics": [{
                "name": "sleep_analysis",
                "data": [{"date": "2026-04-11T00:00:00Z", "qty": 480.0}]
            }]
        }
    }
    standardized = provider.transform_to_standard(payload)
    assert len(standardized) == 1
    assert standardized[0]["metric"] == "sleep_score"
    assert standardized[0]["val"] == 480.0

def test_apple_health_avg_value_extraction():
    provider = AppleHealthProvider()
    payload = {
        "data": {
            "metrics": [{
                "name": "heart_rate",
                "data": [{"date": "2026-04-11T12:00:00Z", "avg": 75.0}]
            }]
        }
    }
    standardized = provider.transform_to_standard(payload)
    assert len(standardized) == 1
    assert standardized[0]["val"] == 75.0

def test_oura_readiness_hrv_balance_fallback():
    provider = OuraProvider(pat="test")
    raw_data = [
        {
            "_metric_type": "daily_readiness",
            "day": "2026-04-11",
            "contributors": {
                "hrv_balance": 88
            }
        }
    ]
    standardized = provider.transform_to_standard(raw_data)
    assert any(e["metric"] == "hrv_balance" and e["val"] == 88.0 for e in standardized)

def test_apple_health_empty_payload():
    provider = AppleHealthProvider()
    assert provider.transform_to_standard({}) == []
    assert provider.transform_to_standard({"data": {}}) == []
