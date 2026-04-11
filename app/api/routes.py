from fastapi import APIRouter, Request, HTTPException
from ..core.database import SomaticDatabase
from ..providers.apple_health import AppleHealthProvider
from ..core.alerts import SomaticTriggerEngine
from datetime import datetime

print("--- [STARTUP DEBUG] Entering app/api/routes.py ---")

router = APIRouter()

print("--- [STARTUP DEBUG] router initialized ---")

# Lazy initializers to prevent startup crashes
_db = None
_trigger_engine = None

def get_db():
    global _db
    if _db is None:
        _db = SomaticDatabase()
    return _db

def get_trigger_engine():
    global _trigger_engine
    if _trigger_engine is None:
        _trigger_engine = SomaticTriggerEngine()
    return _trigger_engine

@router.post("/webhook/somatic-log")
async def receive_apple_health_data(request: Request):
    """
    Endpoint for receiving health data from Health Auto Export.
    """
    db = get_db()
    trigger_engine = get_trigger_engine()
    provider = AppleHealthProvider()
    
    try:
        payload = await request.json()
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
