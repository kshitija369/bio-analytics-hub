import os
import sys
from datetime import datetime, timedelta, timezone
from app.providers.oura import OuraProvider
from app.core.database import SomaticDatabase

def bulk_load(days_back=90):
    print(f"--- Starting Bulk Hydration: Last {days_back} days ---")
    
    db = SomaticDatabase()
    oura = OuraProvider()
    
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    
    # 1. Fetch Data
    # Note: Oura fetch_data handles daily chunks internally
    print(f"Fetching Oura data from {start.date()} to {now.date()}...")
    raw_data = oura.fetch_data(start, now)
    
    if not raw_data:
        print("No data retrieved. Check your OURA_PAT.")
        return

    # 2. Transform & Persist
    standardized = oura.transform_to_standard(raw_data)
    print(f"Standardized {len(standardized)} biometric records.")
    
    if standardized:
        db.insert_biometrics(standardized)
        print("Successfully persisted historical data to Somatic Log.")
    
    print("--- Hydration Complete ---")

if __name__ == "__main__":
    # Ensure app is in path
    sys.path.append(os.getcwd())
    
    days = 90
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
        
    bulk_load(days)
