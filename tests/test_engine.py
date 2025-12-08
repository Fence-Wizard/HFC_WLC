"""Tests for windcalc engine."""

from windcalc import EstimateInput, calculate
from windcalc.engine import calculate_wind_load
from windcalc.schemas import FenceSpecs, WindConditions, WindLoadRequest


def test_calculate_bay_outputs():
    inp = EstimateInput(
        wind_speed_mph=120,
        height_total_ft=8,
        post_spacing_ft=10,
        exposure="C",
    )
    result = calculate(inp)

    assert result.pressure_psf > 0
    assert result.area_per_bay_ft2 == 80
    assert result.total_load_lb > 0
    assert result.load_per_post_lb == result.total_load_lb / 2
    assert result.recommended.post_size
    assert result.assumptions


def test_exposure_factor_increases_pressure():
    base = EstimateInput(
        wind_speed_mph=100,
        height_total_ft=6,
        post_spacing_ft=8,
        exposure="B",
    )
    high = base.model_copy(update={"exposure": "D"})

    base_result = calculate(base)
    high_result = calculate(high)

    assert high_result.pressure_psf > base_result.pressure_psf


def test_warning_triggered_for_tall_fence():
    inp = EstimateInput(
        wind_speed_mph=140,
        height_total_ft=14,
        post_spacing_ft=10,
        exposure="C",
    )
    result = calculate(inp)

    assert any("height exceeds" in w.lower() for w in result.warnings)


def test_legacy_api_still_available():
    fence = FenceSpecs(height=6.0, width=100.0, material="wood", location="Test")
    wind = WindConditions(wind_speed=90.0, exposure_category="B", importance_factor=1.0)
    request = WindLoadRequest(fence=fence, wind=wind, project_name="Test")

    result = calculate_wind_load(request)

    assert result.design_pressure > 0
    assert result.total_load > 0
    assert result.fence_specs == fence
    assert result.wind_conditions == wind
