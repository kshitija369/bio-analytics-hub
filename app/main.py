import uvicorn
from fastapi import FastAPI
from app.api.routes import router
from app.providers.oura import OuraProvider
from app.core.database import SomaticDatabase
from app.core.normalization import SomaticNormalizer
from app.visualization.dashboard import SomaticDashboard
from datetime import datetime, timedelta, timezone
import os

app = FastAPI(title="Witness State Monitoring")
app.include_router(router)

def run_pipeline(hours_back=24, practice_sessions=None):
    """
    Orchestrates the data collection, normalization, and visualization.
    """
    print(f"\n--- Running Witness State Data Pipeline (Last {hours_back} hours) ---")
    db = SomaticDatabase()
    oura = OuraProvider()
    
    # 1. Fetch Oura Data (Pull-based)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)
    
    print(f"Polling Oura V2 API for period: {start.isoformat()} to {now.isoformat()}")
    raw_oura = oura.fetch_data(start, now)
    std_oura = oura.transform_to_standard(raw_oura)
    
    if std_oura:
        db.insert_biometrics(std_oura)
        print(f"Stored {len(std_oura)} new entries from Oura.")

    # 2. Retrieve Unified Data from DB (both Oura and Apple Health)
    unified_raw = db.get_data(start, now)
    
    if not unified_raw:
        print("No biometric data found in the database for the specified period.")
        return
    
    # 3. Normalize & Clean
    print("Normalizing time-series and resampling to 1-minute frequency...")
    normalizer = SomaticNormalizer()
    df_normalized = normalizer.normalize_to_timeseries(unified_raw)
    
    if practice_sessions:
        df_normalized = normalizer.tag_practice_windows(df_normalized, practice_sessions)

    # 4. Generate Dashboard
    print("Generating interactive Plotly dashboard...")
    SomaticDashboard.generate(df_normalized)
    
    # 5. Witness Zoom Analysis (Example)
    zoom_results = SomaticDashboard.perform_witness_zoom(df_normalized, "Witnessing")
    print("\n" + "="*40)
    print(zoom_results)
    print("="*40 + "\n")

if __name__ == "__main__":
    import sys
    # Usage: 
    #   python -m app.main server   -> Starts FastAPI server
    #   python -m app.main pipeline -> Runs the Oura/Dashboard pipeline
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    
    if mode == "server":
        print("Starting Somatic Log Webhook Server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # For demonstration/testing: assuming a practice session occurred recently
        now = datetime.now(timezone.utc)
        example_sessions = [
            (now - timedelta(hours=2), now - timedelta(hours=1.5), "Witnessing"),
            (now - timedelta(hours=10), now - timedelta(hours=9.5), "Anapanasati")
        ]
        run_pipeline(hours_back=24, practice_sessions=example_sessions)
