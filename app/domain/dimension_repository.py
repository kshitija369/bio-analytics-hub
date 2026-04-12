import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.core.database import BiometricDatabase

class DimensionRepository:
    """
    The 'Agnostic Data Hub' that hides providers from the experiment engine.
    Maps generic Dimensions to underlying metric names in the database.
    """
    
    # Mapping of high-level Dimensions to DB metric names
    DIMENSION_MAP = {
        "HeartRate": ["heart_rate"],
        "HRV": ["heart_rate_variability"],
        "ReadinessScore": ["readiness_score"],
        "SleepScore": ["sleep_score"],
        "Activity": ["steps"],
        "MindfulMinutes": ["mindful_minutes"]
    }

    def __init__(self, db: Optional[BiometricDatabase] = None):
        self.db = db or BiometricDatabase()

    def get_dimension_data(self, dimension_type: str, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Retrieves raw biometric data for a given dimension within a time window.
        Returns a DataFrame indexed by timestamp.
        """
        metrics = self.DIMENSION_MAP.get(dimension_type)
        if not metrics:
            print(f"--- [DimensionRepo] Warning: Unknown dimension '{dimension_type}' ---")
            return pd.DataFrame()
            
        data = self.db.get_data(start, end, metrics=metrics)
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        # Ensure ts is datetime, convert to naive (ignore TZ) for math consistency
        df['ts'] = pd.to_datetime(df['ts'], format='ISO8601')
        if pd.api.types.is_datetime64_any_dtype(df['ts']) and df['ts'].dt.tz is not None:
            df['ts'] = df['ts'].dt.tz_localize(None)
            
        df = df.set_index('ts').sort_index()
        
        return df

    def get_daily_aggregate(self, dimension_type: str, target_date: date) -> Optional[float]:
        """
        Retrieves a single aggregate value for a dimension on a specific date.
        Useful for scores like Readiness or Sleep.
        """
        # Define the 24h window for the date
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        
        df = self.get_dimension_data(dimension_type, start, end)
        if df.empty:
            return None
            
        # For daily aggregates (like Oura Readiness), we take the mean 
        # (though usually there is only one record at 00:00:00)
        return float(df['val'].mean())

    def get_window_summary(self, dimension_type: str, start: datetime, end: datetime, agg_func='mean') -> Optional[float]:
        """
        Calculates a summary statistic for a dimension over a specific time window.
        """
        df = self.get_dimension_data(dimension_type, start, end)
        if df.empty:
            return None
            
        if agg_func == 'mean':
            return float(df['val'].mean())
        elif agg_func == 'max':
            return float(df['val'].max())
        elif agg_func == 'min':
            return float(df['val'].min())
        return None
