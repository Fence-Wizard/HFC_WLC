"""Tests for FastAPI wizard app."""

from fastapi.testclient import TestClient

from app.application import app

client = TestClient(app)


def test_root_renders_step1():
    response = client.get("/")
    assert response.status_code == 200
    assert "Wind Load Calculator" in response.text
    assert "Step 1" in response.text


def test_step_flow_and_review():
    step2 = client.post(
        "/step2",
        data={
            "zip_code": "12345",
            "risk_category": "III",
            "wind_speed_mph": 110,
            "exposure": "C",
        },
    )
    assert step2.status_code == 200
    assert "Step 2" in step2.text

    step3 = client.post(
        "/step3",
        data={
            "zip_code": "12345",
            "risk_category": "III",
            "wind_speed_mph": 110,
            "exposure": "C",
            "height_total_ft": 8,
            "post_spacing_ft": 10,
        },
    )
    assert step3.status_code == 200
    assert "Step 3" in step3.text

    review = client.post(
        "/review",
        data={
            "zip_code": "12345",
            "risk_category": "III",
            "wind_speed_mph": 110,
            "exposure": "C",
            "height_total_ft": 8,
            "post_spacing_ft": 10,
            "soil_type": "default",
            "job_name": "Test Job",
        },
    )
    assert review.status_code == 200
    assert "Results" in review.text
    assert "Download PDF" in review.text


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_root():
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Windcalc API"


def test_api_calculate():
    payload = {
        "fence": {
            "height": 6.0,
            "width": 100.0,
            "material": "wood",
            "location": "Test",
        },
        "wind": {
            "wind_speed": 90.0,
            "exposure_category": "B",
            "importance_factor": 1.0,
        },
        "project_name": "API Test",
    }
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["design_pressure"] > 0
    assert data["total_load"] > 0


def test_api_concrete_estimate():
    payload = {
        "hole_specs": [
            {
                "post_type": "Line Post",
                "hole_diameter_in": 10,
                "hole_depth_in": 30,
                "hole_count": 10,
            },
            {
                "post_type": "Terminal",
                "hole_diameter_in": 12,
                "hole_depth_in": 36,
                "hole_count": 4,
            },
        ],
        "include_waste": True,
        "waste_percent": 10.0,
    }
    response = client.post("/api/v1/concrete-estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_holes"] == 14
    assert data["total_volume_cy"] > 0
    assert data["bags_60lb"] > 0


def test_concrete_page_renders():
    response = client.get("/concrete")
    assert response.status_code == 200
    assert "Fence Concrete Calculator" in response.text


def test_concrete_review_flow():
    response = client.post(
        "/concrete/review",
        data={
            "post_type": ["Line Post", "Terminal"],
            "hole_diameter_in": ["10", "12"],
            "hole_depth_in": ["30", "36"],
            "hole_count": ["10", "4"],
            "include_waste": "on",
            "waste_percent": "10",
            "project_name": "Concrete Test",
        },
    )
    assert response.status_code == 200
    assert "Concrete Results" in response.text
    assert "Hole Breakdown" in response.text
