"""Tests for windcalc engine."""

import json
from pathlib import Path

import pytest

from windcalc.schemas import FenceSpecs, WindConditions, WindLoadRequest
from windcalc.engine import calculate_wind_load


def test_calculate_wind_load_basic():
    """Test basic wind load calculation."""
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind = WindConditions(wind_speed=90.0, exposure_category="B", importance_factor=1.0)
    request = WindLoadRequest(fence=fence, wind=wind, project_name="Test")

    result = calculate_wind_load(request)

    assert result.design_pressure > 0
    assert result.total_load > 0
    assert result.fence_specs == fence
    assert result.wind_conditions == wind
    assert result.project_name == "Test"


def test_calculate_wind_load_higher_speed():
    """Test that higher wind speed produces higher loads."""
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind_low = WindConditions(wind_speed=70.0)
    wind_high = WindConditions(wind_speed=110.0)

    result_low = calculate_wind_load(WindLoadRequest(fence=fence, wind=wind_low))
    result_high = calculate_wind_load(WindLoadRequest(fence=fence, wind=wind_high))

    assert result_high.design_pressure > result_low.design_pressure
    assert result_high.total_load > result_low.total_load


def test_calculate_wind_load_golden_basic(tmp_path):
    """Test calculation against golden case - basic fence."""
    golden_file = Path(__file__).parent / "golden_cases" / "basic_fence.json"
    with open(golden_file, "r") as f:
        golden = json.load(f)

    input_data = golden["input"]
    fence = FenceSpecs(**input_data["fence"])
    wind = WindConditions(**input_data["wind"])
    request = WindLoadRequest(
        fence=fence, wind=wind, project_name=input_data["project_name"]
    )

    result = calculate_wind_load(request)

    expected = golden["expected_output"]
    assert expected["design_pressure_min"] <= result.design_pressure <= expected["design_pressure_max"]
    assert result.calculation_notes is not None


def test_calculate_wind_load_golden_high_wind(tmp_path):
    """Test calculation against golden case - high wind."""
    golden_file = Path(__file__).parent / "golden_cases" / "high_wind.json"
    with open(golden_file, "r") as f:
        golden = json.load(f)

    input_data = golden["input"]
    fence = FenceSpecs(**input_data["fence"])
    wind = WindConditions(**input_data["wind"])
    request = WindLoadRequest(
        fence=fence, wind=wind, project_name=input_data["project_name"]
    )

    result = calculate_wind_load(request)

    expected = golden["expected_output"]
    assert expected["design_pressure_min"] <= result.design_pressure <= expected["design_pressure_max"]
    assert result.calculation_notes is not None
