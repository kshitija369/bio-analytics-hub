from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI()

# Database file
DB_FILE = "Somatic_Log.db"

@app.post("/webhook/somatic-log")
async def receive_apple_health_data(request: Request):
    """
    Endpoint for receiving health data from Health Auto Export.
    """
    try:
        payload = await request.json()
        
        # Structure from Health Auto Export: {"data": {"metrics": [...]}}
        metrics = payload.get("data", {}).get("metrics", [])
        
        processed_count = 0
        with open(DB_FILE, "a") as f:
            for m in metrics:
                metric_name = m.get('name')
                # Filter for the "Witness State" relevant metrics
                if metric_name in ['heart_rate', 'heart_rate_variability', 'mindful_minutes']:
                    for entry in m.get('data', []):
                        log_entry = {
                            "ts": entry.get('date'),
                            "metric": metric_name,
                            "val": entry.get('qty') or entry.get('avg') or entry.get('value'),
                            "unit": m.get('units'),
                            "source": "AppleWatch_v9"
                        }
                        f.write(json.dumps(log_entry) + "\n")
                        processed_count += 1
                        
        print(f"[{datetime.now()}] Processed {processed_count} data points from {len(metrics)} metrics.")
        return {"status": "success", "processed_data_points": processed_count}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "alive", "db_size": os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0}

if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 allows access from other devices on your local network
    uvicorn.run(app, host="0.0.0.0", port=8000)
