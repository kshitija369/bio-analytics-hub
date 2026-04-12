import unittest
from datetime import datetime, timedelta, date
from app.core.database import SomaticDatabase
from app.engine.experiment_manager import ExperimentManager
from app.engine.dimension_repository import DimensionRepository
import os
import json

class TestExperimentEngine(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db_path = "Test_Somatic_Log.sqlite"
        self.test_working_db = "Test_Somatic_Log_Working.sqlite"
        
        for db in [self.test_db_path, self.test_working_db]:
            if os.path.exists(db):
                os.remove(db)
            
        self.db = SomaticDatabase(db_path=self.test_db_path, working_db=self.test_working_db)
        self.manager = ExperimentManager()
        self.manager.db = self.db
        self.manager.repo = DimensionRepository(db=self.db)

    def tearDown(self):
        for db in [self.test_db_path, self.test_working_db]:
            if os.path.exists(db):
                os.remove(db)

    def test_narc_evaluation_with_baseline(self):
        target_date = date.today()
        
        # 1. Insert 7 days of historical HRV baseline data
        # We need at least 7 days for the Z-score to calculate
        for i in range(1, 8):
            d = target_date - timedelta(days=i)
            # Window: 22:30 (d-1) to 07:30 (d)
            # Use fixed ISO format to match DB query expectations
            mock_ts = f"{(d - timedelta(days=1)).isoformat()}T23:30:00Z"
            # Add some variance so standard deviation is not zero
            val = 60.0 + (i % 3) 
            self.db.insert_biometrics([{
                "ts": mock_ts,
                "metric": "heart_rate_variability", "val": val,
                "unit": "ms", "source": "Mock", "tag": "baseline"
            }])

        # 2. Insert current night's high-res data (Independent)
        # 22:30 yesterday to 07:30 today
        current_night_start = datetime.combine(target_date - timedelta(days=1), datetime.min.time()).replace(hour=22, minute=30)
        
        # Add a "Dip" at 2:00 AM (early, good)
        dip_time = datetime.combine(target_date, datetime.min.time()).replace(hour=2, minute=0)
        
        mock_entries = [
            {"ts": (current_night_start + timedelta(hours=1)).isoformat(), "metric": "heart_rate_variability", "val": 70.0, "unit": "ms", "source": "Mock", "tag": "baseline"},
            {"ts": dip_time.isoformat(), "metric": "heart_rate", "val": 45.0, "unit": "bpm", "source": "Mock", "tag": "baseline"},
            {"ts": (dip_time + timedelta(hours=2)).isoformat(), "metric": "heart_rate", "val": 55.0, "unit": "bpm", "source": "Mock", "tag": "baseline"}
        ]
        self.db.insert_biometrics(mock_entries)

        # 3. Insert current Daily Score (Dependent)
        self.db.insert_biometrics([{
            "ts": f"{target_date.isoformat()}T00:00:00Z",
            "metric": "readiness_score", "val": 95.0,
            "unit": "score", "source": "Mock", "tag": "daily_insight"
        }])

        # 4. Run NARC Evaluation
        result = self.manager.evaluate_experiment_for_date("EXP-NARC-001", target_date)

        # 5. Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], "success")
        # HRV was 70 vs baseline of 60. Z-score should be positive.
        self.assertGreater(result['z_score'], 0)
        # Dip was at 2 AM (1 hour BEFORE 3 AM baseline), so offset should be -1.0
        self.assertEqual(result['circadian_alignment'], -1.0)

        # Check research_results table
        self.db._ensure_initialized()
        import sqlite3
        conn = sqlite3.connect(self.test_working_db)
        row = conn.execute("SELECT * FROM research_results WHERE experiment_id = ?", ("EXP-NARC-001",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], target_date.isoformat())
        self.assertEqual(row[3], 95.0) # dependent_value

if __name__ == "__main__":
    unittest.main()
