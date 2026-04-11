import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta

class SomaticDashboard:
    @staticmethod
    def generate(df: pd.DataFrame, output_path="unified_somatic_dashboard.html"):
        if df.empty:
            print("No data for dashboard.")
            return

        fig = go.Figure()

        # 1. Plot Heart Rate
        if 'heart_rate' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate'],
                mode='lines', name='Heart Rate (BPM)',
                line=dict(color='black', width=1.5),
                opacity=0.8
            ))

        # 2. Plot HRV on Secondary Y-axis
        if 'heart_rate_variability' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate_variability'],
                mode='markers', name='HRV (SDNN)',
                marker=dict(color='green', size=5, symbol='diamond'),
                yaxis="y2",
                opacity=0.6
            ))

        # 3. State/Practice Overlays
        if 'state_label' in df.columns:
            # Find practice sessions (where label is not Baseline)
            # This is a simplified way to highlight practice blocks
            sessions = df[df['state_label'] != 'Baseline']
            if not sessions.empty:
                # We can group by contiguous labels or just use the raw data points
                # For MVP, we'll highlight the regions
                unique_labels = sessions['state_label'].unique()
                for label in unique_labels:
                    label_data = sessions[sessions['state_label'] == label]
                    # To avoid too many vrects, we find start/end of blocks
                    # (Simplified for now)
                    fig.add_trace(go.Scatter(
                        x=label_data.index, y=[df['heart_rate'].max()] * len(label_data),
                        mode='markers', name=f"Practice: {label}",
                        marker=dict(color='indigo', size=8, symbol='line-ns-open'),
                        hoverinfo='text',
                        text=f"Practice: {label}"
                    ))

        # 4. Layout Configuration
        fig.update_layout(
            title="Somatic_Log: Unified 'Witness State' Dashboard",
            xaxis_title="Time (UTC)",
            yaxis_title="Heart Rate (BPM)",
            yaxis2=dict(
                title="HRV (SDNN ms)",
                overlaying="y",
                side="right",
                showgrid=False
            ),
            template="plotly_white",
            hovermode="x unified",
            height=800,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.write_html(output_path)
        print(f"Unified dashboard saved to {output_path}")

    @staticmethod
    def perform_witness_zoom(df: pd.DataFrame, practice_label="Witnessing"):
        """
        Calculates HRV Change % from the 15 minutes before 
        the practice to the 15 minutes during.
        """
        if 'heart_rate_variability' not in df.columns or 'state_label' not in df.columns:
            return "Insufficient data for Witness Zoom."

        practice_starts = df[df['state_label'] == practice_label].index
        if practice_starts.empty:
            return f"No sessions found for {practice_label}."

        start_time = practice_starts[0]
        
        # 15 mins before
        pre_mask = (df.index >= start_time - timedelta(minutes=15)) & (df.index < start_time)
        pre_hrv = df.loc[pre_mask, 'heart_rate_variability'].mean()
        
        # 15 mins during
        during_mask = (df.index >= start_time) & (df.index <= start_time + timedelta(minutes=15))
        during_hrv = df.loc[during_mask, 'heart_rate_variability'].mean()
        
        if pd.isna(pre_hrv) or pd.isna(during_hrv):
            return "Missing baseline or practice HRV data for zoom."
            
        change_pct = ((during_hrv - pre_hrv) / pre_hrv) * 100
        return f"Witness Zoom Analysis ({practice_label}):\n  Pre-Practice HRV: {pre_hrv:.2f}\n  During-Practice HRV: {during_hrv:.2f}\n  Change: {change_pct:+.2f}%"
