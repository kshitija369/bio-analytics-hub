from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from ..engine.registry import ExperimentRegistry
from ..engine.research_coordinator import ResearchCoordinator
import os

router = APIRouter()
# Template path relative to the app root
templates = Jinja2Templates(directory="app/templates")

_registry = ExperimentRegistry()
_coordinator = ResearchCoordinator()

@router.get("/")
async def experiments_hub(request: Request, start: str = None, end: str = None):
    """The Research Hub (Main Dashboard)."""
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None

    experiments = _registry.get_all_experiments()
    # Add metrics for each experiment for the hub view
    valid_experiments = []
    for e in experiments:
        exp_id = e.get('id')
        if not exp_id:
            continue
        e['metrics'] = _coordinator.get_aggregated_metrics(exp_id, start_dt, end_dt)
        valid_experiments.append(e)
        
    return templates.TemplateResponse(request, "main_hub.html", {
        "experiments": valid_experiments
    })

@router.get("/analytical")
async def analytical_hub(request: Request, start: str = None, end: str = None):
    """The Analytical Continuous Monitoring Dashboard (Legacy Style)."""
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None

    experiments = _registry.get_all_experiments()
    valid_experiments = []
    for e in experiments:
        exp_id = e.get('id')
        if not exp_id:
            continue
        e['metrics'] = _coordinator.get_aggregated_metrics(exp_id, start_dt, end_dt)
        valid_experiments.append(e)
        
    return templates.TemplateResponse(request, "analytical_hub.html", {
        "experiments": valid_experiments
    })

@router.get("/{experiment_id}")
async def experiment_detail(request: Request, experiment_id: str, start: str = None, end: str = None):
    """The Individual Experiment Detail View (Analytical Dashboard)."""
    from datetime import date
    start_dt = date.fromisoformat(start) if start else None
    end_dt = date.fromisoformat(end) if end else None

    protocol = _registry.get_experiment_by_id(experiment_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    metrics = _coordinator.get_aggregated_metrics(experiment_id, start_dt, end_dt)
    results = _coordinator.get_experiment_results(experiment_id, start_dt, end_dt)
    
    return templates.TemplateResponse(request, "experiment_detail.html", {
        "protocol": protocol,
        "metrics": metrics,
        "results": results
    })
