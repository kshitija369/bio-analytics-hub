from app.core.alerts import SomaticTriggerEngine
from unittest.mock import patch
import os

# Ensure we use the correct config path
config_path = "config/triggers.yaml"

def simulate():
    print("--- Starting Somatic Alert Logic Simulation ---")
    engine = SomaticTriggerEngine(config_path)
    
    # We will mock 'send_to_watch' to see if it would have triggered
    with patch('app.core.alerts.send_to_watch', return_value=True) as mock_send:
        
        # Test 1: Normal Heart Rate (Should NOT alert)
        print("\nTest 1: Sending normal Heart Rate (75 BPM)...")
        engine.evaluate("heart_rate", 75)
        if not mock_send.called:
            print("SUCCESS: No alert sent for normal HR.")
        
        # Test 2: High Heart Rate (Should alert 'stress_spike')
        print("\nTest 2: Sending high Heart Rate (110 BPM)...")
        engine.evaluate("heart_rate", 110)
        if mock_send.called:
            args, kwargs = mock_send.call_args
            print(f"SUCCESS: Alert triggered!")
            print(f"  Title: {args[0]}")
            print(f"  Message: {args[1]}")
            print(f"  Priority: {args[2]}")
        mock_send.reset_mock()

        # Test 3: Low HRV (Should alert 'low_recovery')
        print("\nTest 3: Sending low HRV (25 ms)...")
        engine.evaluate("heart_rate_variability", 25)
        if mock_send.called:
            args, kwargs = mock_send.call_args
            print(f"SUCCESS: Alert triggered!")
            print(f"  Title: {args[0]}")
            print(f"  Message: {args[1]}")
        mock_send.reset_mock()

if __name__ == "__main__":
    simulate()
