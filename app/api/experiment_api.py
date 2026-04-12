from fastapi import APIRouter, HTTPException
from ..engine.registry import ExperimentRegistry
from ..engine.research_coordinator import ResearchCoordinator
from typing import List, Dict, Any

router = APIRouter()
_registry = ExperimentRegistry()
_coordinator = ResearchCoordinator()

@router.get("/")
async def list_experiments() -> List[Dict[str, Any]]:
    """Returns metadata for all experiments."""
    return _registry.get_all_experiments()

@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, start: str = None, end: str = None) -> Dict[str, Any]:
    """Returns protocol and aggregated results for a specific experiment."""
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

@router.get("/{experiment_id}/results")
async def get_results(experiment_id: str, start: str = None, end: str = None) -> List[Dict[str, Any]]:
    """Returns raw time-series results for an experiment."""
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None
    return _coordinator.get_experiment_results(experiment_id, start_dt, end_dt)
