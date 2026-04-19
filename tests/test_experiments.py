import unittest
from datetime import datetime, timedelta, date
from app.core.database import BiometricDatabase
from app.engine.experiment_manager import ExperimentManager
from app.domain.dimension_repository import DimensionRepository
import os
import json

class TestExperimentEngine(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db_path = "Test_Bio_Analytics_Hub.sqlite"
        self.test_working_db = "Test_Bio_Analytics_Hub_Working.sqlite"
        
        for db in [self.test_db_path, self.test_working_db]:
            if os.path.exists(db):
                os.remove(db)
            
        self.db = BiometricDatabase(db_path=self.test_db_path, working_db=self.test_working_db)
        self.manager = ExperimentManager()
        self.manager.db = self.db
        self.repo = DimensionRepository(db=self.db)
        self.manager.repo = self.repo

    def tearDown(self):
        for db in [self.test_db_path, self.test_working_db]:
            if os.path.exists(db):
                os.remove(db)

    def test_sri_evaluation_with_baseline(self):
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

        # 4. Run SRI Evaluation
        result = self.manager.evaluate_experiment_for_date("EXP-SRI-001", target_date)

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
        row = conn.execute("SELECT * FROM research_results WHERE experiment_id = ?", ("EXP-SRI-001",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], target_date.isoformat())
        self.assertEqual(row[3], 95.0) # dependent_value

    def test_dimension_repo_naive_conversion(self):
        # Insert timezone-aware data
        ts_aware = "2026-04-11T12:00:00+00:00"
        self.db.insert_biometrics([{
            "ts": ts_aware, "metric": "heart_rate", "val": 60.0,
            "unit": "bpm", "source": "AwareSource", "tag": "test"
        }])
        
        start = datetime(2026, 4, 11, 0, 0)
        end = datetime(2026, 4, 11, 23, 59)
        df = self.repo.get_dimension_data("HeartRate", start, end)
        
        # Verify index is naive
        self.assertIsNone(df.index.tz)
        self.assertEqual(df.index[0].hour, 12)

    def test_upsert_logic(self):
        ts = "2026-04-11T12:00:00Z"
        # 1. First insert
        self.db.insert_biometrics([{
            "ts": ts, "metric": "heart_rate", "val": 60.0,
            "unit": "bpm", "source": "Mock", "tag": "v1"
        }])
        
        # 2. Re-insert same key with different value (UPSERT)
        self.db.insert_biometrics([{
            "ts": ts, "metric": "heart_rate", "val": 75.0,
            "unit": "bpm", "source": "Mock", "tag": "v2"
        }])
        
        # 3. Check record count and value
        self.db._ensure_initialized()
        import sqlite3
        conn = sqlite3.connect(self.test_working_db)
        rows = conn.execute("SELECT val, tag FROM biometrics WHERE ts = ? AND metric = 'heart_rate'", (ts,)).fetchall()
        
        self.assertEqual(len(rows), 1) # Should be exactly one due to UNIQUE constraint
        self.assertEqual(rows[0][0], 75.0)
        self.assertEqual(rows[0][1], "v2")

if __name__ == "__main__":
    unittest.main()
