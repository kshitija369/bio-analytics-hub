import sqlite3
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any

DB_FILE = "Somatic_Log.sqlite" # Local fallback

class SomaticDatabase:
    def __init__(self, db_path=None):
        self._db_path_override = db_path
        self._initialized = False
        
        # Two-Tier Strategy:
        # 1. working_db: Local /tmp file for high-speed, no-lock R/W
        # 2. persistent_db: The FUSE mount at /app/data for backup
        self.working_db = "/tmp/Somatic_Log_Working.sqlite"
        self.persistent_db = "/app/data/Somatic_Log.sqlite"
def _ensure_initialized(self):
    if self._initialized:
        return

    import os
    import shutil

    # 1. Setup Persistent Path
    if self._db_path_override:
        self.persistent_db = self._db_path_override
    elif not os.path.exists("/app/data"):
        # If not on GCP, use local DB as the working DB directly
        self.working_db = DB_FILE
        self.persistent_db = DB_FILE

    print(f"--- [DB DEBUG] Working: {self.working_db}, Persistent: {self.persistent_db} ---")

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
                    tag TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON biometrics(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metric ON biometrics(metric)")
        print("--- [DB DEBUG] Working database initialized successfully ---")
        self._initialized = True
    except Exception as e:
        print(f"--- [DB DEBUG] CRITICAL INITIALIZATION ERROR: {e} ---")
        raise e

        """Backs up the local working DB to the persistent FUSE mount."""
        # Only flush if the mount directory exists and we are in two-tier mode
        if self.working_db != self.persistent_db and os.path.exists("/app/data"):
            print(f"Flushing working DB to persistence: {self.persistent_db}")
            try:
                shutil.copy2(self.working_db, self.persistent_db)
                print("Flush successful.")
            except Exception as e:
                print(f"Flush FAILED: {e}")

    def insert_biometrics(self, entries: List[Dict[str, Any]]):
        self._ensure_initialized()
        with sqlite3.connect(self.working_db) as conn:
            conn.executemany("""
                INSERT INTO biometrics (ts, metric, val, unit, source, tag)
                VALUES (:ts, :metric, :val, :unit, :source, :tag)
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
