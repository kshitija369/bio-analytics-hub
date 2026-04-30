import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ambient_status_endpoint():
    """Verify that the current_status endpoint returns the expected 'Existential State' keys."""
    response = client.get("/api/ui/current_status")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "recommendation" in data
    assert "rationale" in data
    assert "context_hash" in data
    assert isinstance(data["state"], str)

def test_provenance_xray_endpoint():
    """Verify that the provenance endpoint returns HTML with the expected X-Ray trace markers."""
    response = client.get("/api/ui/provenance/mock_hash_123")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    content = response.text
    assert "Agent Decision Trace (X-RAY)" in content
    assert "AGENT_ID" in content
    assert "CHAIN_OF_THOUGHT" in content
    assert "Secular-Witness-001" in content

def test_simulate_impact_endpoint():
    """Verify that the simulate endpoint processes form data and returns a reactive HTML badge."""
    # Test high readiness scenario (Early meal, walk)
    response = client.post("/api/ui/simulate", data={
        "meal_time": "18",
        "post_meal_walk": "on"
    })
    assert response.status_code == 200
    assert "Projected Readiness" in response.text
    # Check for emerald color (higher readiness)
    assert "text-emerald-500" in response.text

    # Test lower readiness scenario (Late meal, no walk)
    response_late = client.post("/api/ui/simulate", data={
        "meal_time": "22",
        "post_meal_walk": "off"
    })
    assert response_late.status_code == 200
    assert "text-amber-500" in response_late.text or "text-rose-500" in response_late.text

def test_main_hub_rendering():
    """Verify the main hub renders with the required HTMX and Tailwind references."""
    response = client.get("/")
    assert response.status_code == 200
    assert "htmx.org" in response.text
    assert "tailwindcss.com" in response.text
    assert "hx-get=\"/api/ui/current_status\"" in response.text
    assert "font-serif" in response.text
    assert "font-mono" in response.text
