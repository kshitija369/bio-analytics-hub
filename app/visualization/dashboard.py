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
        diffs = df.index.to_series().diff() > timedelta(minutes=10)
        groups = diffs.cumsum()
        spans = []
        for _, group in df.groupby(groups):
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
            'readiness': '#3498DB',         # Blue
            'sleep': '#F1C40F',             # Yellow
            'state_key': '#8E44AD',          # Dark Purple
            'bg': '#0A0A0A',
            'grid': '#1A1A1A',
            'text': '#FFFFFF'
        }

        # 3. Process Daily Summary Data
        # Group by date to get daily metrics for the table, handling missing columns gracefully
        agg_map = {
            'is_practice': 'sum',
            'heart_rate': 'mean',
            'heart_rate_variability': 'mean',
            'readiness_score': 'max',
            'hrv_balance': 'max',
            'sleep_score': 'max',
            'steps': 'max'
        }
        # Filter agg_map to only include columns that actually exist in df
        existing_agg = {k: v for k, v in agg_map.items() if k in df.columns}
        
        if existing_agg:
            daily_df = df.resample('D').agg(existing_agg).dropna(how='all')
            daily_df.index = daily_df.index.strftime('%Y-%m-%d')
        else:
            daily_df = pd.DataFrame()

        # 4. Initialize Subplots (5 Rows: Table + 4 Charts)
        fig = make_subplots(
            rows=5, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,
            subplot_titles=("(1) Daily Research Metrics", "(2) Master Practice Key", "(3) Somatic Flow (BPM)", "(4) Recovery Density (HRV)", "(5) Daily Bio-Load (Scores)"),
            row_heights=[0.15, 0.05, 0.25, 0.25, 0.3],
            specs=[[{"type": "table"}], [{"type": "scatter"}], [{"type": "scatter"}], [{"type": "scatter"}], [{"type": "scatter"}]]
        )

        # ----------------------------------------------------------------------
        # ROW 1: DAILY SUMMARY TABLE
        # ----------------------------------------------------------------------
        # Prepare table values with defaults for missing columns
        def get_col(name, round_ndigits=None):
            if name in daily_df.columns:
                return daily_df[name].round(round_ndigits) if round_ndigits is not None else daily_df[name]
            return ["-"] * len(daily_df) if not daily_df.empty else []

        table_vals = [
            daily_df.index if not daily_df.empty else [],
            get_col('is_practice', 0),
            get_col('heart_rate', 1),
            get_col('heart_rate_variability', 1),
            get_col('readiness_score'),
            get_col('hrv_balance'),
            get_col('sleep_score'),
            get_col('steps')
        ]

        fig.add_trace(go.Table(
            header=dict(
                values=["Date", "Practice (Min)", "Avg HR", "Avg HRV", "Readiness", "HRV Bal", "Sleep", "Steps"],
                fill_color='#222', align='left', font=dict(color='white', size=12)
            ),
            cells=dict(
                values=table_vals,
                fill_color='#111', align='left', font=dict(color='white', size=11)
            )
        ), row=1, col=1)

        # ----------------------------------------------------------------------
        # ROW 2: MASTER PRACTICE KEY
        # ----------------------------------------------------------------------
        if 'is_practice' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['is_practice'],
                name='Practice Active', fill='tozeroy',
                line=dict(color=COLORS['state_key'], width=2),
                fillcolor=COLORS['state_key'], opacity=0.8
            ), row=2, col=1)

        # ----------------------------------------------------------------------
        # ROW 3: HEART RATE
        # ----------------------------------------------------------------------
        if 'heart_rate' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate'],
                name='Unified HR', line=dict(color=COLORS['hr_baseline'], width=1.5),
                opacity=0.7
            ), row=3, col=1)

            if 'heart_rate_apple' in df.columns:
                apple_hr = df[df['heart_rate_apple'].notna()]
                fig.add_trace(go.Scatter(
                    x=apple_hr.index, y=apple_hr['heart_rate_apple'],
                    name='Apple Watch HR', mode='markers',
                    marker=dict(size=6, color='#2ECC71', symbol='diamond', line=dict(width=1, color='white'))
                ), row=3, col=1)

            # Vibrant Practice HR
            if 'is_practice' in df.columns:
                practice_data = df[df['is_practice'] == 1]
                if not practice_data.empty:
                    fig.add_trace(go.Scatter(
                        x=practice_data.index, y=practice_data['heart_rate'],
                        name='Witness HR', line=dict(color=COLORS['practice_hr'], width=4),
                        mode='lines+markers', marker=dict(size=4, color=COLORS['practice_hr'])
                    ), row=3, col=1)
            else:
                practice_data = pd.DataFrame()

        # ----------------------------------------------------------------------
        # ROW 4: HRV
        # ----------------------------------------------------------------------
        if 'heart_rate_variability' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['heart_rate_variability'],
                name='Unified HRV', line=dict(color=COLORS['hrv_baseline'], width=1.5),
                opacity=0.7
            ), row=4, col=1)

            if 'heart_rate_variability_apple' in df.columns:
                apple_hrv = df[df['heart_rate_variability_apple'].notna()]
                fig.add_trace(go.Scatter(
                    x=apple_hrv.index, y=apple_hrv['heart_rate_variability_apple'],
                    name='Apple Watch HRV', mode='markers',
                    marker=dict(size=6, color='#2ECC71', symbol='diamond', line=dict(width=1, color='white'))
                ), row=4, col=1)

            # Oura HRV Balance (Fallback/Context)
            if 'hrv_balance_oura' in df.columns:
                oura_bal = df[df['hrv_balance_oura'].notna()]
                fig.add_trace(go.Scatter(
                    x=oura_bal.index, y=oura_bal['hrv_balance_oura'],
                    name='Oura HRV Balance',
                    mode='lines+markers',
                    line=dict(color='#3498DB', width=1, dash='dot'),
                    marker=dict(size=4, symbol='circle'),
                    opacity=0.6
                ), row=4, col=1)

            if not practice_data.empty and 'heart_rate_variability' in practice_data.columns:
                fig.add_trace(go.Scatter(
                    x=practice_data.index, y=practice_data['heart_rate_variability'],
                    name='Witness HRV', line=dict(color=COLORS['practice_hrv'], width=4),
                    mode='lines+markers', marker=dict(size=4, color=COLORS['practice_hrv'])
                ), row=4, col=1)

        # ----------------------------------------------------------------------
        # ROW 5: DAILY BIO-LOAD (Readiness & Sleep)
        # ----------------------------------------------------------------------
        if 'readiness_score' in df.columns:
            # We use forward-fill for scores to make them bars or continuous lines
            fig.add_trace(go.Scatter(
                x=df.index, y=df['readiness_score'].ffill(),
                name='Readiness Score', line=dict(color=COLORS['readiness'], width=3),
                mode='lines'
            ), row=5, col=1)
        
        if 'sleep_score' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['sleep_score'].ffill(),
                name='Sleep Score', line=dict(color=COLORS['sleep'], width=3, dash='dot'),
                mode='lines'
            ), row=5, col=1)

        # 5. Global Layout
        fig.update_layout(
            template="plotly_dark", paper_bgcolor=COLORS['bg'], plot_bgcolor=COLORS['bg'],
            height=1200, hovermode="x unified",
            title=dict(text="<b>SOMATIC RESEARCH HUB:</b> Comprehensive Witness Map", font=dict(size=24, color=COLORS['text']), x=0.05),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis5=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1h", step="hour", stepmode="backward"),
                        dict(count=6, label="6h", step="hour", stepmode="backward"),
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                    ]),
                    bgcolor="#222", activecolor=COLORS['practice_hrv'], font=dict(color="white")
                ),
                rangeslider=dict(visible=True, thickness=0.02),
                type="date", title_text=f"Timeline ({local_tz_short})"
            )
        )

        fig.update_xaxes(gridcolor=COLORS['grid'], zeroline=False, showticklabels=True)
        fig.update_yaxes(gridcolor=COLORS['grid'], zeroline=False)
        
        # Ensure the middle charts have visible timelines for better navigation
        fig.update_xaxes(showticklabels=True, row=3, col=1)
        fig.update_xaxes(showticklabels=True, row=4, col=1)
        
        return fig.to_html(full_html=True, include_plotlyjs='cdn')

    @staticmethod
    def generate(df: pd.DataFrame, output_path="unified_somatic_dashboard.html"):
        html_content = SomaticDashboard.get_html(df)
        with open(output_path, "w") as f:
            f.write(html_content)
        print(f"High-contrast analyzer dashboard saved to {output_path}")

    @staticmethod
    def perform_witness_zoom(df: pd.DataFrame, practice_label="Witnessing"):
        if 'heart_rate_variability' not in df.columns or 'state_label' not in df.columns:
            return "Insufficient data for Witness Zoom."
        practice_starts = df[df['state_label'] == practice_label].index
        if practice_starts.empty:
            return f"No sessions found for {practice_label}."
        start_time = practice_starts[0]
        pre_mask = (df.index >= start_time - timedelta(minutes=15)) & (df.index < start_time)
        pre_hrv = df.loc[pre_mask, 'heart_rate_variability'].mean()
        during_mask = (df.index >= start_time) & (df.index <= start_time + timedelta(minutes=15))
        during_hrv = df.loc[during_mask, 'heart_rate_variability'].mean()
        if pd.isna(pre_hrv) or pd.isna(during_hrv):
            return "Missing baseline or practice HRV data for zoom."
        change_pct = ((during_hrv - pre_hrv) / pre_hrv) * 100
        return f"Witness Zoom Analysis ({practice_label}):\n  Pre-Practice HRV: {pre_hrv:.2f}\n  During-Practice HRV: {during_hrv:.2f}\n  Change: {change_pct:+.2f}%"
