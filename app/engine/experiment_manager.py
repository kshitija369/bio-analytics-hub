import yaml
import os
import json
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from .dimension_repository import DimensionRepository
from app.core.database import SomaticDatabase

class ExperimentManager:
    """
    Coordinates experiment execution: loading protocols, gathering data,
    running calculations, and documenting results.
    """
    def __init__(self, config_path="config/experiments"):
        self.config_path = config_path
        self.repo = DimensionRepository()
        self.db = SomaticDatabase()

    def load_protocol(self, experiment_id: str) -> Dict[str, Any]:
        """Loads a YAML experiment protocol by ID."""
        if not os.path.exists(self.config_path):
             raise FileNotFoundError(f"Experiment config directory not found: {self.config_path}")

        for f in os.listdir(self.config_path):
            if f.endswith(".yaml"):
                file_path = os.path.join(self.config_path, f)
                with open(file_path, 'r') as stream:
                    proto = yaml.safe_load(stream)
                    if proto.get("id") == experiment_id:
                        return proto
        raise FileNotFoundError(f"Experiment protocol {experiment_id} not found in {self.config_path}")

    def evaluate_experiment_for_date(self, experiment_id: str, target_date: date):
        """
        Main entry point for daily experiment evaluation.
        """
        try:
            protocol = self.load_protocol(experiment_id)
        except Exception as e:
            print(f"--- [ExperimentManager] Failed to load protocol {experiment_id}: {e} ---")
            return None
        
        # Dispatch based on experiment type or ID
        if experiment_id == "EXP-001":
            return self._run_nocturnal_recovery_eval(protocol, target_date)
        elif experiment_id == "EXP-NARC-001":
            from .narc_evaluator import NARCEvaluator
            evaluator = NARCEvaluator(db=self.db)
            return evaluator.evaluate(target_date)
        else:
            print(f"--- [ExperimentManager] Unsupported experiment: {experiment_id} ---")
            return None

    def _run_nocturnal_recovery_eval(self, protocol: Dict[str, Any], target_date: date):
        """
        Evaluates EXP-001: Nocturnal Recovery Correlation.
        """
        print(f"--- [EXP-001] Running Nightly Recovery Evaluation for {target_date} ---")
        
        # A. Independent Variable Window (previous night)
        ind_vars = protocol.get('independent_variables', [])
        if not ind_vars:
            return None
            
        ind_var = ind_vars[0]
        window = ind_var.get('window', {})
        
        # From start_hour (yesterday) to end_hour (today)
        start_ts = datetime.combine(target_date - timedelta(days=1), datetime.min.time()).replace(hour=window.get('start_hour', 22))
        end_ts = datetime.combine(target_date, datetime.min.time()).replace(hour=window.get('end_hour', 8))
        
        dim_name = ind_var['dimension']
        avg_high_res = self.repo.get_window_summary(dim_name, start_ts, end_ts, agg_func='mean')
        
        if avg_high_res is None:
             print(f"  [EXP-001] Missing high-res data for {dim_name} between {start_ts} and {end_ts}")
             return None

        # B. Dependent Variable (Daily Score)
        dep_vars = protocol.get('dependent_variables', [])
        if not dep_vars:
            return None
            
        dep_var = dep_vars[0]
        dep_dim = dep_var['dimension']
        daily_score = self.repo.get_daily_aggregate(dep_dim, target_date)
        
        if daily_score is None:
             print(f"  [EXP-001] Missing daily score for {dep_dim} on {target_date}")
             return None

        # C. Calculate Correlation/Insights (over time)
        # For a single day, we store the matched pair for longitudinal analysis
        # Residual is a placeholder for more complex correlation logic later
        residual = daily_score - avg_high_res
        
        result_entry = {
            "experiment_id": protocol['id'],
            "ts": target_date.isoformat(),
            "metric": f"{dim_name}_vs_{dep_dim}",
            "val": residual,
            "metadata": json.dumps({
                "ind_val": avg_high_res,
                "dep_val": daily_score,
                "ind_dim": dim_name,
                "dep_dim": dep_dim,
                "name": protocol.get('name')
            })
        }
        
        self.db.insert_experiment_results([result_entry])
        print(f"  [EXP-001] Result saved: Residual={residual:.2f} (High-Res {dim_name}={avg_high_res:.1f}, Daily {dep_dim}={daily_score:.1f})")
        return result_entry
