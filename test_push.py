import os
import requests
from dotenv import load_dotenv

# 1. Load your keys (from .env or system environment)
load_dotenv()
USER_KEY = os.getenv("PUSHOVER_USER_KEY")
API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

def trigger_test_notification():
    if not USER_KEY or not API_TOKEN:
        print("❌ Error: PUSHOVER_USER_KEY or PUSHOVER_API_TOKEN not found.")
        print("Make sure you ran 'export' or have a .env file.")
        return

    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": API_TOKEN,
        "user": USER_KEY,
        "message": "Witness Test: If you feel this, your Apple Watch is connected! 🧘",
        "title": "Somatic Alert",
        "priority": 1,      # Priority 1 bypasses 'quiet' modes and triggers haptics
        "sound": "calm"     # A subtle sound for mindfulness
    }

    print(f"📡 Sending test notification to User Key starting with: {USER_KEY[:5]}...")
    try:
        response = requests.post(url, data=data, timeout=5)
        if response.status_code == 200:
            print("✅ Success! Check your Apple Watch for a haptic tap.")
        else:
            print(f"❌ Failed. Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    trigger_test_notification()
