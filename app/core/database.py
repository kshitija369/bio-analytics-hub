import sqlite3
import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# New: GCP Healthcare API imports (deferred to keep local mode fast)
# from google.cloud import healthcare_v1

DB_FILE = "Bio_Analytics_Hub.sqlite" # Local fallback

class BiometricDatabase:
    def __init__(self, db_path=None, working_db=None):
        self._db_path_override = db_path
        self._working_db_override = working_db
        self._initialized = False
        
        # Two-Tier Strategy:
        # 1. working_db: Local /tmp file for high-speed, no-lock R/W
        # 2. persistent_db: The FUSE mount at /app/data for backup
        self.working_db = working_db or "/tmp/Bio_Analytics_Hub_Working.sqlite"
        self.persistent_db = "/app/data/Bio_Analytics_Hub.sqlite"
        
        # New: DT4H-Sim FHIR Configuration
        self.use_fhir = os.environ.get("USE_FHIR", "false").lower() == "true"
        self.fhir_store_path = os.environ.get("GCP_FHIR_STORE_PATH") # e.g. projects/P/locations/L/datasets/D/fhirStores/S

    def _ensure_initialized(self):
        if self._initialized:
            return

        # 1. Setup Persistent Path
        if self._db_path_override:
            self.persistent_db = self._db_path_override
        elif not os.path.exists("/app/data"):
            # If not on GCP, use local DB as the working DB directly
            if not self._working_db_override:
                self.working_db = DB_FILE
            self.persistent_db = DB_FILE

        print(f"--- [DB DEBUG] Working: {self.working_db}, Persistent: {self.persistent_db} ---")
        if self.use_fhir:
            print(f"--- [DT4H-Sim] FHIR Mode Enabled: {self.fhir_store_path} ---")

        # 2. Restore from Persistence if available (and on GCP)
        if self.working_db != self.persistent_db and os.path.exists(self.persistent_db):
            print(f"--- [DB DEBUG] Restoring from {self.persistent_db} ---")
            try:
                shutil.copy2(self.persistent_db, self.working_db)
                print("--- [DB DEBUG] Restore successful ---")
            except Exception as e:
                print(f"--- [DB DEBUG] Restore failed: {e} ---")

        # 3. Initialize the working DB schema
        try:
            print(f"--- [DB DEBUG] Opening SQLite at {self.working_db} ---")
            with sqlite3.connect(self.working_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS biometrics (
                        ts TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        val REAL NOT NULL,
                        unit TEXT,
                        source TEXT,
                        tag TEXT,
                        UNIQUE(ts, metric, source)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS experiment_results (
                        experiment_id TEXT NOT NULL,
                        ts TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        val REAL NOT NULL,
                        metadata TEXT,
                        UNIQUE(experiment_id, ts, metric)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS research_results (
                        experiment_id TEXT NOT NULL,
                        morning_date TEXT NOT NULL,
                        independent_value REAL,
                        dependent_value REAL,
                        z_score_deviation REAL,
                        circadian_alignment REAL,
                        subjective_rating INTEGER,
                        PRIMARY KEY (experiment_id, morning_date)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON biometrics(ts)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_metric ON biometrics(metric)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_id ON experiment_results(experiment_id)")
            print("--- [DB DEBUG] Working database initialized successfully ---")
            self.db_path = self.working_db
            self._initialized = True
        except Exception as e:
            print(f"--- [DB DEBUG] CRITICAL INITIALIZATION ERROR: {e} ---")
            raise e

    def _flush_to_persistence(self):
        """Backs up the local working DB to the persistent FUSE mount."""
        # Only flush if the mount directory exists and we are in two-tier mode
        if self.working_db != self.persistent_db and os.path.exists("/app/data"):
            print(f"--- [DB DEBUG] Flushing working DB to persistence: {self.persistent_db} ---")
            try:
                shutil.copy2(self.working_db, self.persistent_db)
                print("--- [DB DEBUG] Flush successful ---")
            except Exception as e:
                print(f"--- [DB DEBUG] Flush FAILED: {e} ---")

    def insert_biometrics(self, entries: List[Dict[str, Any]]):
        self._ensure_initialized()
        
        # 1. SQL Sync (Legacy support/Local cache)
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO biometrics (ts, metric, val, unit, source, tag)
                VALUES (:ts, :metric, :val, :unit, :source, :tag)
            """, entries)
        self._flush_to_persistence()

        # 2. FHIR Sync (Clinical Grade DT4H-Sim)
        if self.use_fhir:
            self._ingest_to_fhir(entries)

    def _ingest_to_fhir(self, entries: List[Dict[str, Any]]):
        """
        Translates raw biometric entries into FHIR R4 Observations
        and simulates streaming to the GCP Healthcare API.
        """
        print(f"--- [DT4H-Sim] Constructing {len(entries)} FHIR Observations ---")
        
        observations = []
        for entry in entries:
            # Construct a standard FHIR R4 Observation resource
            obs = {
                "resourceType": "Observation",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "vital-signs",
                                "display": "Vital Signs"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": entry.get("loinc", "unknown"),
                            "display": entry.get("metric")
                        }
                    ]
                },
                "subject": {
                    "reference": "Patient/DT4H-Sim-Avatar-001"
                },
                "effectiveDateTime": entry.get("ts"),
                "valueQuantity": {
                    "value": entry.get("val"),
                    "unit": entry.get("unit"),
                    "system": "http://unitsofmeasure.org",
                    "code": entry.get("unit")
                },
                "device": {
                    "display": entry.get("source")
                }
            }
            observations.append(obs)
        
        # Simulation: Print the first observation for verification
        if observations:
            print(f"--- [DT4H-Sim] Sample Observation Created: {json.dumps(observations[0], indent=2)} ---")
        
        # Future: Stream to GCP Healthcare API using healthcare_v1
        # fhir_client.create_resource(parent=self.fhir_store_path, type="Observation", body=obs)

    def insert_experiment_results(self, entries: List[Dict[str, Any]]):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO experiment_results (experiment_id, ts, metric, val, metadata)
                VALUES (:experiment_id, :ts, :metric, :val, :metadata)
            """, entries)
        self._flush_to_persistence()

    def get_data(self, start_time: datetime, end_time: datetime, metrics: List[str] = None) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        
        query = "SELECT ts, metric, val, unit, source, tag FROM biometrics WHERE ts BETWEEN ? AND ?"
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if metrics:
            query += " AND metric IN ({})".format(','.join(['?'] * len(metrics)))
            params.extend(metrics)
            
        with sqlite3.connect(self.working_db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
