import json
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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

    def get_experiment_results(self, experiment_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all recorded results for a specific experiment from 
        the experiment_results or research_results table.
        """
        self.db._ensure_initialized()
        import sqlite3
        with sqlite3.connect(self.db.working_db) as conn:
            conn.row_factory = sqlite3.Row
            
            if experiment_id == "EXP-NARC-001":
                query = "SELECT morning_date as ts, 'NARC_Score' as metric, independent_value as val, morning_date, independent_value as ind_val, dependent_value as dep_val, z_score_deviation, circadian_alignment FROM research_results WHERE experiment_id = ? ORDER BY morning_date DESC"
                rows = conn.execute(query, (experiment_id,)).fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    # Wrap in metadata for UI compatibility
                    d['metadata'] = {
                        "ind_val": d['ind_val'],
                        "dep_val": d['dep_val'],
                        "z_score": d['z_score_deviation'],
                        "circadian": d['circadian_alignment']
                    }
                    results.append(d)
                return results
            else:
                query = "SELECT ts, metric, val, metadata FROM experiment_results WHERE experiment_id = ? ORDER BY ts DESC"
                rows = conn.execute(query, (experiment_id,)).fetchall()
                results = []
                for row in rows:
                    d = dict(row)
                    if d['metadata']:
                        d['metadata'] = json.loads(d['metadata'])
                    results.append(d)
                return results

    def get_aggregated_metrics(self, experiment_id: str) -> Dict[str, Any]:
        """
        Calculates high-level stats (Pearson R, MAE) for the study.
        """
        results = self.get_experiment_results(experiment_id)
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
