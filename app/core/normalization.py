import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

class SomaticNormalizer:
    @staticmethod
    def normalize_to_timeseries(data: List[Dict[str, Any]], resample_rate='1min') -> pd.DataFrame:
        """
        Takes standardized biometric list and returns a cleaned, 
        resampled, and interpolated pandas DataFrame.
        """
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['ts'] = pd.to_datetime(df['ts'], format='ISO8601')
        
        # Ensure UTC and localize if missing
        df['ts'] = df.apply(
            lambda x: x['ts'].tz_convert('UTC') if x['ts'].tz is not None 
            else x['ts'].tz_localize('UTC'), axis=1
        )
        
        df = df.set_index('ts')
        
        # Pivot to have metrics as columns for easier time-series manipulation
        # Note: This assumes one value per metric per timestamp, or we take the mean
        pivoted = df.pivot_table(index='ts', columns='metric', values='val', aggfunc='mean')
        
        # Resample and Interpolate
        resampled = pivoted.resample(resample_rate).mean()
        # Linear interpolation to fill gaps (max_gap could be added later)
        interpolated = resampled.interpolate(method='linear')
        
        return interpolated

    @staticmethod
    def tag_practice_windows(df: pd.DataFrame, practice_sessions: List[tuple]) -> pd.DataFrame:
        """
        Flags periods of 'Witnessing' or other practices.
        practice_sessions: List of (start_dt, end_dt, label)
        """
        if df.empty:
            return df
            
        df['state_label'] = 'Baseline'
        
        for start, end, label in practice_sessions:
            start_dt = pd.to_datetime(start).tz_localize('UTC') if pd.to_datetime(start).tz is None else pd.to_datetime(start).tz_convert('UTC')
            end_dt = pd.to_datetime(end).tz_localize('UTC') if pd.to_datetime(end).tz is None else pd.to_datetime(end).tz_convert('UTC')
            
            mask = (df.index >= start_dt) & (df.index <= end_dt)
            df.loc[mask, 'state_label'] = label
            
        return df
