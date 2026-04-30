from .base import BiometricProvider
from typing import List, Dict, Any
from datetime import datetime

class CGMProvider(BiometricProvider):
    """
    Adapter for Continuous Glucose Monitoring (CGM) data.
    Supports ingestion from Dexcom, Stelo, or local bridge proxies.
    """
    LOINC_MAP = {
        "blood_glucose": "14745-4" # Glucose [Mass/volume] in Interstitial fluid
    }

    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """CGM data is often push-based or polled via specific cloud APIs."""
        return []

    def transform_to_standard(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transforms CGM JSON payload to standard format.
        Expected format: {'entries': [{'date': '...', 'sgv': 120, 'direction': 'SingleUp'}]}
        """
        entries = payload.get("entries", [])
        standardized = []
        
        for entry in entries:
            ts = entry.get('date') or entry.get('timestamp')
            val = entry.get('sgv') or entry.get('value')
            direction = entry.get('direction', 'Flat')
            
            if val is not None and ts:
                standardized.append({
                    "ts": ts,
                    "metric": "blood_glucose",
                    "val": float(val),
                    "unit": "mg/dL",
                    "source": "CGM_Provider",
                    "tag": direction,
                    "loinc": self.LOINC_MAP["blood_glucose"]
                })
        return standardized
