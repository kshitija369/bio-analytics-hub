import os
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, timezone

# Configuration
PERSONAL_ACCESS_TOKEN = os.environ.get("OURA_PAT", "YOUR_OURA_TOKEN")
HEADERS = {'Authorization': f'Bearer {PERSONAL_ACCESS_TOKEN}'}
FETCH_HOURS = int(os.environ.get("FETCH_HOURS", 24))

def fetch_oura_v2(endpoint, start_time, end_time):
    """General fetcher for Oura API v2 endpoints."""
    url = f'https://api.ouraring.com/v2/usercollection/{endpoint}'
    params = {
        'start_datetime': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        'end_datetime': end_time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(f"Error fetching {endpoint}: {response.status_code} - {response.text}")
        return []
    return response.json().get('data', [])

def process_and_flag_data(meditation_windows, hours_back=24):
    """Fetches, normalizes, and flags practice windows."""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours_back)

    print(f"Fetching Oura data from {start_time} to {now} ({hours_back} hours)...")

    # 1. Fetch Data
    hr_data = fetch_oura_v2('heartrate', start_time, now)
    stress_data = fetch_oura_v2('daily_stress', start_time, now)

    if not hr_data:
        print(f"No heart rate data found for the last {hours_back} hours.")
        return pd.DataFrame()

    # 2. Normalize Heart Rate to DataFrame
    df_hr = pd.DataFrame(hr_data)
    df_hr['timestamp'] = pd.to_datetime(df_hr['timestamp'])
    df_hr = df_hr.set_index('timestamp')
    df_hr = df_hr[['bpm']].resample('1min').mean().interpolate()

    # 3. Flag Practice Windows
    df_hr['is_practice'] = False
    df_hr['practice_type'] = None

    for start, end, label in meditation_windows:
        start_dt = pd.to_datetime(start).tz_localize('UTC') if pd.to_datetime(start).tz is None else pd.to_datetime(start).tz_convert('UTC')
        end_dt = pd.to_datetime(end).tz_localize('UTC') if pd.to_datetime(end).tz is None else pd.to_datetime(end).tz_convert('UTC')
        
        mask = (df_hr.index >= start_dt) & (df_hr.index <= end_dt)
        df_hr.loc[mask, 'is_practice'] = True
        df_hr.loc[mask, 'practice_type'] = label

    return df_hr

def create_interactive_dashboard(df, practice_windows):
    """Generates an interactive HTML dashboard using Plotly."""
    if df.empty:
        print("No data for dashboard.")
        return

    fig = go.Figure()

    # 1. Heart Rate Line
    fig.add_trace(go.Scatter(
        x=df.index, y=df['bpm'],
        mode='lines',
        name='Heart Rate (BPM)',
        line=dict(color='black', width=1.5),
        opacity=0.8
    ))

    # 2. Add Practice Windows as Shaded Regions
    for start, end, label in practice_windows:
        start_dt = pd.to_datetime(start).tz_localize('UTC') if pd.to_datetime(start).tz is None else pd.to_datetime(start).tz_convert('UTC')
        end_dt = pd.to_datetime(end).tz_localize('UTC') if pd.to_datetime(end).tz is None else pd.to_datetime(end).tz_convert('UTC')
        
        # Check if window overlaps with our data
        if start_dt >= df.index.min() and start_dt <= df.index.max():
            fig.add_vrect(
                x0=start_dt, x1=end_dt,
                fillcolor="indigo", opacity=0.3,
                layer="below", line_width=0,
                annotation_text=label, annotation_position="top left",
                annotation=dict(font_size=14, font_color="indigo", font_weight="bold")
            )

    # 3. Dashboard Layout Styling
    fig.update_layout(
        title={
            'text': "Oura Recovery Dashboard: Systemic Stress vs. Practice",
            'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top'
        },
        xaxis_title="Time (UTC)",
        yaxis_title="Heart Rate (BPM)",
        template="plotly_white",
        hovermode="x unified",
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 4. Save to HTML
    output_path = 'oura_dashboard.html'
    fig.write_html(output_path)
    print(f"Interactive dashboard saved to {output_path}")

def fetch_sleep_architecture(start_date, end_date):
    """
    Fetches deeper sleep metrics to correlate with Witness practice.
    Focuses on Recovery Index and Heart Rate Drop Timing.
    """
    url = 'https://api.ouraring.com/v2/usercollection/daily_sleep'
    params = {'start_date': start_date, 'end_date': end_date}
    
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(f"Error fetching sleep architecture: {response.status_code}")
        return pd.DataFrame()
        
    data = response.json().get('data', [])
    
    sleep_insights = []
    for day in data:
        # 'contributors' contains the architectural logic
        contribs = day.get('contributors', {})
        sleep_insights.append({
            "date": day['day'],
            "recovery_index": contribs.get('recovery_index'), # Timing of HR drop
            "rem_score": contribs.get('rem_sleep'),
            "deep_score": contribs.get('deep_sleep'),
            "efficiency": contribs.get('efficiency'),
            "score": day.get('score')
        })
    return pd.DataFrame(sleep_insights)

if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    print(f"\n--- Fetching Deep Sleep Architecture ({start_date} to {end_date}) ---")
    sleep_df = fetch_sleep_architecture(start_date, end_date)
    if not sleep_df.empty:
        print(sleep_df)

    practice_sessions = [
        (now - timedelta(hours=4), now - timedelta(hours=3), "Witnessing"),
        (now - timedelta(hours=24), now - timedelta(hours=23), "Anapanasati")
    ]

    analysis_df = process_and_flag_data(practice_sessions, hours_back=FETCH_HOURS)
    create_interactive_dashboard(analysis_df, practice_sessions)
