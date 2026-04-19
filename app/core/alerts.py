import yaml
import operator
import os
import json
from datetime import datetime, timedelta
from .notifiers import send_to_watch
class BiometricTriggerEngine:
    _last_alerts = {}

    def __init__(self, config_path="config/triggers.yaml", db=None):
        print(f"--- [DEBUG] Initializing TriggerEngine with config: {config_path} ---")
        self.config_path = config_path
        self.config = self._load_config()
        self.db = db
        self.ops = {"gt": operator.gt, "lt": operator.lt, "eq": operator.eq}
        # DT4H-Sim: Agentic Configuration
        self.use_agent = os.environ.get("USE_AGENTIC_ALERTS", "false").lower() == "true"
        # Secular Witness: Event-Driven Configuration
        self.pubsub_topic = os.environ.get("GCP_PUBSUB_TOPIC", "biometric-anomalies")

    def _load_config(self):
        print(f"--- [DEBUG] Loading trigger config from: {self.config_path} ---")
        if not os.path.exists(self.config_path):
            print(f"--- [DEBUG] Config file NOT FOUND at {self.config_path} ---")
            return {'alerts': {'enabled': False}}
            
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"--- [DEBUG] Error loading trigger config: {e} ---")
            return {'alerts': {'enabled': False}}

    def evaluate_anomaly(self, metric_name: str, current_value: float, timestamp: datetime):
        """
        Phase 1: Perception.
        Calculates dynamic baseline (7-day moving avg) and publishes anomalies.
        """
        if not self.db:
            return

        # 1. Fetch 7-day baseline
        start_7d = timestamp - timedelta(days=7)
        historical = self.db.get_data(start_7d, timestamp, metrics=[metric_name])

        if not historical or len(historical) < 10: # Minimum sample size
            return

        vals = [r['val'] for r in historical]
        moving_avg = sum(vals) / len(vals)

        # 2. Check for Anomaly (e.g. HRV drop > 20%)
        if metric_name == "heart_rate_variability":
            deviation = ((current_value - moving_avg) / moving_avg) * 100
            if deviation < -20: # 20% Drop
                self._publish_anomaly(metric_name, current_value, moving_avg, deviation, timestamp)

    def _publish_anomaly(self, metric, val, baseline, deviation, ts):
        """Publishes event to Pub/Sub for the Orchestrator to process."""
        print(f"--- [Perception] Anomaly Detected: {metric} is {deviation:.1f}% below baseline ---")

        anomaly_event = {
            "metric": metric,
            "val": val,
            "baseline": baseline,
            "deviation": round(deviation, 2),
            "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        }

        # Simulation: In production, use google.cloud.pubsub_v1
        print(f"--- [Perception] Publishing to {self.pubsub_topic}: {json.dumps(anomaly_event)} ---")

        # If agentic alerts are still in legacy mode, we might also trigger the nudge here
        # but for Secular Witness, the Orchestrator (Worker) handles it.

    def evaluate(self, metric_name, current_value, timestamp=None):
        if not self.config.get('alerts', {}).get('enabled', False):
            return

        # 1. Freshness Check: Don't trigger for data older than 15 minutes
        if timestamp:
            if isinstance(timestamp, str):
                try:
                    # Handle both ISO formats
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    return
            else:
                dt = timestamp
            
            # If data is older than 15 minutes, skip alert (it's historical)
            # Use naive comparison since we converted Z to offset above, or just ensure both are UTC
            if (datetime.now() - dt.replace(tzinfo=None)).total_seconds() > 900:
                return

        for rule in self.config.get('thresholds', []):
            if rule['metric'] == metric_name:
                op_func = self.ops.get(rule['condition'])
                if not op_func:
                    continue
                
                if op_func(current_value, rule['value']):
                    if self._is_cooldown_active(rule['id']):
                        continue

                    if self.use_agent:
                        self._trigger_agentic_nudge(rule, current_value)
                    else:
                        self._send_static_alert(rule, current_value)

    def _send_static_alert(self, rule, current_value):
        """Original threshold-based haptic alert."""
        payload = rule['payload']
        msg = payload['message'].format(value=current_value)
        title = payload['title']
        priority = payload.get('priority', 0)
        
        if send_to_watch(title, msg, priority):
            self._last_alerts[rule['id']] = datetime.now()

    def _trigger_agentic_nudge(self, rule, current_value):
        """
        DT4H-Sim: Agentic Workflow.
        Passes context to Gemini to generate an explainable 'Care Nudge'.
        """
        print(f"--- [Agentic Hub] Evaluating context for {rule['id']} (Val: {current_value}) ---")
        
        # Mock Gemini Response (In real use, we'd use Vertex AI here)
        nudge = "Elevated heart rate detected. Consider a 2-minute physiological sigh to reset your autonomic balance."
        
        title = "AI Performance Nudge"
        if send_to_watch(title, nudge, priority=1):
            self._last_alerts[rule['id']] = datetime.now()
            print(f"  [Agentic Hub] Nudge sent: {nudge}")

    def _is_cooldown_active(self, rule_id):
        last_time = self._last_alerts.get(rule_id)
        if not last_time:
            return False
            
        cooldown = timedelta(minutes=self.config['alerts'].get('cooldown_minutes', 30))
        return datetime.now() < (last_time + cooldown)
