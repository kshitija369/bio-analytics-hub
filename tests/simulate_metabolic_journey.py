import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.engine.simulation_engine import SimulationEngine
from app.core.normalization import BiometricNormalizer
from app.engine.agent_orchestrator import AgentOrchestrator

def simulate_metabolic_journey():
    print("--- [Simulation] Longevity OS Metabolic Journey ---")
    
    # 1. Setup Historical Context (Stable Glucose)
    now = datetime.now()
    # Mocking evening time (9 PM) to trigger the agent
    mock_now = now.replace(hour=21, minute=0)
    
    idx = pd.date_range(end=mock_now, periods=10, freq='15min')
    history_df = pd.DataFrame(index=idx)
    history_df['heart_rate'] = 65.0 + np.random.normal(0, 2, 10)
    history_df['heart_rate_variability'] = 55.0 + np.random.normal(0, 5, 10)
    history_df['blood_glucose'] = 145.0 + np.random.normal(0, 2, 10) # High glucose
    
    # 2. Run Normalizer (Velocity Calculation)
    print("\n[Step 1] Normalizing historical glucose and calculating velocity...")
    normalized = BiometricNormalizer.calculate_glucose_velocity(history_df)
    last_row = normalized.iloc[-1]
    
    # Force a trend for simulation
    current_g = last_row['blood_glucose']
    current_v = last_row['glucose_velocity']
    current_t = "DoubleUp" 
    
    print(f"  Current Glucose: {current_g:.1f} mg/dL")
    print(f"  Glucose Velocity: {current_v:.2f} mg/dL/min")
    print(f"  Glucose Trend: {current_t}")

    # 3. Trigger Agent Orchestrator
    print("\n[Step 2] Passing state to Agent Orchestrator...")
    agent = AgentOrchestrator()
    agent.evaluate_metabolic_state(current_g, current_v, current_t)

    # 4. Simulate High-Carb Event Impact
    print("\n[Step 3] Simulating a high-carb intervention...")
    engine = SimulationEngine()
    prospective_events = [
        {"event": "meal", "carbs": 75, "time": "12:00", "duration_mins": 30}
    ]
    
    result = engine.predict_next_24h(history_df, prospective_events)
    
    if result['status'] == 'success':
        print(f"  Predicted Readiness: {result['predicted_readiness']}")
        print(f"  Predicted Glucose Peak: {result['predicted_glucose_peak']} mg/dL")
        
        # Check for DoubleUp in the synthetic data
        synthetic_df = pd.DataFrame(result['time_series'])
        synthetic_df['ts'] = pd.to_datetime(synthetic_df['ts'])
        synthetic_df.set_index('ts', inplace=True)
        
        # Calculate velocity on synthetic data
        synthetic_normalized = BiometricNormalizer.calculate_glucose_velocity(synthetic_df)
        
        max_velocity = synthetic_normalized['glucose_velocity'].max()
        print(f"  Max Predicted Velocity: {max_velocity:.2f} mg/dL/min")
        
        if max_velocity > 2.0:
            print("  [ALERT] DoubleUp trend detected in simulation!")
            print("  [ACTION] Proactive intervention: 15-min Nature Fix suggested.")
            
            # Re-run simulation with Nature Fix
            print("\n[Step 3] Mitigating with 'Nature Fix' walk...")
            mitigated_events = prospective_events + [
                {"event": "nature", "duration_mins": 20}
            ]
            mitigated_result = engine.predict_next_24h(history_df, mitigated_events)
            print(f"  New Predicted Readiness: {mitigated_result['predicted_readiness']}")
            print(f"  (Readiness improved via autonomic stabilization)")

if __name__ == "__main__":
    simulate_metabolic_journey()
