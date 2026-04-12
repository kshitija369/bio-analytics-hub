import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure app is in path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.alerts import BiometricTriggerEngine
from app.core.notifiers import send_to_watch

def debug_full_stack():
    # 1. Check for .env file location
    root_env = Path(__file__).parent.parent / '.env'
    print(f"--- 1. Checking Environment (.env at {root_env}) ---")
    if root_env.exists():
        load_dotenv(dotenv_path=root_env)
        print("SUCCESS: .env file found and loaded.")
    else:
        print("WARNING: .env file NOT found in root.")

    u = os.getenv("PUSHOVER_USER_KEY")
    t = os.getenv("PUSHOVER_API_TOKEN")
    o = os.getenv("OURA_PAT")
    
    print(f"User Key: {'SET' if u else 'MISSING'}")
    print(f"API Token: {'SET' if t else 'MISSING'}")
    print(f"Oura PAT: {'SET' if o else 'MISSING'}")

    print("\n--- 2. Testing Direct Notifier (Watch Tap) ---")
    # This bypasses all logic and goes straight to the API
    success = send_to_watch("Deep Debug", "If you feel this, Notifier is OK.", priority=1)
    if success:
        print("SUCCESS: API call returned 200.")
    else:
        print("FAILED: API call failed. Check credentials above.")

    print("\n--- 3. Testing Engine Logic (Stress Spike) ---")
    engine = BiometricTriggerEngine()
    print("Sending 110 BPM (Threshold is 100)...")
    # This should trigger the 'stress_spike' rule if not in cooldown
    engine.evaluate("heart_rate", 110)
    
    print("\n--- 4. Checking Cooldowns ---")
    print(f"Active Cooldowns: {BiometricTriggerEngine._last_alerts.keys()}")

if __name__ == "__main__":
    debug_full_stack()
