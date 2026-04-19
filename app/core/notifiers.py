import requests
import os
from dotenv import load_dotenv

load_dotenv()

def send_to_watch(title, message, priority=0):
    """
    Sends a push notification to Apple Watch via Pushover.
    Requires: PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN
    """
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    token = os.environ.get("PUSHOVER_API_TOKEN")

    if not user_key or not token:
        print("Warning: PUSHOVER credentials not set. Alert not sent.")
        return False

    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": token,
        "user": user_key,
        "message": message,
        "title": title,
        "priority": priority,
        "sound": "magic" if priority > 0 else "none"
    }

    try:
        response = requests.post(url, data=data, timeout=5)
        if response.status_code == 200:
            print(f"Watch Alert Sent: {title}")
            return True
        else:
            print(f"Error sending to Pushover: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception during notification send: {e}")
        return False

def send_bidirectional_nudge(title, message, callback_url=None):
    """
    DT4H-Sim/Secular-Witness: Phase 3.
    Sends a nudge with interactive actions (Accept/Snooze/Reject).
    """
    print(f"--- [Notifier] Sending Bidirectional Nudge: {title} ---")
    # In production, this would use WhatsApp Business or Slack with interactive blocks
    # and provide a callback_url for the User's Human-in-the-Loop decision.
    print(f"  [Notifier] Message: {message}")
    print(f"  [Notifier] Waiting for HITL response at {callback_url}...")
    return True
