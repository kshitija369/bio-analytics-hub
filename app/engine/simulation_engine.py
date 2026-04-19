import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class SimulationEngine:
    """
    DT4H-Sim Predictive Sandbox.
    Orchestrates Vertex AI models to generate 'Synthetic Days' 
    and Multi-Scale Digital Twin (MSDT) predictions.
    """
    def __init__(self, experiment_id: str = "EXP-SRI-001"):
        self.experiment_id = experiment_id
        # Placeholder for Vertex AI configuration
        self.model_endpoint = "projects/P/locations/L/endpoints/E"

    def predict_next_24h(self, history_df: pd.DataFrame, prospective_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates a synthetic 24-hour trajectory using vector-based modeling.
        Returns both time-series data and a single predicted Readiness Score.
        """
        print(f"--- [MSDT Engine] Simulating vector-based 24h for {self.experiment_id} ---")
        
        if history_df.empty:
            return {"status": "error", "message": "No historical data"}

        # 1. Establish Baseline (The 'Twin' state)
        last_ts = history_df.index.max()
        synthetic_start = last_ts + timedelta(minutes=15)
        synthetic_end = synthetic_start + timedelta(hours=24)
        idx = pd.date_range(start=synthetic_start, end=synthetic_end, freq='15min')
        
        base_hr = history_df['heart_rate'].mean() if 'heart_rate' in history_df.columns else 60.0
        base_hrv = history_df['heart_rate_variability'].mean() if 'heart_rate_variability' in history_df.columns else 50.0
        base_readiness = 80.0 # Standard baseline

        # 2. Calculate Vectors
        nature_time = sum([e.get('duration_mins', 0) for e in prospective_events if e.get('event') == 'nature'])
        meditation_time = sum([e.get('duration_mins', 0) for e in prospective_events if e.get('event') == 'meditation'])
        cold_plunge = any([e.get('event') == 'cold_exposure' for e in prospective_events])
        alcohol_drinks = sum([e.get('drinks', 0) for e in prospective_events if e.get('event') == 'alcohol'])
        late_meal = any([e.get('event') == 'meal' and '21:00' < str(e.get('time', '00:00')) for e in prospective_events])

        # 3. Physiological Impact Calculation
        # HRV Delta (Higher is Better)
        hrv_delta = (nature_time / 15 * 1.5) + (meditation_time / 10 * 1.0) + (5.0 if cold_plunge else 0)
        hrv_delta -= (alcohol_drinks * 6.0) + (8.0 if late_meal else 0)
        
        # HR Delta (Lower is Better)
        hr_delta = (alcohol_drinks * 5.0) + (4.0 if late_meal else 0)
        hr_delta -= (nature_time / 15 * 1.0) + (meditation_time / 10 * 0.5) + (2.0 if cold_plunge else 0)

        # Readiness Score Impact
        readiness_delta = (nature_time / 15 * 2.0) + (meditation_time / 10 * 1.5) + (8.0 if cold_plunge else 0)
        readiness_delta -= (alcohol_drinks * 8.0) + (12.0 if late_meal else 0)
        predicted_readiness = max(0, min(100, base_readiness + readiness_delta))

        # Dip Shift (Negative = Earlier/Better)
        dip_shift = (alcohol_drinks * 0.5 + (1.5 if late_meal else 0)) - (nature_time / 60 * 0.5 + (1.0 if cold_plunge else 0))

        # 4. Generate Trajectories
        t_hours = np.linspace(0, 24, len(idx))
        dip_center = 6.0 + dip_shift
        hammock = -5.0 * np.exp(-((t_hours - dip_center)**2) / (2 * 3.0**2))
        
        synthetic_hr = base_hr + hr_delta + hammock + np.random.normal(0, 0.5, len(idx))
        synthetic_hrv = base_hrv + hrv_delta + (-hammock * 1.5) + np.random.normal(0, 1.0, len(idx))

        df = pd.DataFrame(index=idx)
        df['heart_rate'] = synthetic_hr
        df['heart_rate_variability'] = synthetic_hrv
        df['is_synthetic'] = 1
        df['ts'] = df.index.map(lambda x: x.isoformat())
        
        return {
            "status": "success",
            "predicted_readiness": round(predicted_readiness, 1),
            "predicted_hrv_avg": round(base_hrv + hrv_delta, 1),
            "time_series": df.reset_index().to_dict(orient="records")
        }
