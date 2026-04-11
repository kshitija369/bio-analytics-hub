from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta
from app.core.normalization import SomaticNormalizer

class SomaticDashboard:
    @staticmethod
    def _get_session_spans(df):
        """Helper to find continuous blocks of 'Witnessing'"""
        if df.empty: return []
        # Group samples that are within 10 minutes of each other to form a session
        diffs = df.index.to_series().diff() > timedelta(minutes=10)
        groups = diffs.cumsum()
        spans = []
        for _, group in df.groupby(groups):
            # If it's a single point, give it a small duration (e.g. 1 min) for visibility
            start = group.index.min()
            end = group.index.max()
            if start == end:
                end = start + timedelta(minutes=1)
            spans.append((start, end))
        return spans

    @staticmethod
    def get_html(df: pd.DataFrame) -> str:
        if df.empty:
            return "<html><body><h1>No data available for dashboard.</h1></body></html>"

        # 1. Apply Localization
        df = SomaticNormalizer.localize_dataframe(df)
        local_tz_short = df.index.strftime('%Z')[0] if not df.empty else "Local"

        # 2. High-Contrast Cyber-Somatic Palette
        COLORS = {
            'hr_baseline': 'rgba(231, 76, 60, 0.4)',  # Faded Red
            'hrv_baseline': 'rgba(189, 195, 199, 0.5)', # Gray
            'practice_hr': '#9B59B6',       # Vibrant Purple (ACTIVE)
            'practice_hrv': '#2ECC71',      # Radiant Green (ACTIVE)
            'state_key': '#8E44AD',          # Dark Purple (State Key)
            'bg': '#0A0A0A',
            'grid': '#1A1A1A',
            'text': '#FFFFFF'
        }

        # 3. Add Binary State Column (The Key to Intuition)
        if 'state_label' in df.columns:
            df['is_practice'] = (df['state_label'] == 'Witnessing').astype(int)
        else:
            df['is_practice'] = 0

        # 4. Initialize Subplots (3 Rows for Master Key)
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.04,
            subplot_titles=("(1) Master Practice Key", "(2) Somatic Baseline (BPM)", "(3) Recovery Density (HRV)"),
            row_heights=[0.1, 0.45, 0.45]
        )

        # ----------------------------------------------------------------------
        # ROW 1: MASTER PRACTICE KEY (Binary state indicator)
        # ----------------------------------------------------------------------
        fig.add_trace(go.Scatter(
            x=df.index, y=df['is_practice'],
            name='Practice Active',
            fill='tozeroy',
            line=dict(color=COLORS['state_key'], width=2),
            fillcolor=COLORS['state_key'],
            opacity=0.8,
            mode='lines'
        ), row=1, col=1)

        # ----------------------------------------------------------------------
        # ROW 2: HEART RATE (Dynamic Color/Thickness Change)
        # ----------------------------------------------------------------------
        if 'heart_rate' in df.columns:
            # Baseline HR (Faded)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate'],
                name='Unified HR',
                line=dict(color=COLORS['hr_baseline'], width=1.5),
                mode='lines',
                opacity=0.7
            ), row=2, col=1)

            # Apple Watch Specific Samples
            if 'heart_rate_apple' in df.columns:
                apple_hr = df[df['heart_rate_apple'].notna()]
                fig.add_trace(go.Scatter(
                    x=apple_hr.index, y=apple_hr['heart_rate_apple'],
                    name='Apple Watch HR',
                    mode='markers',
                    marker=dict(size=6, color='#2ECC71', symbol='diamond', line=dict(width=1, color='white')),
                    opacity=0.9
                ), row=2, col=1)

            # Witness HR (Thick/Vibrant)
            practice_data = df[df['is_practice'] == 1]
            if not practice_data.empty:
                # We use markers+lines to ensure gaps are handled visually correctly
                fig.add_trace(go.Scatter(
                    x=practice_data.index, y=practice_data['heart_rate'],
                    name='Witness HR',
                    line=dict(color=COLORS['practice_hr'], width=4),
                    mode='lines+markers',
                    marker=dict(size=4, color=COLORS['practice_hr'])
                ), row=2, col=1)

        # ----------------------------------------------------------------------
        # ROW 3: HRV (Dynamic Color/Thickness Change)
        # ----------------------------------------------------------------------
        if 'heart_rate_variability' in df.columns:
            # Baseline HRV (Faded)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate_variability'],
                name='Unified HRV',
                line=dict(color=COLORS['hrv_baseline'], width=1.5),
                mode='lines',
                opacity=0.7
            ), row=3, col=1)

            # Apple Watch Specific HRV
            if 'heart_rate_variability_apple' in df.columns:
                apple_hrv = df[df['heart_rate_variability_apple'].notna()]
                fig.add_trace(go.Scatter(
                    x=apple_hrv.index, y=apple_hrv['heart_rate_variability_apple'],
                    name='Apple Watch HRV',
                    mode='markers',
                    marker=dict(size=6, color='#2ECC71', symbol='diamond', line=dict(width=1, color='white')),
                    opacity=0.9
                ), row=3, col=1)

            # Witness HRV (Thick/Radiant)
            if not practice_data.empty:

        # 5. Smart Zoom & Dark Mode Layout
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['bg'],
            height=1000,
            hovermode="x unified",
            title=dict(
                text="<b>SOMATIC WITNESS LOG:</b> High-Contrast State Analyzer",
                font=dict(size=24, color=COLORS['text']),
                x=0.05
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis3=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1h", step="hour", stepmode="backward"),
                        dict(count=6, label="6h", step="hour", stepmode="backward"),
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                    ]),
                    bgcolor="#222",
                    activecolor=COLORS['practice_hrv'],
                    font=dict(color="white")
                ),
                rangeslider=dict(visible=True, thickness=0.03),
                type="date",
                title_text=f"Timeline ({local_tz_short})"
            )
        )

        fig.update_xaxes(gridcolor=COLORS['grid'], zeroline=False)
        fig.update_yaxes(gridcolor=COLORS['grid'], zeroline=False)
        
        return fig.to_html(full_html=True, include_plotlyjs='cdn')

    @staticmethod
    def generate(df: pd.DataFrame, output_path="unified_somatic_dashboard.html"):
        html_content = SomaticDashboard.get_html(df)
        with open(output_path, "w") as f:
            f.write(html_content)
        print(f"High-contrast analyzer dashboard saved to {output_path}")

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
