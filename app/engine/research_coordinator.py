import json
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from .dimension_repository import DimensionRepository
from app.core.database import SomaticDatabase

class ResearchCoordinator:
    """
    The 'Agnostic Data Fetcher' that combines protocol definitions 
    with actual database results for the UI/API.
    """
    def __init__(self):
        self.repo = DimensionRepository()
        self.db = SomaticDatabase()

    def get_experiment_results(self, experiment_id: str, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """
        Fetches recorded results for a specific experiment, optionally filtered by date.
        """
        self.db._ensure_initialized()
        import sqlite3
        with sqlite3.connect(self.db.working_db) as conn:
            conn.row_factory = sqlite3.Row
            
            params = [experiment_id]
            date_filter = ""
            if start_date:
                date_filter += " AND morning_date >= ?" if experiment_id == "EXP-NARC-001" else " AND ts >= ?"
                params.append(start_date.isoformat())
            if end_date:
                date_filter += " AND morning_date <= ?" if experiment_id == "EXP-NARC-001" else " AND ts <= ?"
                params.append(end_date.isoformat())

            if experiment_id == "EXP-NARC-001":
                query = f"SELECT morning_date as ts, 'NARC_Score' as metric, independent_value as val, morning_date, independent_value as ind_val, dependent_value as dep_val, z_score_deviation, circadian_alignment FROM research_results WHERE experiment_id = ? {date_filter} ORDER BY morning_date DESC"
                rows = conn.execute(query, params).fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    d['metadata'] = {
                        "ind_val": d['ind_val'],
                        "dep_val": d['dep_val'],
                        "z_score": d['z_score_deviation'],
                        "circadian": d['circadian_alignment']
                    }
                    results.append(d)
                return results
            else:
                query = f"SELECT ts, metric, val, metadata FROM experiment_results WHERE experiment_id = ? {date_filter} ORDER BY ts DESC"
                rows = conn.execute(query, params).fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    if d['metadata']:
                        d['metadata'] = json.loads(d['metadata'])
                    results.append(d)
                return results

    def get_aggregated_metrics(self, experiment_id: str, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """
        Calculates high-level stats for the study within a specific range.
        """
        results = self.get_experiment_results(experiment_id, start_date, end_date)
        if not results or len(results) < 2:
            return {"correlation": 0.0, "count": len(results), "status": "Insufficient Data"}

        df = pd.DataFrame([
            {
                "ind": r['metadata'].get('ind_val'),
                "dep": r['metadata'].get('dep_val')
            } for r in results if r['metadata']
        ]).dropna()

        if len(df) < 2:
            return {"correlation": 0.0, "count": len(df), "status": "Insufficient Data"}

        correlation = df['ind'].corr(df['dep'])
        mae = (df['ind'] - df['dep']).abs().mean()

        return {
            "correlation": round(correlation, 3),
            "mae": round(mae, 2),
            "count": len(df),
            "status": "Significant" if abs(correlation) > 0.6 else "Weak Correlation"
        }
