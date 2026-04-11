import os
import requests
from datetime import datetime, timedelta

OURA_PAT = os.environ.get("OURA_PAT", "YOUR_OURA_TOKEN")
HEADERS = {'Authorization': f'Bearer {OURA_PAT}'}

def check_endpoints():
    now = datetime.now()
    start = now - timedelta(days=30) # Look back 30 days
    start_str = start.strftime("%Y-%m-%d")
    
    endpoints = [
        'heartrate',
        'daily_stress',
        'sleep',
        'activity',
        'readiness'
    ]
    
    print(f"Checking Oura data for the last 30 days (since {start_str})...\n")
    
    for ep in endpoints:
        url = f'https://api.ouraring.com/v2/usercollection/{ep}'
        # Note: some endpoints use start_datetime, others use start_date
        params = {'start_date': start_str} if ep in ['sleep', 'activity', 'readiness', 'daily_stress'] else {'start_datetime': start.isoformat()}
        
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json().get('data', [])
            print(f"[{ep.upper()}]: Found {len(data)} entries.")
        else:
            print(f"[{ep.upper()}]: Error {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_endpoints()
