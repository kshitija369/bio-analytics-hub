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
async def experiments_hub(request: Request):
    """The Research Hub (Main Dashboard)."""
    experiments = _registry.get_all_experiments()
    # Add metrics for each experiment for the hub view
    for e in experiments:
        e['metrics'] = _coordinator.get_aggregated_metrics(e['id'])
        
    return templates.TemplateResponse("main_hub.html", {
        "request": request, 
        "experiments": experiments
    })

@router.get("/{experiment_id}")
async def experiment_detail(request: Request, experiment_id: str):
    """The Individual Experiment Detail View (Analytical Dashboard)."""
    protocol = _registry.get_experiment_by_id(experiment_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    metrics = _coordinator.get_aggregated_metrics(experiment_id)
    results = _coordinator.get_experiment_results(experiment_id)
    
    return templates.TemplateResponse("experiment_detail.html", {
        "request": request,
        "protocol": protocol,
        "metrics": metrics,
        "results": results
    })
