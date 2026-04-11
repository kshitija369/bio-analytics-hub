import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

DB_FILE = "Somatic_Log.sqlite" # Renamed to reflect it's actual SQLite

class SomaticDatabase:
    def __init__(self, db_path=None):
        self._db_path_override = db_path
        self._initialized = False
        self.db_path = None

    def _ensure_initialized(self):
        if self._initialized:
            return

        if self._db_path_override:
            self.db_path = self._db_path_override
        elif os.path.exists("/app/data"):
            # Path for persistent mount in GCP Cloud Run
            self.db_path = "/app/data/Somatic_Log.sqlite"
        else:
            self.db_path = DB_FILE # Local fallback
            
        print(f"Initializing database at: {self.db_path}")
        try:
            # Increase timeout for FUSE latency
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # Optimized for FUSE (No locking, no journal)
                if "/app/data" in self.db_path:
                    print("Applying FUSE-compatible SQLite pragmas...")
                    conn.execute("PRAGMA journal_mode = OFF")
                    conn.execute("PRAGMA synchronous = OFF")
                    conn.execute("PRAGMA temp_store = MEMORY")
                
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
            print("Database initialized successfully.")
            self._initialized = True
        except Exception as e:
            print(f"CRITICAL ERROR initializing database: {e}")
            if "/app/data" in (self.db_path or ""):
                print("Falling back to ephemeral /tmp storage...")
                self.db_path = "/tmp/Somatic_Log.sqlite"
                self._initialized = False 
                self._ensure_initialized()
            else:
                raise e

    def insert_biometrics(self, entries: List[Dict[str, Any]]):
        self._ensure_initialized()
        # Retry logic for FUSE locks
        import time
        max_retries = 5
        for i in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=30) as conn:
                    conn.executemany("""
                        INSERT INTO biometrics (ts, metric, val, unit, source, tag)
                        VALUES (:ts, :metric, :val, :unit, :source, :tag)
                    """, entries)
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and i < max_retries - 1:
                    time.sleep(1)
                    continue
                raise e

    def get_data(self, start_time: datetime, end_time: datetime, metrics: List[str] = None) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        query = "SELECT ts, metric, val, unit, source, tag FROM biometrics WHERE ts BETWEEN ? AND ?"
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if metrics:
            query += " AND metric IN ({})".format(','.join(['?'] * len(metrics)))
            params.extend(metrics)
            
        # Use a longer timeout and specific FUSE flags if possible
        # For reading, we can use uri=True to open in read-only mode to avoid locks
        try:
            db_uri = f"file:{self.db_path}?mode=ro" if "/app/data" in self.db_path else self.db_path
            with sqlite3.connect(db_uri, timeout=30, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            # Fallback to normal connection if URI fails
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
