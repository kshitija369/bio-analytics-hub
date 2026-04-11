from fastapi import APIRouter, Request, HTTPException
from datetime import datetime

router = APIRouter()

# Lazy initializers
_db = None
_trigger_engine = None

def get_db():
    global _db
    if _db is None:
        from ..core.database import SomaticDatabase
        _db = SomaticDatabase()
    return _db

def get_trigger_engine():
    global _trigger_engine
    if _trigger_engine is None:
        from ..core.alerts import SomaticTriggerEngine
        _trigger_engine = SomaticTriggerEngine()
    return _trigger_engine

@router.post("/webhook/somatic-log")
async def receive_apple_health_data(request: Request):
    """
    Endpoint for receiving health data from Health Auto Export.
    """
    # Imports inside to ensure fast startup
    from ..providers.apple_health import AppleHealthProvider
    
    db = get_db()
    trigger_engine = get_trigger_engine()
    provider = AppleHealthProvider()
    
    try:
        payload = await request.json()
        print(f"--- [WEBHOOK DEBUG] Raw Payload Received ---")
        import json
        print(json.dumps(payload)[:1000]) # Log first 1000 chars
        
        standardized_data = provider.transform_to_standard(payload)
        
        if standardized_data:
            db.insert_biometrics(standardized_data)
            
            # Evaluate real-time triggers
            for entry in standardized_data:
                trigger_engine.evaluate(entry['metric'], entry['val'])
            
        print(f"[{datetime.now()}] Processed {len(standardized_data)} data points from Apple Health.")
        return {"status": "success", "processed_data_points": len(standardized_data)}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "alive"}

@router.get("/dashboard")
async def get_dashboard():
    """
    Serves the interactive High-Contrast State Analyzer.
    """
    from fastapi.responses import HTMLResponse
    from ..core.normalization import SomaticNormalizer
    from ..visualization.dashboard import SomaticDashboard
    from datetime import datetime, timedelta, timezone
    
    db = get_db()
    
    # 1. Fetch last 7 days of data
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=168)
    unified_raw = db.get_data(start, now)
    
    if not unified_raw:
        return HTMLResponse("<html><body><h1>No data found in database for the last 7 days.</h1></body></html>")
    
    # 2. Normalize
    normalizer = SomaticNormalizer()
    df_normalized = normalizer.normalize_to_timeseries(unified_raw)
    
    # 3. Return HTML
    html_content = SomaticDashboard.get_html(df_normalized)
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/sync")
async def trigger_sync():
    """
    Endpoint to trigger a fresh data sync (Oura pull + Unify).
    """
    from ..main import run_pipeline
    try:
        # Run the full 7-day sync
        run_pipeline(hours_back=168)
        return {"status": "success", "message": "7-day sync completed successfully."}
    except Exception as e:
        print(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db-status")
async def db_status():
    """
    Debug endpoint to check database integrity and record counts.
    """
    import os
    db = get_db()
    db._ensure_initialized()
    
    status = {
        "db_path": db.db_path,
        "exists": os.path.exists(db.db_path) if db.db_path else False,
        "size_bytes": os.path.getsize(db.db_path) if db.db_path and os.path.exists(db.db_path) else 0,
        "record_counts": {}
    }
    
    if status["exists"]:
        import sqlite3
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute("SELECT metric, count(*) FROM biometrics GROUP BY metric")
                status["record_counts"] = {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            status["error"] = str(e)
            
    return status
