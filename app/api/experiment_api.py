from fastapi import APIRouter, HTTPException, Request
from ..engine.registry import ExperimentRegistry
from ..engine.research_coordinator import ResearchCoordinator
from ..engine.simulation_engine import SimulationEngine
from typing import List, Dict, Any

router = APIRouter()
_registry = ExperimentRegistry()
_coordinator = ResearchCoordinator()
_sim_engine = SimulationEngine()

@router.get("/", tags=["Research API"])
async def list_experiments() -> List[Dict[str, Any]]:
    """
    ### List All Experiments
    Retrieves metadata for all defined research protocols.
    """
    return _registry.get_all_experiments()

@router.get("/migrate", tags=["Research API"])
async def migrate_experiment_data():
    """
    ### Data Migration: NAR -> SRI
    Renames all historical records from EXP-NAR-001 to EXP-SRI-001.
    """
    from ..api.routes import get_db
    from fastapi import HTTPException
    db = get_db()
    db._ensure_initialized()
    import sqlite3
    try:
        with sqlite3.connect(db.db_path) as conn:
            # 1. Update research_results table
            res1 = conn.execute("UPDATE research_results SET experiment_id = 'EXP-SRI-001' WHERE experiment_id = 'EXP-NAR-001'")
            # 2. Update experiment_results table
            res2 = conn.execute("UPDATE experiment_results SET experiment_id = 'EXP-SRI-001' WHERE experiment_id = 'EXP-NAR-001'")
            conn.commit()
            return {
                "status": "success", 
                "message": "Migration complete", 
                "research_updated": res1.rowcount,
                "experiments_updated": res2.rowcount
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{experiment_id}", tags=["Research API"])
async def get_experiment(experiment_id: str, start: str = None, end: str = None) -> Dict[str, Any]:
    """
    ### Get Study Protocol & Aggregate Metrics
    Returns the hypothesis, variables, and calculated correlation ($r$) for a specific study.
    - **Calculates**: Pearson Correlation and Mean Absolute Error on the fly.
    - **Zoom**: Filters metrics based on optional start/end dates.
    """
    proto = _registry.get_experiment_by_id(experiment_id)
    if not proto:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None
    
    metrics = _coordinator.get_aggregated_metrics(experiment_id, start_dt, end_dt)
    return {
        "protocol": proto,
        "metrics": metrics
    }

@router.get("/{experiment_id}/results", tags=["Research API"])
async def get_results(experiment_id: str, start: str = None, end: str = None) -> List[Dict[str, Any]]:
    """
    ### Fetch Raw Research Results
    Retrieves the time-series dimension data (Independent vs. Dependent) for visualization.
    """
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None
    return _coordinator.get_experiment_results(experiment_id, start_dt, end_dt)

@router.post("/{experiment_id}/simulate", tags=["Predictive Sandbox"])
async def simulate_future(experiment_id: str, request: Request):
    """
    ### DT4H-Sim: Generate Synthetic Trajectory
    Accepts prospective events and returns a predicted 24-hour physiological trajectory.
    """
    payload = await request.json()
    events = payload.get("events", [])
    
    # 1. Fetch recent history for baseline
    from datetime import datetime, timedelta
    from app.domain.dimension_repository import DimensionRepository
    repo = DimensionRepository()
    
    now = datetime.now()
    history = repo.get_dimension_data("HeartRate", now - timedelta(days=7), now)
    
    # 2. Run Simulation
    sim_result = _sim_engine.predict_next_24h(history, events)
    
    if sim_result.get("status") == "error":
        return {"status": "error", "message": sim_result.get("message")}
        
    return {
        "status": "success",
        "experiment_id": experiment_id,
        "prediction": sim_result["time_series"],
        "predicted_score": sim_result["predicted_readiness"],
        "predicted_hrv": sim_result["predicted_hrv_avg"]
    }
