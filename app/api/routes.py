from fastapi import APIRouter, Request, HTTPException
from ..core.database import SomaticDatabase
from ..providers.apple_health import AppleHealthProvider
from ..core.alerts import SomaticTriggerEngine
from datetime import datetime

router = APIRouter()
db = SomaticDatabase()
provider = AppleHealthProvider()
trigger_engine = SomaticTriggerEngine()

@router.post("/webhook/somatic-log")
async def receive_apple_health_data(request: Request):
    """
    Endpoint for receiving health data from Health Auto Export.
    """
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
