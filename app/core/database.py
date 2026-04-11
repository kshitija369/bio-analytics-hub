import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

DB_FILE = "Somatic_Log.sqlite" # Renamed to reflect it's actual SQLite

class SomaticDatabase:
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        elif os.path.exists("/app/data"):
            # Path for persistent mount in GCP Cloud Run
            self.db_path = "/app/data/Somatic_Log.sqlite"
        else:
            self.db_path = DB_FILE # Local fallback
            
        self._init_db()

    def _init_db(self):
        print(f"Initializing database at: {self.db_path}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Optimized for FUSE (No locking, no journal)
                if "/app/data" in self.db_path:
                    print("Applying FUSE-compatible SQLite pragmas...")
                    conn.execute("PRAGMA locking_mode = EXCLUSIVE")
                    conn.execute("PRAGMA journal_mode = OFF")
                
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
        except Exception as e:
            print(f"CRITICAL ERROR initializing database: {e}")
            # Fallback to local /tmp if the mount is broken
            if "/app/data" in self.db_path:
                print("Falling back to ephemeral /tmp storage...")
                self.db_path = "/tmp/Somatic_Log.sqlite"
                self._init_db()
            else:
                raise e

    def insert_biometrics(self, entries: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT INTO biometrics (ts, metric, val, unit, source, tag)
                VALUES (:ts, :metric, :val, :unit, :source, :tag)
            """, entries)

    def get_data(self, start_time: datetime, end_time: datetime, metrics: List[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT ts, metric, val, unit, source, tag FROM biometrics WHERE ts BETWEEN ? AND ?"
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if metrics:
            query += " AND metric IN ({})".format(','.join(['?'] * len(metrics)))
            params.extend(metrics)
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
