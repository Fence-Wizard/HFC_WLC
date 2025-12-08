"""Tests for windcalc schemas."""

import pytest
from pydantic import ValidationError

from windcalc.schemas import (
    FenceSpecs,
    WindConditions,
    WindLoadRequest,
    WindLoadResult,
)


def test_fence_specs_valid():
    """Test valid FenceSpecs creation."""
    fence = FenceSpecs(
        height=6.0, width=100.0, material="wood", location="Test Location"
    )
    assert fence.height == 6.0
    assert fence.width == 100.0
    assert fence.material == "wood"
    assert fence.location == "Test Location"


def test_fence_specs_invalid_height():
    """Test FenceSpecs with invalid height."""
    with pytest.raises(ValidationError):
        FenceSpecs(height=-1.0, width=100.0, material="wood", location="Test")


def test_wind_conditions_valid():
    """Test valid WindConditions creation."""
    wind = WindConditions(
        wind_speed=90.0, exposure_category="B", importance_factor=1.0
    )
    assert wind.wind_speed == 90.0
    assert wind.exposure_category == "B"
    assert wind.importance_factor == 1.0


def test_wind_conditions_defaults():
    """Test WindConditions with default values."""
    wind = WindConditions(wind_speed=90.0)
    assert wind.exposure_category == "B"
    assert wind.importance_factor == 1.0


def test_wind_load_request_valid():
    """Test valid WindLoadRequest creation."""
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind = WindConditions(wind_speed=90.0)
    request = WindLoadRequest(
        fence=fence, wind=wind, project_name="Test Project"
    )
    assert request.fence == fence
    assert request.wind == wind
    assert request.project_name == "Test Project"


def test_wind_load_result_valid():
    """Test valid WindLoadResult creation."""
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind = WindConditions(wind_speed=90.0)
    result = WindLoadResult(
        design_pressure=25.0,
        total_load=15000.0,
        fence_specs=fence,
        wind_conditions=wind,
    )
    assert result.design_pressure == 25.0
    assert result.total_load == 15000.0
