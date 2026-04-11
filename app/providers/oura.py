import os
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
from .base import BiometricProvider

class OuraProvider(BiometricProvider):
    def __init__(self, pat=None):
        self.pat = pat or os.environ.get("OURA_PAT", "YOUR_OURA_TOKEN")
        self.headers = {'Authorization': f'Bearer {self.pat}'}
        self.base_url = "https://api.ouraring.com/v2/usercollection"

    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Fetches heartrate and daily_sleep data."""
        all_raw_data = []
        
        # 1. Fetch Heart Rate
        hr_url = f"{self.base_url}/heartrate"
        params = {
            'start_datetime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'end_datetime': end_time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        hr_resp = requests.get(hr_url, headers=self.headers, params=params)
        if hr_resp.status_code == 200:
            hr_data = hr_resp.json().get('data', [])
            for entry in hr_data:
                entry['_metric_type'] = 'heartrate'
            all_raw_data.extend(hr_data)
        
        # 2. Fetch Daily Sleep (for contributors like recovery_index)
        sleep_url = f"{self.base_url}/daily_sleep"
        # Sleep API uses start_date (YYYY-MM-DD)
        params_sleep = {
            'start_date': start_time.date().isoformat(),
            'end_date': end_time.date().isoformat()
        }
        sleep_resp = requests.get(sleep_url, headers=self.headers, params=params_sleep)
        if sleep_resp.status_code == 200:
            sleep_data = sleep_resp.json().get('data', [])
            for entry in sleep_data:
                entry['_metric_type'] = 'daily_sleep'
            all_raw_data.extend(sleep_data)
            
        return all_raw_data

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for entry in raw_data:
            metric_type = entry.get('_metric_type')
            
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
                # Map sleep contributors
                contribs = entry.get('contributors', {})
                day = entry['day']
                # Using 00:00:00 for daily metrics
                base_ts = f"{day}T00:00:00Z"
                
                metrics_to_map = {
                    'recovery_index': 'sleep_recovery_index',
                    'rem_sleep': 'sleep_rem_score',
                    'deep_sleep': 'sleep_deep_score',
                    'efficiency': 'sleep_efficiency'
                }
                
                for key, metric_name in metrics_to_map.items():
                    if key in contribs:
                        standardized.append({
                            "ts": base_ts,
                            "metric": metric_name,
                            "val": float(contribs[key]),
                            "unit": "score",
                            "source": "Oura_v2",
                            "tag": "daily_insight"
                        })
                
                if 'score' in entry:
                    standardized.append({
                        "ts": base_ts,
                        "metric": "sleep_score",
                        "val": float(entry['score']),
                        "unit": "score",
                        "source": "Oura_v2",
                        "tag": "daily_insight"
                    })
                    
        return standardized
