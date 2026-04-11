import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

import pytz

class SomaticNormalizer:
    @staticmethod
    def localize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Detects system timezone and translates UTC indices."""
        if df.empty:
            return df
        
        # Use pytz for stability in Docker
        # Default to Palo Alto (America/Los_Angeles)
        try:
            local_tz = 'America/Los_Angeles'
            tz_obj = pytz.timezone(local_tz)
        except Exception as e:
            print(f"--- [DEBUG] pytz failure, falling back to UTC: {e} ---")
            local_tz = 'UTC'
            tz_obj = pytz.UTC
        
        # 1. Convert index to datetime if it isn't
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            df.index = pd.to_datetime(df.index)
        
        # 2. Localize: UTC -> System Local
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert(local_tz)
        else:
            df.index = df.index.tz_convert(local_tz)
            
        return df

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
        
        # Standardize source names for cleaner columns
        df['source_key'] = df['source'].apply(lambda x: 'apple' if 'Apple' in str(x) else 'oura')
        
        # Create a unique metric name per source (e.g., heart_rate_apple)
        df['metric_with_source'] = df.apply(lambda row: f"{row['metric']}_{row['source_key']}", axis=1)
        
        df = df.set_index('ts')
        
        # Pivot using the source-specific metric names
        pivoted = df.pivot_table(index='ts', columns='metric_with_source', values='val', aggfunc='mean')
        
        # Also include the generic metric names (mean of both sources) for backward compatibility
        pivoted_generic = df.pivot_table(index='ts', columns='metric', values='val', aggfunc='mean')
        pivoted = pd.concat([pivoted, pivoted_generic], axis=1)

        # Capture tags (if any exist) to preserve state_labels
        tags = df.pivot_table(index='ts', columns='metric', values='tag', aggfunc='first')
        if 'mindful_minutes' in tags.columns:
             pivoted['state_label'] = tags['mindful_minutes'].fillna('Baseline')
        else:
             pivoted['state_label'] = 'Baseline'

        # Resample and Interpolate metrics
        resampled_metrics = pivoted.drop(columns=['state_label']).resample(resample_rate).mean()
        interpolated = resampled_metrics.interpolate(method='linear')
        
        # Resample state_label (forward fill or similar)
        interpolated['state_label'] = pivoted['state_label'].resample(resample_rate).ffill().reindex(interpolated.index).fillna('Baseline')
        
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
