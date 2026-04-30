from fastapi import FastAPI, Request
import os

app = FastAPI(
    title="Agnostic Biometric Research Platform",
    description="""
    A universal biometric research platform for analyzing physiological data,
    Nocturnal Autonomic Research (NAR), and Longevity Frameworks.

    ### Key Features:
    * **Research Engine**: Agnostic biometric dimensions (Heart Rate, HRV) vs. Daily Aggregates.
    * **Sleep Recovery Index**: Nightly autonomic research with baseline comparison and circadian alignment.

    * **Real-time Triggers**: Physiological prompts for high HR and low recovery states.
    * **Agnostic Ingestion**: Support for Oura V2 and Apple Health (Auto-Export).
    """,
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Simple health endpoints
@app.get("/")
async def root(request: Request):
    from app.api.experiment_ui import experiments_hub
    return await experiments_hub(request)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Router inclusion (Logic-heavy code deferred to here)
try:
    from app.api.routes import router
    from app.api.experiment_api import router as experiment_api_router
    from app.api.experiment_ui import router as experiment_ui_router
    from app.api.ui_routes import router as ui_router
    
    app.include_router(router)
    app.include_router(experiment_ui_router, prefix="/experiments", tags=["Research Hub"])
    app.include_router(experiment_api_router, prefix="/api/v1/experiments", tags=["Research API"])
    app.include_router(ui_router, prefix="/api/ui", tags=["Longevity OS UI"])
except Exception as e:
    print(f"--- [CRITICAL] Router load failed: {e} ---")

def run_pipeline(hours_back=168, practice_sessions=None):
    """Pipeline logic (only runs in CLI mode)"""
    from app.adapters.oura import OuraProvider
    from app.core.database import BiometricDatabase
    from app.core.normalization import BiometricNormalizer
    from app.visualization.dashboard import BiometricDashboard
    from app.core.alerts import BiometricTriggerEngine
    from datetime import datetime, timedelta, timezone

    print(f"\n--- Running Peak Autonomic Recovery Data Pipeline (Last {hours_back} hours) ---")
    db = BiometricDatabase()
    oura = OuraProvider()
    trigger_engine = BiometricTriggerEngine(db=db)
    
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)
    
    raw_oura = oura.fetch_data(start, now)
    std_oura = oura.transform_to_standard(raw_oura)
    
    if std_oura:
        db.insert_biometrics(std_oura)
        for entry in std_oura:
            trigger_engine.evaluate(entry['metric'], entry['val'], timestamp=entry['ts'])
            # Phase 1: Secular Witness Perception (Event-Driven)
            trigger_engine.evaluate_anomaly(entry['metric'], entry['val'], timestamp=entry['ts'])

    unified_raw = db.get_data(start, now)
    if unified_raw:
        df_normalized = BiometricNormalizer().normalize_to_timeseries(unified_raw)
        if practice_sessions:
            df_normalized = BiometricNormalizer().tag_practice_windows(df_normalized, practice_sessions)
        BiometricDashboard.generate(df_normalized)

if __name__ == "__main__":
    import sys
    import uvicorn
    mode = sys.argv[1] if len(sys.argv) > 1 else "pipeline"
    
    if mode == "server":
        port = int(os.environ.get("PORT", 8080))
        # Note: Production uses gunicorn via entrypoint
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
    else:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        example_sessions = [(now - timedelta(hours=2), now - timedelta(hours=1.5), "Recovery")]
        run_pipeline(hours_back=24, practice_sessions=example_sessions)
