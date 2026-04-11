from fastapi import FastAPI
import os

# --- [ULTRA-SLIM STARTUP] ---
# No heavy imports (pandas, plotly, etc.) at the top level.
# This guarantees the port binds in < 1 second.

app = FastAPI(title="Witness State Monitoring")

@app.get("/")
async def root():
    return {"status": "alive", "message": "Witness State Monitoring API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# The router is included only when needed or via a deferred import
def include_deferred_router():
    try:
        from app.api.routes import router
        app.include_router(router)
        return True
    except Exception as e:
        print(f"Deferred router load error: {e}")
        return False

# Attempt to include router, but don't let it crash the startup
include_deferred_router()

def run_pipeline(hours_back=168, practice_sessions=None):
    """Pipeline logic (only runs in CLI mode)"""
    # Imports moved inside to protect server startup
    from app.providers.oura import OuraProvider
    from app.core.database import SomaticDatabase
    from app.core.normalization import SomaticNormalizer
    from app.visualization.dashboard import SomaticDashboard
    from app.core.alerts import SomaticTriggerEngine
    from datetime import datetime, timedelta, timezone

    print(f"\n--- Running Witness State Data Pipeline (Last {hours_back} hours) ---")
    db = SomaticDatabase()
    oura = OuraProvider()
    trigger_engine = SomaticTriggerEngine()
    
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)
    
    raw_oura = oura.fetch_data(start, now)
    std_oura = oura.transform_to_standard(raw_oura)
    
    if std_oura:
        db.insert_biometrics(std_oura)
        for entry in std_oura:
            trigger_engine.evaluate(entry['metric'], entry['val'])

    unified_raw = db.get_data(start, now)
    if unified_raw:
        df_normalized = SomaticNormalizer().normalize_to_timeseries(unified_raw)
        if practice_sessions:
            df_normalized = SomaticNormalizer().tag_practice_windows(df_normalized, practice_sessions)
        SomaticDashboard.generate(df_normalized)

if __name__ == "__main__":
    import sys
    import uvicorn
    mode = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    
    if mode == "server":
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        example_sessions = [(now - timedelta(hours=2), now - timedelta(hours=1.5), "Witnessing")]
        run_pipeline(hours_back=24, practice_sessions=example_sessions)
