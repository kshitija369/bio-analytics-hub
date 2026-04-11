import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .base import BiometricProvider
import pandas as pd

class OuraProvider(BiometricProvider):
    def __init__(self, pat=None):
        # 1. Prioritize passed PAT, then environment, then fallback
        raw_pat = pat or os.environ.get("OURA_PAT", "")
        
        # 2. Strict Validation: Check if token is effectively empty or placeholder
        self.pat = str(raw_pat).strip()
        if not self.pat or self.pat == "YOUR_OURA_TOKEN":
            print("--- [OURA ERROR] No valid OURA_PAT found in environment or secrets! ---")
            
        self.base_url = "https://api.ouraring.com/v2/usercollection"

    def _get_headers(self):
        """Generates fresh headers for each request."""
        return {
            'Authorization': f'Bearer {self.pat}',
            'User-Agent': 'Witness-State-Monitor/1.0',
            'Accept': 'application/json'
        }

    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetches heartrate, sleep sessions, and daily summaries."""
        if not self.pat:
            print("--- [OURA ERROR] Aborting fetch: Missing API Token ---")
            return []

        all_raw_data = []
        headers = self._get_headers()
        
        # 1. Fetch Heart Rate
        current_start = start_time
        while current_start < end_time:
            current_end = min(current_start + timedelta(days=1), end_time)
            url = f"{self.base_url}/heartrate"
            params = {
                'start_datetime': current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end_datetime': current_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            try:
                # Use direct requests.get for maximum compatibility
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code == 200:
                    data = resp.json().get('data', [])
                    for entry in data: entry['_metric_type'] = 'heartrate'
                    all_raw_data.extend(data)
                else:
                    print(f"  [Oura Debug] FAILED HR ({resp.status_code}): {resp.text}")
            except Exception as e:
                print(f"  [Oura Debug] HR EXCEPTION: {e}")
            current_start = current_end
        
        # 2. Daily Summary and Session Endpoints
        params_daily = {
            'start_date': start_time.date().isoformat(),
            'end_date': end_time.date().isoformat()
        }
        
        endpoints = ['sleep', 'daily_sleep', 'daily_readiness', 'daily_activity', 'daily_stress']
        for ep in endpoints:
            url = f"{self.base_url}/{ep}"
            try:
                resp = requests.get(url, headers=headers, params=params_daily, timeout=30)
                if resp.status_code == 200:
                    data = resp.json().get('data', [])
                    print(f"  [Oura Debug] SUCCESS: {ep} ({len(data)} records)")
                    for entry in data: entry['_metric_type'] = ep
                    all_raw_data.extend(data)
                else:
                    print(f"  [Oura Debug] FAILED {ep} ({resp.status_code}): {resp.text}")
            except Exception as e:
                print(f"  [Oura Debug] {ep} EXCEPTION: {e}")
            
        return all_raw_data

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for entry in raw_data:
            metric_type = entry.get('_metric_type')
            day = entry.get('day')
            
            if metric_type == 'heartrate':
                standardized.append({
                    "ts": entry['timestamp'], "metric": "heart_rate", "val": float(entry['bpm']),
                    "unit": "bpm", "source": "Oura_v2", "tag": "baseline"
                })
            
            elif metric_type == 'sleep':
                if 'hrv' in entry and 'items' in entry['hrv']:
                    ts = pd.to_datetime(entry['hrv']['timestamp'])
                    interval = entry['hrv'].get('interval', 300)
                    for i, val in enumerate(entry['hrv']['items']):
                        if val is not None:
                            sample_ts = (ts + timedelta(seconds=i*interval)).isoformat()
                            standardized.append({
                                "ts": sample_ts, "metric": "heart_rate_variability", "val": float(val),
                                "unit": "ms", "source": "Oura_v2_sleep", "tag": "baseline"
                            })
                elif 'average_hrv' in entry and entry['average_hrv']:
                    standardized.append({
                        "ts": f"{day}T00:00:00Z", "metric": "heart_rate_variability", 
                        "val": float(entry['average_hrv']), "unit": "ms", "source": "Oura_v2", "tag": "daily_insight"
                    })

            elif metric_type == 'daily_readiness':
                base_ts = f"{day}T00:00:00Z"
                if 'score' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "readiness_score", "val": float(entry['score']),
                        "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                    })
                if 'contributors' in entry and 'hrv_balance' in entry['contributors']:
                    val = entry['contributors']['hrv_balance']
                    if val is not None:
                        standardized.append({
                            "ts": base_ts, "metric": "hrv_balance", "val": float(val),
                            "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                        })

            elif metric_type == 'daily_sleep':
                base_ts = f"{day}T00:00:00Z"
                if 'score' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "sleep_score", "val": float(entry['score']),
                        "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                    })

            elif metric_type == 'daily_activity':
                base_ts = f"{day}T12:00:00Z"
                if 'steps' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "steps", "val": float(entry['steps']),
                        "unit": "steps", "source": "Oura_v2", "tag": "daily_insight"
                    })
                    
        return standardized
