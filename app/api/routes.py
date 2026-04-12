from fastapi import APIRouter, Request, HTTPException
from datetime import datetime

router = APIRouter()

# Lazy initializers
_db = None
_trigger_engine = None

def get_db():
    global _db
    if _db is None:
        from ..core.database import BiometricDatabase
        _db = BiometricDatabase()
    return _db

def get_trigger_engine():
    global _trigger_engine
    if _trigger_engine is None:
        from ..core.alerts import BiometricTriggerEngine
        _trigger_engine = BiometricTriggerEngine()
    return _trigger_engine

@router.post("/webhook/biometric-log", tags=["Ingestion"])
async def receive_apple_health_data(request: Request):
    """
    ### Apple Health Webhook (Auto-Export)
    Receiver for high-resolution 1-minute biometric data from Apple Watch.
    - **Validates**: Standard metric names.
    - **Triggers**: Real-time haptic prompts if thresholds are exceeded.
    """
    # Imports inside to ensure fast startup
    from ..adapters.apple_health import AppleHealthProvider
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
                trigger_engine.evaluate(entry['metric'], entry['val'], timestamp=entry['ts'])
            
        print(f"[{datetime.now()}] Processed {len(standardized_data)} data points from Apple Health.")
        return {"status": "success", "processed_data_points": len(standardized_data)}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "alive"}

@router.get("/dashboard", tags=["Research"])
async def get_dashboard():
    """
    ### High-Contrast Biometric Dashboard
    Serves the primary unified dashboard showing Heart Rate, HRV, and State Decryption.
    """
    from fastapi.responses import HTMLResponse
    from ..core.normalization import BiometricNormalizer
    from ..visualization.dashboard import BiometricDashboard
    from datetime import datetime, timedelta, timezone
    
    db = get_db()
    
    # 1. Fetch last 7 days of data
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=168)
    unified_raw = db.get_data(start, now)
    
    if not unified_raw:
        return HTMLResponse("<html><body><h1>No data found in database for the last 7 days.</h1></body></html>")
    
    # 2. Normalize
    normalizer = BiometricNormalizer()
    df_normalized = normalizer.normalize_to_timeseries(unified_raw)
    
    # 3. Return HTML
    html_content = BiometricDashboard.get_html(df_normalized)
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/sync", tags=["Ingestion"])
async def trigger_sync(days: int = 7):
    """
    ### Oura V2 Sync
    Triggers a manual pull of Oura high-resolution data and daily aggregates.
    """
    from ..main import run_pipeline
    try:
        # Calculate hours back
        hours = days * 24
        run_pipeline(hours_back=hours)
        return {"status": "success", "message": f"{days}-day sync completed successfully."}
    except Exception as e:
        print(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db-status", tags=["Diagnostics"])
async def db_status():
    """
    ### Database Integrity Check
    Returns record counts across all biometric and research tables.
    """
    import os
    db = get_db()
    # CRITICAL: Initialize first to set db_path attributes
    db._ensure_initialized()
    
    status = {
        "db_path": db.db_path,
        "exists": os.path.exists(db.db_path) if db.db_path else False,
        "size_bytes": os.path.getsize(db.db_path) if db.db_path and os.path.exists(db.db_path) else 0,
        "record_counts": {},
        "experiment_counts": {}
    }
    
    if status["exists"]:
        import sqlite3
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute("SELECT metric, count(*) FROM biometrics GROUP BY metric")
                status["record_counts"] = {row[0]: row[1] for row in cursor.fetchall()}
                
                exp_cursor = conn.execute("SELECT experiment_id, count(*) FROM experiment_results GROUP BY experiment_id")
                status["experiment_counts"] = {row[0]: row[1] for row in exp_cursor.fetchall()}
                
                res_cursor = conn.execute("SELECT experiment_id, count(*) FROM research_results GROUP BY experiment_id")
                status["research_counts"] = {row[0]: row[1] for row in res_cursor.fetchall()}
        except Exception as e:
            status["error"] = str(e)
            
    return status

@router.get("/experiments/evaluate", tags=["Research API"])
async def evaluate_experiments(experiment_id: str = "EXP-NAR-001", target_date: str = None, days_back: int = 0):
    """
    ### Trigger Study Evaluation
    Runs the inference logic (e.g., Z-Score, Dip Calculation) for a specific study.
    """

    from ..engine.experiment_manager import ExperimentManager
    from datetime import date, timedelta
    
    manager = ExperimentManager()
    
    if target_date:
        base_date = date.fromisoformat(target_date)
    else:
        base_date = date.today()
        
    results = []
    # Limit to 14 days per request to prevent timeouts on Cloud Run
    safe_days = min(days_back, 14)
    if days_back > 14:
        print(f"--- [Notice] days_back {days_back} exceeds safety limit. Processing latest 14 days only. ---")

    for i in range(safe_days, -1, -1):
        eval_date = base_date - timedelta(days=i)
        try:
            res = manager.evaluate_experiment_for_date(experiment_id, eval_date)
            if res:
                results.append(res)
        except Exception as e:
            print(f"Error evaluating {experiment_id} for {eval_date}: {e}")
            
    if results:
        return {"status": "success", "evaluations": len(results), "latest_result": results[-1]}
    else:
        return {"status": "no_data", "message": f"No data available for experiment {experiment_id} in the requested window."}

@router.get("/test-oura", tags=["System Diagnostics"])
async def test_oura_connectivity():
    """
    ### Live Oura API Handshake
    Diagnostic endpoint to verify authentication and data visibility.
    """
    import requests
    import os
    pat = os.environ.get("OURA_PAT", "")
    headers = {'Authorization': f'Bearer {pat.strip()}'}
    
    results = {}
    
    # 1. Test Readiness
    try:
        url = "https://api.ouraring.com/v2/usercollection/daily_readiness"
        resp = requests.get(url, headers=headers, params={'start_date': '2026-04-10', 'end_date': '2026-04-10'}, timeout=10)
        results["readiness"] = list(resp.json().get('data', [{}])[0].keys()) if resp.status_code == 200 else resp.text
    except Exception as e:
        results["readiness_error"] = str(e)

    # 2. Test Sleep (High-Res HRV source)
    try:
        url = "https://api.ouraring.com/v2/usercollection/sleep"
        resp = requests.get(url, headers=headers, params={'start_date': '2026-04-10', 'end_date': '2026-04-10'}, timeout=10)
        if resp.status_code == 200 and resp.json().get('data'):
            sleep_entry = resp.json()['data'][0]
            results["sleep_keys"] = list(sleep_entry.keys())
            if 'hrv' in sleep_entry:
                results["hrv_keys"] = list(sleep_entry['hrv'].keys())
        else:
            results["sleep_status"] = resp.status_code
            results["sleep_payload"] = resp.text
    except Exception as e:
        results["sleep_error"] = str(e)
        
    return results
