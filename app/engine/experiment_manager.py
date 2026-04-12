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
        if experiment_id == "EXP-NARC-001":
            from .narc_evaluator import NARCEvaluator
            evaluator = NARCEvaluator(db=self.db)
            return evaluator.evaluate(target_date)
        else:
            print(f"--- [ExperimentManager] Unsupported experiment: {experiment_id} ---")
            return None
