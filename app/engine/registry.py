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

class AgentToolRegistry:
    """
    DT4H-Sim/Secular-Witness: Phase 3.
    Registers external API definitions as function-calling tools for Gemini.
    """
    def __init__(self):
        self.tools = {
            "create_calendar_block": {
                "name": "create_calendar_block",
                "description": "Stages a calendar invitation for a suggested recovery practice.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "e.g. 15-minute Nature Walk"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "duration_mins": {"type": "integer"}
                    },
                    "required": ["title", "start_time"]
                }
            },
            "pause_slack_notifications": {
                "name": "pause_slack_notifications",
                "description": "Silences work notifications to protect a physiological recovery window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "duration_mins": {"type": "integer", "description": "Minutes to snooze"}
                    },
                    "required": ["duration_mins"]
                }
            },
            "set_home_lighting": {
                "name": "set_home_lighting",
                "description": "Syncs home light temperature (Kelvin) to support circadian alignment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kelvin": {"type": "integer", "description": "Target Kelvin (2000 for night, 5000 for morning)"}
                    },
                    "required": ["kelvin"]
                }
            },
            "optimize_sleep_temp": {
                "name": "optimize_sleep_temp",
                "description": "Lowers home temperature to support deep sleep architecture.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_temp": {"type": "number", "description": "Target temperature in Fahrenheit"}
                    },
                    "required": ["target_temp"]
                }
            }
        }

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        return list(self.tools.values())
