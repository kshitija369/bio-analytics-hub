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

    def test_nocturnal_recovery_evaluation(self):
        target_date = date.today()
        
        # 1. Insert Mock High-Res Data (Independent Variable: HRV)
        # 10 PM yesterday to 8 AM today
        start_ts = datetime.combine(target_date - timedelta(days=1), datetime.min.time()).replace(hour=22)
        
        mock_entries = []
        for i in range(600): # 10 hours * 60 mins
            ts = (start_ts + timedelta(minutes=i)).isoformat()
            mock_entries.append({
                "ts": ts, "metric": "heart_rate_variability", "val": 50.0 + (i % 10),
                "unit": "ms", "source": "MockWatch", "tag": "baseline"
            })
        self.db.insert_biometrics(mock_entries)
        
        # 2. Insert Mock Daily Score (Dependent Variable: Readiness)
        self.db.insert_biometrics([{
            "ts": f"{target_date.isoformat()}T00:00:00Z",
            "metric": "readiness_score",
            "val": 85.0,
            "unit": "score",
            "source": "MockRing",
            "tag": "daily_insight"
        }])
        
        # 3. Run Evaluation
        result = self.manager.evaluate_experiment_for_date("EXP-001", target_date)
        
        # 4. Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['experiment_id'], "EXP-001")
        
        # Check database directly
        self.db._ensure_initialized()
        import sqlite3
        conn = sqlite3.connect(self.test_working_db)
        row = conn.execute("SELECT * FROM experiment_results WHERE experiment_id = ?", ("EXP-001",)).fetchone()
        self.assertIsNotNone(row)
        metadata = json.loads(row[4])
        self.assertEqual(metadata['dep_val'], 85.0)
        self.assertAlmostEqual(metadata['ind_val'], 54.5, delta=1.0) # Mean of 50-59

if __name__ == "__main__":
    unittest.main()
