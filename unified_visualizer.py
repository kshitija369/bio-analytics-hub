import os
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import requests

# --- Configuration ---
DB_FILE = "Somatic_Log.db"
OURA_PAT = os.environ.get("OURA_PAT", "YOUR_OURA_TOKEN")
FETCH_HOURS = int(os.environ.get("FETCH_HOURS", 24))

def load_apple_health_data():
    """Loads and parses data from the Somatic_Log.db file."""
    if not os.path.exists(DB_FILE):
        print(f"Warning: {DB_FILE} not found. No Apple Health data to load.")
        return pd.DataFrame()

    data_list = []
    with open(DB_FILE, "r") as f:
        for line in f:
            try:
                data_list.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    if not data_list:
        return pd.DataFrame()

    df = pd.DataFrame(data_list)
    df['ts'] = pd.to_datetime(df['ts'])
    # Convert all timestamps to UTC to match Oura
    df['ts'] = df['ts'].dt.tz_convert('UTC') if df['ts'].dt.tz is not None else df['ts'].dt.tz_localize('UTC')
    
    return df

def fetch_oura_heartrate(hours_back=24):
    """Fetches high-resolution heart rate data from Oura V2."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)
    
    url = 'https://api.ouraring.com/v2/usercollection/heartrate'
    params = {
        'start_datetime': start.strftime("%Y-%m-%dT%H:%M:%S"),
        'end_datetime': now.strftime("%Y-%m-%dT%H:%M:%S")
    }
    headers = {'Authorization': f'Bearer {OURA_PAT}'}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get('data', [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    return pd.DataFrame()

def create_unified_dashboard():
    """Generates an interactive dashboard overlaying Apple Watch and Oura data."""
    print("Loading data for unified visualization...")
    
    df_apple = load_apple_health_data()
    df_oura = fetch_oura_heartrate(FETCH_HOURS)

    fig = go.Figure()

    # 1. Plot Oura Heart Rate (High-Resolution Baseline)
    if not df_oura.empty:
        fig.add_trace(go.Scatter(
            x=df_oura['timestamp'], y=df_oura['bpm'],
            mode='lines', name='Oura HR (BPM)',
            line=dict(color='gray', width=1, dash='dot'),
            opacity=0.5
        ))

    # 2. Plot Apple Watch Metrics
    if not df_apple.empty:
        # HR from Apple Watch
        hr_aw = df_apple[df_apple['metric'] == 'heart_rate']
        if not hr_aw.empty:
            fig.add_trace(go.Scatter(
                x=hr_aw['ts'], y=hr_aw['val'],
                mode='markers+lines', name='Apple Watch HR',
                marker=dict(color='black', size=4)
            ))

        # HRV from Apple Watch (Secondary Y-axis candidate, but keeping it simple for now)
        hrv_aw = df_apple[df_apple['metric'] == 'heart_rate_variability']
        if not hrv_aw.empty:
            fig.add_trace(go.Scatter(
                x=hrv_aw['ts'], y=hrv_aw['val'],
                mode='markers', name='Apple Watch HRV (SDNN)',
                marker=dict(color='green', size=6, symbol='diamond'),
                yaxis="y2"
            ))

        # Mindful Minutes (Background Spans)
        mindful = df_apple[df_apple['metric'] == 'mindful_minutes']
        for _, row in mindful.iterrows():
            # Mindful minutes are usually logged as a single point with duration
            # Here we just flag the point
            fig.add_vrect(
                x0=row['ts'] - timedelta(minutes=1), x1=row['ts'] + timedelta(minutes=1),
                fillcolor="indigo", opacity=0.2, layer="below", line_width=0,
                annotation_text="Mindful", annotation_position="top left"
            )

    # 3. Layout Configuration
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
        height=800
    )

    output_path = "unified_somatic_dashboard.html"
    fig.write_html(output_path)
    print(f"Unified dashboard saved to {output_path}")

if __name__ == "__main__":
    create_unified_dashboard()
