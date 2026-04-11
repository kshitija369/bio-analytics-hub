from .base import BiometricProvider
from typing import List, Dict, Any
from datetime import datetime

class AppleHealthProvider(BiometricProvider):
    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Apple Health is push-based via webhooks, so fetch_data is not used for ingestion."""
        return []

    def transform_to_standard(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transforms Health Auto Export JSON payload to standard format.
        """
        metrics = payload.get("data", {}).get("metrics", [])
        standardized = []
        
        for m in metrics:
            metric_name = m.get('name')
            data_entries = m.get('data', [])
            print(f"  [Debug] Processing metric: {metric_name} ({len(data_entries)} points)")
            
            # Filter for relevant metrics
            if metric_name in ['heart_rate', 'heart_rate_variability', 'mindful_minutes']:
                for entry in data_entries:
                    val = entry.get('qty') or entry.get('avg') or entry.get('value')
                    if val is not None:
                        standardized.append({
                            "ts": entry.get('date'),
                            "metric": metric_name,
                            "val": float(val),
                            "unit": m.get('units'),
                            "source": "AppleWatch_v9",
                            "tag": "Witnessing" if metric_name == 'mindful_minutes' else "baseline"
                        })
        return standardized
