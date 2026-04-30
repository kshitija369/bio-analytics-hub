import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta, date, time
from typing import Optional, Dict, Any
from app.domain.dimension_repository import DimensionRepository
from app.core.database import BiometricDatabase

class NAREvaluator:
    """
    Nocturnal Autonomic Recovery (NAR) Evaluator.
    Calculates Z-score deviations and the overnight 'Hammock Curve' efficiency.
    """
    EXPERIMENT_ID = "EXP-NAR-001"

    def __init__(self, db: Optional[BiometricDatabase] = None):
        self.db = db or BiometricDatabase()
        self.repo = DimensionRepository(db=self.db)

    def calculate_nighttime_metabolic_load(self, glucose_df: pd.DataFrame) -> float:
        """
        Calculates the Glucose Area Under Curve (AUC) for the nighttime period.
        """
        if glucose_df.empty:
            return 0.0
            
        # Calculate AUC using trapezoidal rule (mg/dL * minutes)
        # Assuming glucose_df is already filtered to the sleep window
        # Reset index to get time delta in minutes from start
        temp_df = glucose_df.copy()
        temp_df['minutes'] = (temp_df.index - temp_df.index[0]).total_seconds() / 60.0
        
        # Use np.trapezoid (NumPy 2.0+) or fallback to np.trapz
        if hasattr(np, 'trapezoid'):
            auc = np.trapezoid(temp_df['val'], x=temp_df['minutes'])
        else:
            auc = np.trapz(temp_df['val'], x=temp_df['minutes'])
        return float(auc)

    def evaluate(self, morning_date: date) -> Dict[str, Any]:
        """
        Main entry point for Nocturnal Autonomic Recovery daily evaluation.
        """
        print(f"--- [NAR] Running Evaluation for {morning_date} ---")

        
        # 1. Window: 22:30 (yesterday) to 07:30 (today)
        night_start = datetime.combine(morning_date - timedelta(days=1), time(22, 30))
        night_end = datetime.combine(morning_date, time(7, 30))
        
        # 2. Extract Agnostic Dimensions
        hrv_df = self.repo.get_dimension_data("HRV", night_start, night_end)
        hr_df = self.repo.get_dimension_data("HeartRate", night_start, night_end)
        glucose_df = self.repo.get_dimension_data("blood_glucose", night_start, night_end)
        readiness = self.repo.get_daily_aggregate("ReadinessScore", morning_date)

        if hrv_df.empty or hr_df.empty or readiness is None:
            print(f"  [NAR] Missing core dimensions for {morning_date}")
            return {"status": "missing_data"}

        # 3. Dip Calculator: min(heart_rate)
        min_hr_ts = hr_df['val'].idxmin()
        min_hr_val = hr_df.loc[min_hr_ts, 'val']
        
        # Calculate Dip Penalty (hours after 3 AM)
        # Dimensions from repo are naive datetimes (UTC-based)
        three_am = datetime.combine(morning_date, time(3, 0))
        
        # Positive value = late dip (bad), Negative = early dip (good)
        dip_delta_hours = (min_hr_ts - three_am).total_seconds() / 3600
        circadian_alignment = dip_delta_hours

        # 4. Metabolic Load Calculation (Glucose AUC)
        metabolic_load_auc = self.calculate_nighttime_metabolic_load(glucose_df)

        # 5. Z-Score Calculation (21-day HRV Baseline)
        baseline_start = morning_date - timedelta(days=22)
        baseline_end = morning_date - timedelta(days=1)
        
        # Get mean nightly HRVs for the last 21 days
        historical_hrvs = []
        for d in pd.date_range(baseline_start, baseline_end):
             # Window for that night
             d_start = datetime.combine(d.date() - timedelta(days=1), time(22, 30))
             d_end = datetime.combine(d.date(), time(7, 30))
             avg_h = self.repo.get_window_summary("HRV", d_start, d_end)
             if avg_h: historical_hrvs.append(avg_h)

        current_hrv_avg = hrv_df['val'].mean()
        
        z_score = 0.0
        if len(historical_hrvs) >= 7: # Need at least a week for baseline
            mu = np.mean(historical_hrvs)
            sigma = np.std(historical_hrvs)
            if sigma > 0:
                z_score = (current_hrv_avg - mu) / sigma

        # 6. Persistence
        self.save_result(
            morning_date, 
            independent_value=current_hrv_avg, 
            dependent_value=readiness,
            z_score=z_score,
            circadian_alignment=circadian_alignment,
            metabolic_load=metabolic_load_auc
        )

        return {
            "status": "success",
            "z_score": round(z_score, 2),
            "circadian_alignment": round(circadian_alignment, 2),
            "metabolic_load_auc": round(metabolic_load_auc, 1),
            "dip_hr": min_hr_val,
            "dip_time": min_hr_ts.isoformat()
        }

    def save_result(self, morning_date: date, independent_value, dependent_value, z_score, circadian_alignment, metabolic_load=0.0):
        self.db._ensure_initialized()
        with sqlite3.connect(self.db.working_db) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO research_results 
                (experiment_id, morning_date, independent_value, dependent_value, z_score_deviation, circadian_alignment, metabolic_load)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.EXPERIMENT_ID, morning_date.isoformat(), independent_value, dependent_value, z_score, circadian_alignment, metabolic_load))
        self.db._flush_to_persistence()

