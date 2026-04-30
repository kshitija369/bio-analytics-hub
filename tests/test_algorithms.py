import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.engine.simulation_engine import SimulationEngine
from app.engine.nar_evaluator import NAREvaluator
from app.core.database import BiometricDatabase
import os

class TestExperimentalAlgorithms(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine()
        # Mock history data: 1 week of steady metrics
        idx = pd.date_range(start="2026-04-01", end="2026-04-07", freq='1h')
        self.history = pd.DataFrame(index=idx)
        self.history['heart_rate'] = 60.0
        self.history['heart_rate_variability'] = 50.0

    def test_simulation_stressor_impact(self):
        """Stressors should decrease HRV and Readiness, increase HR."""
        events = [{"event": "alcohol", "drinks": 3}, {"event": "meal", "time": "22:30"}]
        result = self.engine.predict_next_24h(self.history, events)
        
        self.assertEqual(result['status'], 'success')
        # Stressors should drop readiness below baseline (80)
        self.assertLess(result['predicted_readiness'], 80.0)
        # Alcohol (3*6=18) + Late Meal (8) = 26 HRV drop from baseline (50)
        self.assertAlmostEqual(result['predicted_hrv_avg'], 50.0 - 26.0, delta=0.1)
        
        # Check time-series directionality
        df = pd.DataFrame(result['time_series'])
        self.assertGreater(df['heart_rate'].mean(), 60.0)
        print(f"✅ Stressor Test: Readiness {result['predicted_readiness']}, HRV {result['predicted_hrv_avg']}")

    def test_simulation_buffer_impact(self):
        """Buffers should increase HRV and Readiness, decrease HR."""
        events = [{"event": "nature", "duration_mins": 60}, {"event": "cold_exposure"}]
        result = self.engine.predict_next_24h(self.history, events)
        
        self.assertEqual(result['status'], 'success')
        # Buffers should raise readiness above baseline (80)
        self.assertGreater(result['predicted_readiness'], 80.0)
        # Nature (60/15*1.5=6) + Cold (5) = 11 HRV gain from baseline (50)
        self.assertAlmostEqual(result['predicted_hrv_avg'], 50.0 + 11.0, delta=0.1)
        
        # Check time-series directionality
        df = pd.DataFrame(result['time_series'])
        self.assertLess(df['heart_rate'].mean(), 60.0)
        print(f"✅ Buffer Test: Readiness {result['predicted_readiness']}, HRV {result['predicted_hrv_avg']}")

    def test_compounding_vectors(self):
        """Stacking stressors and buffers should show net sum effect."""
        # 3 drinks (-24 readiness) + Nature Fix (+8 readiness) = -16 from baseline (80) -> 64
        events = [{"event": "alcohol", "drinks": 3}, {"event": "nature", "duration_mins": 60}]
        result = self.engine.predict_next_24h(self.history, events)
        
        self.assertAlmostEqual(result['predicted_readiness'], 64.0, delta=0.1)
        print(f"✅ Compounding Test: Net Readiness {result['predicted_readiness']}")

    def test_hammock_curve_dip_shift(self):
        """Stressors should shift the heart rate dip later in the night."""
        # 1. Healthy Baseline (No events)
        res_baseline = self.engine.predict_next_24h(self.history, [])
        df_base = pd.DataFrame(res_baseline['time_series'])
        dip_idx_base = df_base['heart_rate'].idxmin()
        
        # 2. Heavy Stressor (Late meal + Alcohol)
        events = [{"event": "alcohol", "drinks": 4}, {"event": "meal", "time": "23:00"}]
        res_stressed = self.engine.predict_next_24h(self.history, events)
        df_stress = pd.DataFrame(res_stressed['time_series'])
        dip_idx_stress = df_stress['heart_rate'].idxmin()
        
        # Stressed dip should be later (higher index) than baseline
        self.assertGreater(dip_idx_stress, dip_idx_base)
        print(f"✅ Hammock Dip Test: Baseline Dip @ {dip_idx_base}, Stressed Dip @ {dip_idx_stress}")

    def test_metabolic_simulation(self):
        """High-carb meals should trigger a glucose spike in the simulation."""
        # Add baseline glucose to history
        self.history['blood_glucose'] = 90.0
        
        # High-carb meal (+80 spike)
        events = [{"event": "meal", "carbs": 100}]
        result = self.engine.predict_next_24h(self.history, events)
        
        self.assertEqual(result['status'], 'success')
        self.assertAlmostEqual(result['predicted_glucose_peak'], 170.0, delta=5.0)
        
        # Check time-series for peak
        df = pd.DataFrame(result['time_series'])
        self.assertGreater(df['blood_glucose'].max(), 160.0)
        print(f"✅ Metabolic Test: Glucose Peak {result['predicted_glucose_peak']}")

if __name__ == "__main__":
    unittest.main()
