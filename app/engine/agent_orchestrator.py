import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.domain.dimension_repository import DimensionRepository
from .registry import AgentToolRegistry
from app.core.notifiers import send_bidirectional_nudge
from app.adapters.home_assistant import HomeAssistantAdapter
from app.core.provenance import ProvenanceLogger

class AgentOrchestrator:
    """
    The 'Secular Witness' Agent Orchestrator.
    Subscribes to biometric anomaly events and uses Gemini to 
    evaluate context and trigger autonomous actions.
    """
    def __init__(self):
        self.project_id = os.environ.get("GCP_PROJECT_ID")
        self.subscription_id = os.environ.get("GCP_PUBSUB_SUBSCRIPTION", "biometric-anomaly-sub")
        self.model_name = "gemini-1.5-pro-002"
        self.repo = DimensionRepository()
        self.tool_registry = AgentToolRegistry()
        self.ha = HomeAssistantAdapter()
        self.provenance = ProvenanceLogger()

    def sync_circadian_lighting(self):
        """
        PoC: Syncs home lighting to Satchin Panda's light exposure rules.
        """
        hour = datetime.now().hour
        print(f"--- [Agent] Syncing Circadian Lighting (Hour: {hour}) ---")
        
        # Satchin Panda Logic: Bright/Cool in morning, Warm/Dim at night
        if 6 <= hour < 10:
            target_kelvin = 5000 # Daylight (Alertness)
        elif 10 <= hour < 18:
            target_kelvin = 4000 # Neutral
        else:
            target_kelvin = 2000 # Warm (Melatonin support)

        # In production, pull entity_id from user config
        self.ha.set_light_kelvin("light.bedroom", target_kelvin)
        print(f"  [Agent] Circadian Light Sync Complete: {target_kelvin}K")

    def evaluate_metabolic_state(self, current_glucose: float, velocity: float, trend: str, current_time: Optional[datetime] = None):
        """
        Monitors for late-night metabolic excursions and triggers 
        preventative 'Metabolic Clearance' nudges.
        """
        now = current_time or datetime.now()
        hour = now.hour
        
        print(f"--- [Agent] Evaluating Metabolic State: {current_glucose} mg/dL ({trend}) ---")
        
        # Trigger: Late evening (after 8 PM), high glucose, and rising
        if hour >= 20 and current_glucose > 130 and "Up" in trend:
            nudge_msg = (
                f"Your glucose is rising late ({current_glucose} mg/dL, {trend}). "
                "To protect your autonomic recovery and tomorrow's focus, "
                "take a 15-minute walk now to clear this spike."
            )
            print(f"  [Agent] METABOLIC TRIGGER: {nudge_msg}")
            
            # Action & Provenance
            self._execute_action(nudge_msg)
            self.provenance.log_decision(
                agent_id="Metabolic-Guardian-001",
                context={"glucose": current_glucose, "trend": trend, "hour": hour},
                reasoning="Late glycemic load detected. High risk for autonomic suppression.",
                action="Preventative Metabolic Nudge"
            )

    def start_listening(self):
        """
        Initializes the Pub/Sub subscriber and processes anomaly events.
        """
        print(f"--- [Secular Witness] Agent Orchestrator starting on {self.subscription_id} ---")
        
        # Simulation: In production, this would be an async subscriber.listen() loop
        while True:
            # print("--- [Agent] Polling for anomalies... ---")
            time.sleep(60) 

    def process_anomaly(self, anomaly_data: dict):
        """
        Phase 2: Reasoning.
        Contextualizes the anomaly and generates a 'Care Nudge'.
        """
        print(f"--- [Agent] Processing Anomaly: {anomaly_data['metric']} drop detected ---")
        
        # 1. Context Assembly (Chain-of-Thought)
        context = self._assemble_context(anomaly_data)
        
        # 2. Reasoning (Gemini call)
        reasoning = self._get_gemini_reasoning(context)
        
        # 3. Action (Phase 3) & Provenance Logging
        if reasoning and "Toxic Stress" in reasoning:
            self._execute_action(reasoning)
            self.provenance.log_decision(
                agent_id="Secular-Witness-001",
                context=anomaly_data,
                reasoning=reasoning,
                action="Interactive Care Nudge"
            )
        else:
            print(f"--- [Agent] No action required: {reasoning} ---")
            self.provenance.log_decision(
                agent_id="Secular-Witness-001",
                context=anomaly_data,
                reasoning=reasoning,
                action="None"
            )

    def _assemble_context(self, anomaly: dict) -> str:
        """
        Gathers recent time-series and experimental context for the LLM.
        """
        ts = datetime.fromisoformat(anomaly['timestamp'])
        # Pull last 4 hours of Heart Rate and HRV
        history = self.repo.get_dimension_data("HeartRate", ts - timedelta(hours=4), ts)
        
        context_block = {
            "anomaly": anomaly,
            "recent_history": history.tail(10).to_dict() if not history.empty else "No history available",
            "study_id": "EXP-SRI-001",
            "persona": "Adlerian/Longevity Coach"
        }
        return json.dumps(context_block, indent=2)

    def _get_gemini_reasoning(self, context_json: str) -> Optional[str]:
        """
        Performs Chain-of-Thought reasoning to evaluate if the drop is 'Toxic Stress'
        or 'Good Difficulty'.
        """
        print(f"--- [Agent] Analyzing context with Gemini {self.model_name} ---")
        
        # Mock logic based on the simulated persona
        context = json.loads(context_json)
        deviation = abs(context['anomaly']['deviation'])
        
        if deviation > 30:
            return "Toxic Stress detected. Immediate Care Nudge: Suggested 15-minute nature walk to reset cortisol."
        else:
            return "Acceptable physiological strain. No intervention required."

    def _execute_action(self, nudge: str):
        """
        Phase 3 logic: Execution of autonomous actions with HITL oversight.
        """
        print(f"--- [Agent] Formulating Action Workflow for: {nudge} ---")
        
        # 1. Register tools with the model
        # tools = self.tool_registry.get_all_tool_definitions()
        
        # 2. Simulation: Trigger Bidirectional Notification for User Confirmation
        send_bidirectional_nudge(
            title="Performance Intervention Suggested",
            message=nudge,
            callback_url=f"https://{os.environ.get('GCP_REGION', 'us-central1')}-run.app/api/v1/agent/callback"
        )
        print(f"--- [Agent] Action Staged: Awaiting User Approval ---")

if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.start_listening()
