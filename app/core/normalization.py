import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import pytz

class BiometricNormalizer:
    @staticmethod
    def localize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Detects and localizes naive DataFrames to UTC."""
        if df.index.tz is None:
            return df.tz_localize('UTC')
        return df.tz_convert('UTC')

    @staticmethod
    def normalize_to_timeseries(raw_entries: List[Dict[str, Any]], resample_rate: str = '1min') -> pd.DataFrame:
        """
        Processes heterogeneous raw biometric entries into a unified,
        uniformly sampled UTC time-series DataFrame.
        """
        if not raw_entries:
            return pd.DataFrame()

        df = pd.DataFrame(raw_entries)
        
        # Ensure timestamp is datetime and UTC
        df['ts'] = pd.to_datetime(df['ts'], format='ISO8601', utc=True)
        # Use .dt.tz_convert to ensure everything is explicitly UTC
        df['ts'] = df['ts'].dt.tz_convert('UTC')
        
        # Add a unique key for pivot: metric + source
        # This prevents collisions when multiple sources provide the same metric
        df['source_key'] = df['source'].apply(lambda x: str(x).split('_')[0].lower())
        df['metric_with_source'] = df['metric'] + "_" + df['source_key']
        
        # Pivot into columns (Time-Series)
        # Note: We pivot on metric_with_source but keep 'metric' logic for unified views
        pivoted = df.pivot_table(index='ts', columns='metric', values='val', aggfunc='mean')
        
        # Add state_label if it exists
        if 'tag' in df.columns:
            # For simplicity, we take the 'first' tag encountered for that timestamp
            tags = df.pivot_table(index='ts', columns='metric', values='tag', aggfunc='first')
            # Use the most frequent tag across all metrics for that minute as 'state_label'
            pivoted['state_label'] = tags.ffill(axis=1).iloc[:, -1]
        else:
            pivoted['state_label'] = 'Baseline'

        # Resample and Interpolate metrics
        resampled_metrics = pivoted.drop(columns=['state_label']).resample(resample_rate).mean()
        interpolated = resampled_metrics.interpolate(method='linear')
        
        # Resample state_label (forward fill)
        interpolated['state_label'] = pivoted['state_label'].resample(resample_rate).ffill().reindex(interpolated.index).fillna('Baseline')
        
        return interpolated

    @staticmethod
    def tag_practice_windows(df: pd.DataFrame, practice_sessions: List[tuple]) -> pd.DataFrame:
        """
        Flags periods of 'Recovery' or other practices.
        practice_sessions: List of (start_dt, end_dt, label)
        """
        if df.empty:
            return df
            
        df['state_label'] = 'Baseline'
        
        for start, end, label in practice_sessions:
            # Handle naive or aware inputs
            start_dt = pd.to_datetime(start).tz_localize('UTC') if pd.to_datetime(start).tz is None else pd.to_datetime(start).tz_convert('UTC')
            end_dt = pd.to_datetime(end).tz_localize('UTC') if pd.to_datetime(end).tz is None else pd.to_datetime(end).tz_convert('UTC')
            
            mask = (df.index >= start_dt) & (df.index <= end_dt)
            df.loc[mask, 'state_label'] = label
            
        return df

    @staticmethod
    def stitch_synthetic_day(history_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
        """
        DT4H-Sim: Stitches historical observations with predicted 
        synthetic data for a continuous 48h view.
        """
        if history_df.empty: return synthetic_df
        if synthetic_df.empty: return history_df
        
        # Mark history as non-synthetic
        if 'is_synthetic' not in history_df.columns:
            history_df['is_synthetic'] = 0
            
        combined = pd.concat([history_df, synthetic_df]).sort_index()
        return combined
