import yaml
import os
import json
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from app.domain.dimension_repository import DimensionRepository
from app.core.database import BiometricDatabase

# New: BigQuery for explainability (PA-XDT)
# from google.cloud import bigquery

class ExperimentManager:
    """
    Coordinates experiment execution: loading protocols, gathering data,
    running calculations, and documenting results.
    """
    def __init__(self, config_path="config/experiments"):
        self.config_path = config_path
        self.repo = DimensionRepository()
        self.db = BiometricDatabase()

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
        if experiment_id == "EXP-NAR-001":
            from .nar_evaluator import NAREvaluator
            evaluator = NAREvaluator(db=self.db)
            res = evaluator.evaluate(target_date)
            if res and res.get('status') == 'success':
                self._log_provenance(experiment_id, res)
            return res
        else:
            print(f"--- [ExperimentManager] Unsupported experiment: {experiment_id} ---")
            return None

    def _log_provenance(self, experiment_id: str, results: Dict[str, Any]):
        """
        DT4H-Sim: Provenance Logging (PA-XDT).
        Writes the 'paper trail' of the inference to BigQuery.
        """
        print(f"--- [Provenance] Logging trace for {experiment_id} ---")
        # In real use, this would stream to BigQuery
        trace = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now().isoformat(),
            "results_summary": results,
            "version": "DT4H-Sim-1.1"
        }
        # Simulated BigQuery Insert
        pass
