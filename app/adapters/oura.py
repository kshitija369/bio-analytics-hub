import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from .base import BiometricProvider
import pandas as pd

class OuraProvider(BiometricProvider):
    # New: LOINC Mappings for DT4H-Sim FHIR Compliance
    LOINC_MAP = {
        "heart_rate": "8867-4",
        "heart_rate_variability": "80404-7",
        "steps": "55423-8",
        "readiness_score": "LP200424-3", # Generic Recovery/Readiness
        "sleep_score": "70182-1",      # Sleep Duration/Quality
        "hrv_balance": "80404-7"        # Map to HRV dimension
    }

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
            'User-Agent': 'Bio-Analytics-Monitor/1.0',
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
            
            def create_entry(ts, metric, val, unit, source, tag):
                return {
                    "ts": ts, "metric": metric, "val": val,
                    "unit": unit, "source": source, "tag": tag,
                    "loinc": self.LOINC_MAP.get(metric)
                }

            if metric_type == 'heartrate':
                standardized.append(create_entry(
                    entry['timestamp'], "heart_rate", float(entry['bpm']),
                    "bpm", "Oura_v2", "baseline"
                ))
            
            elif metric_type == 'sleep':
                if 'hrv' in entry and 'items' in entry['hrv']:
                    ts = pd.to_datetime(entry['hrv']['timestamp'])
                    interval = entry['hrv'].get('interval', 300)
                    for i, val in enumerate(entry['hrv']['items']):
                        if val is not None:
                            sample_ts = (ts + timedelta(seconds=i*interval)).isoformat()
                            standardized.append(create_entry(
                                sample_ts, "heart_rate_variability", float(val),
                                "ms", "Oura_v2_sleep", "baseline"
                            ))
                elif 'average_hrv' in entry and entry['average_hrv']:
                    standardized.append(create_entry(
                        f"{day}T00:00:00Z", "heart_rate_variability", 
                        float(entry['average_hrv']), "ms", "Oura_v2", "daily_insight"
                    ))

            elif metric_type == 'daily_readiness':
                base_ts = f"{day}T00:00:00Z"
                if 'score' in entry:
                    standardized.append(create_entry(
                        base_ts, "readiness_score", float(entry['score']),
                        "score", "Oura_v2", "daily_insight"
                    ))
                if 'contributors' in entry and 'hrv_balance' in entry['contributors']:
                    val = entry['contributors']['hrv_balance']
                    if val is not None:
                        standardized.append(create_entry(
                            base_ts, "hrv_balance", float(val),
                            "score", "Oura_v2", "daily_insight"
                        ))

            elif metric_type == 'daily_sleep':
                base_ts = f"{day}T00:00:00Z"
                if 'score' in entry:
                    standardized.append(create_entry(
                        base_ts, "sleep_score", float(entry['score']),
                        "score", "Oura_v2", "daily_insight"
                    ))

            elif metric_type == 'daily_activity':
                base_ts = f"{day}T12:00:00Z"
                if 'steps' in entry:
                    standardized.append(create_entry(
                        base_ts, "steps", float(entry['steps']),
                        "steps", "Oura_v2", "daily_insight"
                    ))
                    
        return standardized
