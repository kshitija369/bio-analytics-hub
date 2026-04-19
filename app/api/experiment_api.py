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
    synthetic_df = _sim_engine.predict_next_24h(history, events)
    
    if synthetic_df.empty:
        return {"status": "error", "message": "Insufficient history for simulation"}
        
    # 3. Format for UI
    synthetic_df['ts'] = synthetic_df.index.map(lambda x: x.isoformat())
    # Convert index to column for dict conversion
    results = synthetic_df.reset_index().rename(columns={'index':'timestamp'}).to_dict(orient="records")
    
    return {
        "status": "success",
        "experiment_id": experiment_id,
        "prediction": results
    }
