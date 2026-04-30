import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.adapters.cgm import CGMProvider
from app.core.normalization import BiometricNormalizer
from app.engine.nar_evaluator import NAREvaluator
from app.engine.agent_orchestrator import AgentOrchestrator
from app.core.database import BiometricDatabase
import os
import sqlite3

class TestMetabolicCore(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_metabolic.sqlite"
        self.db = BiometricDatabase(db_path=self.db_path, working_db="/tmp/test_metabolic_working.sqlite")
        self.cgm_provider = CGMProvider()
        self.evaluator = NAREvaluator(db=self.db)
        self.orchestrator = AgentOrchestrator()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists("/tmp/test_metabolic_working.sqlite"):
            os.remove("/tmp/test_metabolic_working.sqlite")

    def test_cgm_transformation(self):
        """Verify CGM adapter transforms various JSON formats correctly."""
        payload = {
            "entries": [
                {"date": "2026-04-19T20:00:00Z", "sgv": 120, "direction": "SingleUp"},
                {"timestamp": "2026-04-19T20:05:00Z", "value": 125, "direction": "Flat"}
            ]
        }
        standardized = self.cgm_provider.transform_to_standard(payload)
        self.assertEqual(len(standardized), 2)
        self.assertEqual(standardized[0]['val'], 120.0)
        self.assertEqual(standardized[0]['metric'], "blood_glucose")
        self.assertEqual(standardized[0]['tag'], "SingleUp")
        self.assertEqual(standardized[1]['val'], 125.0)

    def test_glucose_velocity_and_trends(self):
        """Verify velocity calculation and trend labeling logic."""
        idx = pd.date_range(start="2026-04-19T20:00:00Z", periods=5, freq='5min')
        # Rapid rise: 100 -> 120 (4 mg/dL/min)
        data = {
            'blood_glucose': [100, 110, 120, 115, 110]
        }
        df = pd.DataFrame(data, index=idx)
        normalized = BiometricNormalizer.calculate_glucose_velocity(df)
        
        # Velocity at index 1: (110-100) / 5 min = 2.0 mg/dL/min
        self.assertAlmostEqual(normalized.iloc[1]['glucose_velocity'], 2.0)
        self.assertEqual(normalized.iloc[1]['glucose_trend'], "DoubleUp") # > 2.0 or >= 2.0 check
        
        # Velocity at index 3: (115-120) / 5 min = -1.0 mg/dL/min
        self.assertAlmostEqual(normalized.iloc[3]['glucose_velocity'], -1.0)
        self.assertEqual(normalized.iloc[3]['glucose_trend'], "SingleDown") # -1.0 is SingleDown per inclusive logic

    def test_nighttime_auc_calculation(self):
        """Verify AUC (Area Under Curve) calculation with a known shape."""
        # Simple rectangle: 100 mg/dL for 60 minutes = 6000 AUC
        idx = pd.date_range(start="2026-04-19T22:30:00Z", periods=61, freq='1min')
        df = pd.DataFrame({'val': [100.0] * 61}, index=idx)
        auc = self.evaluator.calculate_nighttime_metabolic_load(df)
        self.assertAlmostEqual(auc, 6000.0)
        
        # Triangle: 100 to 200 over 60 mins = 0.5 * (100+200) * 60 = 9000 AUC
        df_tri = pd.DataFrame({'val': np.linspace(100, 200, 61)}, index=idx)
        auc_tri = self.evaluator.calculate_nighttime_metabolic_load(df_tri)
        self.assertAlmostEqual(auc_tri, 9000.0)

    def test_metabolic_nudge_trigger_logic(self):
        """Verify agent triggers nudges only during late hours and high/rising glucose."""
        from io import StringIO
        import sys
        
        # Helper to capture stdout
        def capture_trigger(g, v, t, time_obj):
            captured_output = StringIO()
            sys.stdout = captured_output
            self.orchestrator.evaluate_metabolic_state(g, v, t, current_time=time_obj)
            sys.stdout = sys.__stdout__
            return captured_output.getvalue()

        # Case 1: Late, High, Rising -> Should Trigger
        trigger_time = datetime(2026, 4, 19, 21, 0, 0)
        output = capture_trigger(140.0, 2.5, "DoubleUp", trigger_time)
        self.assertIn("METABOLIC TRIGGER", output)
        
        # Case 2: Early, High, Rising -> Should NOT Trigger (Hour 14 < 20)
        early_time = datetime(2026, 4, 19, 14, 0, 0)
        output_early = capture_trigger(140.0, 2.5, "DoubleUp", early_time)
        self.assertNotIn("METABOLIC TRIGGER", output_early)
        
        # Case 3: Late, Low, Rising -> Should NOT Trigger (Glucose 110 < 130)
        output_low = capture_trigger(110.0, 1.5, "SingleUp", trigger_time)
        self.assertNotIn("METABOLIC TRIGGER", output_low)
        
        # Case 4: Late, High, Falling -> Should NOT Trigger (Trend "Flat")
        output_falling = capture_trigger(140.0, -1.5, "Flat", trigger_time)
        self.assertNotIn("METABOLIC TRIGGER", output_falling)

    def test_database_metabolic_persistence(self):
        """Verify metabolic_load is correctly persisted in research_results."""
        self.db._ensure_initialized()
        morning_date = datetime(2026, 4, 20).date()
        
        # Manual insert to verify column exists and works
        with sqlite3.connect(self.db.working_db) as conn:
            conn.execute("""
                INSERT INTO research_results 
                (experiment_id, morning_date, metabolic_load)
                VALUES (?, ?, ?)
            """, ("TEST-EXP", morning_date.isoformat(), 15000.5))
        
        # Verify retrieval
        with sqlite3.connect(self.db.working_db) as conn:
            row = conn.execute("SELECT metabolic_load FROM research_results WHERE experiment_id = 'TEST-EXP'").fetchone()
            self.assertEqual(row[0], 15000.5)

if __name__ == "__main__":
    unittest.main()
