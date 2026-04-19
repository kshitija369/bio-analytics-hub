from .base import BiometricProvider
from typing import List, Dict, Any
from datetime import datetime

class AppleHealthProvider(BiometricProvider):
    # New: LOINC Mappings for DT4H-Sim FHIR Compliance
    LOINC_MAP = {
        "heart_rate": "8867-4",
        "heart_rate_variability": "80404-7",
        "mindful_minutes": "61150-9",   # Mindfulness duration
        "sleep_score": "70182-1"        # Sleep quality proxy
    }

    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Apple Health is push-based via webhooks, so fetch_data is not used for ingestion."""
        return []

    def transform_to_standard(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transforms Health Auto Export JSON payload to standard format.
        """
        # Support both 'data.metrics' and top-level 'metrics' just in case
        metrics = payload.get("data", {}).get("metrics") or payload.get("metrics", [])
        standardized = []
        
        for m in metrics:
            metric_name = m.get('name')
            data_entries = m.get('data', [])
            units = m.get('units', 'unknown')
            print(f"  [Apple Debug] Processing metric: {metric_name} ({len(data_entries)} points)")
            
            # Map metrics to standard names
            target_metrics = {
                'heart_rate': 'heart_rate',
                'heart_rate_variability': 'heart_rate_variability',
                'heart_rate_variability_sdnn': 'heart_rate_variability',
                'mindful_minutes': 'mindful_minutes',
                'sleep_analysis': 'sleep_score' # Proxy mapping for simplicity
            }
            
            if metric_name in target_metrics:
                db_metric = target_metrics[metric_name]
                for entry in data_entries:
                    # Health Auto Export uses 'qty' or 'value'
                    val = entry.get('qty')
                    if val is None: val = entry.get('value')
                    if val is None: val = entry.get('avg')
                    
                    if val is not None:
                        standardized.append({
                            "ts": entry.get('date'),
                            "metric": db_metric,
                            "val": float(val),
                            "unit": units,
                            "source": "AppleWatch_v9",
                            "tag": "Recovery" if metric_name == 'mindful_minutes' else "baseline",
                            "loinc": self.LOINC_MAP.get(db_metric)
                        })
        return standardized
