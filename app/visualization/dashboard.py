from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta

class SomaticDashboard:
    @staticmethod
    def generate(df: pd.DataFrame, output_path="unified_somatic_dashboard.html"):
        if df.empty:
            print("No data for dashboard.")
            return

        # 1. Initialize Subplots
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05,
            subplot_titles=("Somatic Flow (Heart Rate)", "Recovery Density (HRV)"),
            row_heights=[0.6, 0.4]
        )

        # 2. Add Heart Rate (Somatic Flow)
        if 'heart_rate' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate'],
                mode='lines', name='Heart Rate (BPM)',
                line=dict(color='black', width=1),
                opacity=0.7
            ), row=1, col=1)

            # Highlight Witness Sessions on HR plot
            if 'state_label' in df.columns:
                witness_df = df[df['state_label'] == 'Witnessing']
                if not witness_df.empty:
                    fig.add_trace(go.Scatter(
                        x=witness_df.index, y=witness_df['heart_rate'],
                        mode='markers', name='Witness State',
                        marker=dict(color='indigo', size=6, symbol='diamond'),
                        hoverinfo='text',
                        text='In Practice: Witnessing'
                    ), row=1, col=1)

        # 3. Add HRV (Recovery Density)
        if 'heart_rate_variability' in df.columns:
            fig.add_trace(go.Bar(
                x=df.index, y=df['heart_rate_variability'],
                name='HRV (SDNN ms)',
                marker_color='teal',
                opacity=0.8
            ), row=2, col=1)

        # 4. Global Layout Configuration
        fig.update_layout(
            title="7-Day Somatic Witness Map: Physiological Realities of Practice",
            template="plotly_white",
            hovermode="x unified",
            height=900,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_yaxes(title_text="BPM", row=1, col=1)
        fig.update_yaxes(title_text="SDNN (ms)", row=2, col=1)
        fig.update_xaxes(title_text="Time (UTC)", row=2, col=1)

        fig.write_html(output_path)
        print(f"Intuitive unified dashboard saved to {output_path}")

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
