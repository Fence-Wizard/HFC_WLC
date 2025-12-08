"""Tests for windcalc API."""

from fastapi.testclient import TestClient

from windcalc.api import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_calculate_endpoint_valid():
    """Test calculate endpoint with valid data."""
    request_data = {
        "fence": {
            "height": 6.0,
            "width": 100.0,
            "material": "wood",
            "location": "Test Location",
        },
        "wind": {
            "wind_speed": 90.0,
            "exposure_category": "B",
            "importance_factor": 1.0,
        },
        "project_name": "Test Project",
    }

    response = client.post("/calculate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "design_pressure" in data
    assert "total_load" in data
    assert data["design_pressure"] > 0
    assert data["total_load"] > 0


def test_calculate_endpoint_invalid():
    """Test calculate endpoint with invalid data."""
    request_data = {
        "fence": {
            "height": -1.0,  # Invalid negative height
            "width": 100.0,
            "material": "wood",
            "location": "Test",
        },
        "wind": {"wind_speed": 90.0},
    }

    response = client.post("/calculate", json=request_data)
    assert response.status_code == 422  # Validation error


def test_list_projects_endpoint():
    """Test list projects endpoint."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert isinstance(data["projects"], list)
