import yaml
import operator
import os
from datetime import datetime, timedelta
from .notifiers import send_to_watch

class SomaticTriggerEngine:
    _last_alerts = {}

    def __init__(self, config_path="config/triggers.yaml"):
        print(f"--- [DEBUG] Initializing TriggerEngine with config: {config_path} ---")
        # Allow specifying config_path for testing or flexibility
        if not os.path.exists(config_path):
            print(f"--- [DEBUG] Config file NOT FOUND at {config_path} ---")
            self.config = {'alerts': {'enabled': False}}
            return
            
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            print("--- [DEBUG] Trigger config loaded successfully ---")
        except Exception as e:
            print(f"--- [DEBUG] Error loading trigger config: {e} ---")
            self.config = {'alerts': {'enabled': False}}
            
        self.ops = {"gt": operator.gt, "lt": operator.lt, "eq": operator.eq}

    def evaluate(self, metric_name, current_value):
        if not self.config.get('alerts', {}).get('enabled', False):
            return

        for rule in self.config.get('thresholds', []):
            if rule['metric'] == metric_name:
                op_func = self.ops.get(rule['condition'])
                if not op_func:
                    continue
                
                if op_func(current_value, rule['value']):
                    if self._is_cooldown_active(rule['id']):
                        continue

                    # Send the alert
                    payload = rule['payload']
                    msg = payload['message'].format(value=current_value)
                    title = payload['title']
                    priority = payload.get('priority', 0)
                    
                    if send_to_watch(title, msg, priority):
                        self._last_alerts[rule['id']] = datetime.now()

    def _is_cooldown_active(self, rule_id):
        last_time = self._last_alerts.get(rule_id)
        if not last_time:
            return False
            
        cooldown = timedelta(minutes=self.config['alerts'].get('cooldown_minutes', 30))
        return datetime.now() < (last_time + cooldown)
