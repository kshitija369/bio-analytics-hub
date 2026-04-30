from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..engine.agent_orchestrator import AgentOrchestrator
from ..core.provenance import ProvenanceLogger
from ..engine.simulation_engine import SimulationEngine
from datetime import datetime
import json
import pandas as pd

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
_sim_engine = SimulationEngine()

# Mock for initial UI development
@router.get("/current_status")
async def get_current_status():
    """
    Returns the user's current 'Existential State' and Agent recommendation.
    In production, this would pull from the latest DB entries and AgentOrchestrator.
    """
    # Simulate some logic
    hour = datetime.now().hour
    
    # Simple logic to match the "Calm Tech" requirement
    if 6 <= hour < 10:
        state = "Rising Phase"
        action = "Deep Work Window: 2 Hours Remaining"
        rationale = "Circadian rhythm indicates peak cortisol and alertness. Ideal for high-cognition tasks."
    elif 10 <= hour < 18:
        state = "Maintenance Phase"
        action = "Steady Focus: Take a 5-min micro-break"
        rationale = "Metabolic state is stable, but cognitive load is accumulating."
    else:
        state = "Restoration Phase"
        action = "Biological Debt High: Suggesting a 15-min walk"
        rationale = "Late glycemic load detected. High risk for autonomic suppression if sedentary."

    return {
        "state": state,
        "recommendation": action,
        "rationale": rationale,
        "context_hash": "mock_hash_123" # In production, this would be a real hash from ProvenanceLogger
    }

@router.get("/provenance/{context_hash}", response_class=HTMLResponse)
async def get_provenance_xray(request: Request, context_hash: str):
    """
    Returns a monospace X-Ray view of the agent's decision-making process.
    """
    # Mock provenance data
    provenance_data = {
        "agent_id": "Secular-Witness-001",
        "timestamp": datetime.now().isoformat(),
        "input_metrics": {
            "HRV": "45ms (-15% vs baseline)",
            "Glucose": "135 mg/dL (Rising)",
            "Sleep_Score": "72 (Sub-optimal)"
        },
        "chain_of_thought": [
            "Detecting sub-optimal sleep recovery from previous night.",
            "Current glucose spike detected after 8 PM.",
            "HRV trend shows sympathetic dominance.",
            "Conclusion: High probability of restorative sleep interference.",
            "Action: Recommend metabolic clearance (walk)."
        ]
    }
    
    return templates.TemplateResponse(request, "partials/provenance_xray.html", {
        "provenance": provenance_data
    })

@router.post("/simulate", response_class=HTMLResponse)
async def simulate_impact(request: Request):
    """
    Recalculates predictive math based on user inputs and returns a badge snippet.
    """
    form_data = await request.form()
    meal_time = int(form_data.get("meal_time", 18)) # Hour of last meal
    post_meal_walk = form_data.get("post_meal_walk") == "on"
    
    events = []
    # Add meal event
    events.append({
        "event": "meal",
        "time": f"{meal_time:02d}:00",
        "carbs": 60 # Assume standard meal for now
    })
    
    if post_meal_walk:
        events.append({
            "event": "nature",
            "duration_mins": 20
        })

    # Mock history for simulation
    history_df = pd.DataFrame({
        "heart_rate": [65],
        "heart_rate_variability": [55],
        "blood_glucose": [98]
    }, index=[pd.Timestamp.now()])
    
    results = _sim_engine.predict_next_24h(history_df, events)
    
    # Return a reactive badge
    color_class = "text-emerald-500" if results["predicted_readiness"] > 80 else "text-amber-500"
    if results["predicted_readiness"] < 60:
        color_class = "text-rose-500"

    return f"""
    <div id="readiness-badge" class="flex flex-col items-center animate-in fade-in zoom-in duration-500">
        <span class="font-mono text-[10px] uppercase tracking-widest text-zinc-500 mb-1">Projected Readiness</span>
        <span class="font-serif text-4xl {color_class}">{results["predicted_readiness"]}</span>
        <span class="font-mono text-[10px] text-zinc-600 mt-2">Predicted for Tomorrow</span>
    </div>
    """
