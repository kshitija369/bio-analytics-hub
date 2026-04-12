import os
import yaml
from typing import List, Dict, Any, Optional

class ExperimentRegistry:
    """
    Scans the config/experiments directory and returns structured 
    metadata for the Research Hub.
    """
    def __init__(self, config_path="config/experiments"):
        self.config_path = config_path

    def get_all_experiments(self) -> List[Dict[str, Any]]:
        """Returns metadata for all defined experiments."""
        experiments = []
        if not os.path.exists(self.config_path):
            return experiments

        for f in os.listdir(self.config_path):
            if f.endswith(".yaml"):
                try:
                    with open(os.path.join(self.config_path, f), 'r') as stream:
                        proto = yaml.safe_load(stream)
                        if proto:
                            # Add some "derived" status for the UI hub
                            proto['status'] = "Active" # Placeholder logic
                            experiments.append(proto)
                except Exception as e:
                    print(f"--- [Registry] Error loading {f}: {e} ---")
        return experiments

    def get_experiment_by_id(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Finds a specific experiment protocol."""
        all_exp = self.get_all_experiments()
        for e in all_exp:
            if e.get('id') == experiment_id:
                return e
        return None
