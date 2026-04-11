import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

DB_FILE = "Somatic_Log.sqlite" # Renamed to reflect it's actual SQLite

class SomaticDatabase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
