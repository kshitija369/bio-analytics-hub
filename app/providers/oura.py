import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .base import BiometricProvider

class OuraProvider(BiometricProvider):
    def __init__(self, pat=None):
        self.pat = pat or os.environ.get("OURA_PAT", "YOUR_OURA_TOKEN")
        self.headers = {'Authorization': f'Bearer {self.pat}'}
        self.base_url = "https://api.ouraring.com/v2/usercollection"

    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetches heartrate, sleep, stress, and readiness data."""
        all_raw_data = []
        # Local headers to ensure consistency
        local_headers = {'Authorization': f'Bearer {self.pat}'}
        
        # 1. Fetch Heart Rate in 24h chunks
        current_start = start_time
        while current_start < end_time:
            current_end = min(current_start + timedelta(days=1), end_time)
            hr_url = f"{self.base_url}/heartrate"
            params = {
                'start_datetime': current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end_datetime': current_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            hr_resp = requests.get(hr_url, headers=local_headers, params=params)
            if hr_resp.status_code == 200:
                hr_data = hr_resp.json().get('data', [])
                for entry in hr_data:
                    entry['_metric_type'] = 'heartrate'
                all_raw_data.extend(hr_data)
            current_start = current_end
        
        # 2. Daily Summary Endpoints
        params_daily = {
            'start_date': start_time.date().isoformat(),
            'end_date': end_time.date().isoformat()
        }
        
        endpoints = ['daily_sleep', 'daily_stress', 'daily_readiness', 'daily_activity']
        for endpoint in endpoints:
            url = f"{self.base_url}/{endpoint}"
            resp = requests.get(url, headers=local_headers, params=params_daily)
            if resp.status_code == 200:
                data = resp.json().get('data', [])
                print(f"  [Oura Debug] SUCCESS: Fetched {len(data)} from {endpoint}")
                for entry in data:
                    entry['_metric_type'] = endpoint
                all_raw_data.extend(data)
            else:
                print(f"  [Oura Debug] FAILED {endpoint}: {resp.status_code} - {resp.text}")
                print(f"  [Oura Debug] URL attempted: {url}")
            
        return all_raw_data

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for entry in raw_data:
            metric_type = entry.get('_metric_type')
            day = entry.get('day')
            
            if metric_type == 'heartrate':
                standardized.append({
                    "ts": entry['timestamp'],
                    "metric": "heart_rate",
                    "val": float(entry['bpm']),
                    "unit": "bpm",
                    "source": "Oura_v2",
                    "tag": entry.get('source', 'baseline')
                })
            
            elif metric_type == 'daily_sleep':
                base_ts = f"{day}T00:00:00Z"
                contribs = entry.get('contributors', {})
                metrics_to_map = {
                    'recovery_index': 'sleep_recovery_index',
                    'rem_sleep': 'sleep_rem_score',
                    'deep_sleep': 'sleep_deep_score'
                }
                for key, metric_name in metrics_to_map.items():
                    if key in contribs:
                        standardized.append({
                            "ts": base_ts, "metric": metric_name, "val": float(contribs[key]),
                            "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                        })
                if 'score' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "sleep_score", "val": float(entry['score']),
                        "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                    })

            elif metric_type == 'daily_readiness':
                base_ts = f"{day}T00:00:00Z"
                # Debug logging to see available keys
                print(f"  [Oura Debug] Readiness Keys: {list(entry.keys())}")
                
                if 'hrv_iv' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "heart_rate_variability", "val": float(entry['hrv_iv']),
                        "unit": "ms", "source": "Oura_v2", "tag": "daily_insight"
                    })
                elif 'contributors' in entry and 'hrv_balance' in entry['contributors']:
                    # Fallback to balance if raw IV is missing
                    standardized.append({
                        "ts": base_ts, "metric": "heart_rate_variability", "val": float(entry['contributors']['hrv_balance']),
                        "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                    })
                
                if 'score' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "readiness_score", "val": float(entry['score']),
                        "unit": "score", "source": "Oura_v2", "tag": "daily_insight"
                    })

            elif metric_type == 'daily_activity':
                base_ts = f"{day}T12:00:00Z" # Midday for activity summaries
                mapping = {
                    'active_calories': 'calories',
                    'steps': 'steps',
                    'equivalent_walking_distance': 'walking_m'
                }
                for key, metric in mapping.items():
                    if key in entry:
                        standardized.append({
                            "ts": base_ts, "metric": metric, "val": float(entry[key]),
                            "unit": "val", "source": "Oura_v2", "tag": "daily_insight"
                        })

            elif metric_type == 'daily_stress':
                base_ts = f"{day}T12:00:00Z"
                if 'stress_high' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "stress_high_min", "val": float(entry['stress_high']),
                        "unit": "min", "source": "Oura_v2", "tag": "daily_insight"
                    })
                if 'recovery_high' in entry:
                    standardized.append({
                        "ts": base_ts, "metric": "recovery_high_min", "val": float(entry['recovery_high']),
                        "unit": "min", "source": "Oura_v2", "tag": "daily_insight"
                    })
                    
        return standardized
