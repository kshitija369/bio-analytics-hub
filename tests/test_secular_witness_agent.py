import pytest
from app.core.alerts import BiometricTriggerEngine
from app.engine.agent_orchestrator import AgentOrchestrator
from app.core.database import BiometricDatabase
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import json

def test_secular_witness_agent_full_cycle():
    """
    Validates the event-driven lifecycle of the Secular Witness agent.
    Perception (Phase 1) -> Reasoning (Phase 2) -> Action (Phase 3).
    """
    print("\n--- Starting Secular Witness Agent E2E Validation ---")
    
    # 1. Setup Mock DB with history for Baseline
    db = BiometricDatabase(db_path="Test_Agent_Log.sqlite", working_db="Test_Agent_Working.sqlite")
    db._ensure_initialized()
    
    now = datetime.now(timezone.utc)
    # Insert 10 points for a stable baseline (~60 HRV)
    history = []
    for i in range(20):
        history.append({
            "ts": (now - timedelta(hours=i)).isoformat(),
            "metric": "heart_rate_variability",
            "val": 60.0,
            "unit": "ms", "source": "Mock", "tag": "baseline", "loinc": "80404-7"
        })
    db.insert_biometrics(history)
    
    # 2. Phase 1: Perception (Anomaly Detection)
    # Trigger a 40% drop (60 -> 36)
    current_val = 36.0
    trigger_engine = BiometricTriggerEngine(db=db)
    
    print("Phase 1: Evaluating anomaly...")
    with patch("app.core.alerts.BiometricTriggerEngine._publish_anomaly") as mock_publish:
        trigger_engine.evaluate_anomaly("heart_rate_variability", current_val, now)
        
        assert mock_publish.called
        anomaly_args = mock_publish.call_args[0]
        assert anomaly_args[0] == "heart_rate_variability"
        assert anomaly_args[3] < -20 # Verify deviation is > 20% drop
        print(f"✅ Phase 1 (Perception) Validated. Deviation: {anomaly_args[3]:.1f}%")
        
        # Capture the data that would go to Pub/Sub
        anomaly_data = {
            "metric": anomaly_args[0],
            "val": anomaly_args[1],
            "baseline": anomaly_args[2],
            "deviation": anomaly_args[3],
            "timestamp": now.isoformat()
        }

    # 3. Phase 2 & 3: Reasoning & Action
    orchestrator = AgentOrchestrator()
    orchestrator.repo.db = db # Point to test DB
    
    print("Phase 2/3: Processing anomaly through Orchestrator...")
    with patch("app.engine.agent_orchestrator.send_bidirectional_nudge", return_value=True) as mock_nudge:
        orchestrator.process_anomaly(anomaly_data)
        
        # Verify Action was staged (Phase 3)
        assert mock_nudge.called
        assert "Toxic Stress" in mock_nudge.call_args[1]['message']
        print("✅ Phase 2/3 (Reasoning & Action) Validated.")

    print("\n--- Additional Exhaustive Checks ---")
    
    # 4. Test 'Good Difficulty' Logic (Minor drop < 30%)
    minor_anomaly = anomaly_data.copy()
    minor_anomaly['deviation'] = -15.0 # 15% drop
    
    with patch("app.engine.agent_orchestrator.send_bidirectional_nudge") as mock_nudge_minor:
        orchestrator.process_anomaly(minor_anomaly)
        # Should not trigger an action for minor drops
        assert not mock_nudge_minor.called
        print("✅ Reasoning (Good Difficulty) Validated.")

    # 6. Test Insufficient Baseline Data
    print("Phase 1: Testing insufficient data edge case...")
    empty_db = BiometricDatabase(db_path="Empty_Test.sqlite", working_db="Empty_Working.sqlite")
    empty_db._ensure_initialized()
    trigger_engine_empty = BiometricTriggerEngine(db=empty_db)

    with patch("app.core.alerts.BiometricTriggerEngine._publish_anomaly") as mock_publish_empty:
        # 1 point is not enough for a baseline
        empty_db.insert_biometrics([{
            "ts": now.isoformat(), "metric": "heart_rate_variability", "val": 60.0,
            "unit": "ms", "source": "Mock", "tag": "baseline", "loinc": "80404-7"
        }])
        trigger_engine_empty.evaluate_anomaly("heart_rate_variability", 30.0, now)
        assert not mock_publish_empty.called
        print("✅ Insufficient Data Handling Validated.")

    # Cleanup all test DBs
    import os
    for f in ["Empty_Test.sqlite", "Empty_Working.sqlite", "Test_Agent_Log.sqlite", "Test_Agent_Working.sqlite"]:
        if os.path.exists(f): os.remove(f)

    print("\n--- Secular Witness Agent Validation Complete ---")

if __name__ == "__main__":
    test_secular_witness_agent_full_cycle()
