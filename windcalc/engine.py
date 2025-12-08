"""Wind load calculation engine."""

from __future__ import annotations

from typing import Dict

from windcalc.schemas import (
    EstimateInput,
    EstimateOutput,
    Recommendation,
    WindConditions,
    WindLoadRequest,
    WindLoadResult,
)

# Placeholder constants - replace with proper ASCE 7 calculations for production use
VELOCITY_PRESSURE_COEFFICIENT = 0.00256
DESIGN_PRESSURE_MULTIPLIER = 1.2  # Simplified multiplier - replace with proper Cf coefficients
EXPOSURE_FACTORS: Dict[str, float] = {"B": 0.7, "C": 1.0, "D": 1.15}


def calculate_wind_load(request: WindLoadRequest) -> WindLoadResult:
    """
    Calculate wind load for a fence project (legacy API).

    This is a simplified placeholder implementation. The actual calculation should follow
    relevant building codes (ASCE 7, etc.) for wind load on fences.
    """

    wind_speed = request.wind.wind_speed
    importance = request.wind.importance_factor

    velocity_pressure = VELOCITY_PRESSURE_COEFFICIENT * (wind_speed**2) * importance
    design_pressure = velocity_pressure * DESIGN_PRESSURE_MULTIPLIER

    fence_area = request.fence.height * request.fence.width
    total_load = design_pressure * fence_area

    return WindLoadResult(
        project_name=request.project_name,
        design_pressure=round(design_pressure, 2),
        total_load=round(total_load, 2),
        fence_specs=request.fence,
        wind_conditions=request.wind,
        calculation_notes=(
            "Simplified placeholder calculation - "
            "replace with ASCE 7 compliant implementation"
        ),
    )


def calculate(data: EstimateInput) -> EstimateOutput:
    """
    Calculate bay-level loads for the wizard-friendly workflow.

    The math intentionally mirrors the legacy placeholder logic but returns
    structured outputs used by the FastAPI wizard. All values are rounded to
    sensible precision for display purposes.
    """

    exposure_factor = EXPOSURE_FACTORS.get(data.exposure.upper(), EXPOSURE_FACTORS["C"])
    velocity_pressure = VELOCITY_PRESSURE_COEFFICIENT * (data.wind_speed_mph**2)
    pressure_psf = round(velocity_pressure * DESIGN_PRESSURE_MULTIPLIER * exposure_factor, 2)

    area = data.area_per_bay_ft2
    total_load_lb = round(pressure_psf * area, 2)
    load_per_post_lb = round(total_load_lb / 2, 2)

    recommended = _recommend_member(load_per_post_lb)
    warnings = _build_warnings(data, pressure_psf, load_per_post_lb)
    assumptions = _assumptions()

    return EstimateOutput(
        pressure_psf=pressure_psf,
        area_per_bay_ft2=round(area, 2),
        total_load_lb=total_load_lb,
        load_per_post_lb=load_per_post_lb,
        recommended=recommended,
        warnings=warnings,
        assumptions=assumptions,
    )


def _recommend_member(load_per_post: float) -> Recommendation:
    if load_per_post < 500:
        return Recommendation(post_size="2-3/8\" SS40", footing_diameter_in=10, embedment_in=24)
    if load_per_post < 1000:
        return Recommendation(post_size="2-7/8\" SS40", footing_diameter_in=12, embedment_in=30)
    return Recommendation(post_size="3-1/2\" SS40", footing_diameter_in=16, embedment_in=36)


def _build_warnings(data: EstimateInput, pressure: float, load_per_post: float) -> list[str]:
    warnings: list[str] = []
    if data.height_total_ft > 12:
        warnings.append("Fence height exceeds common tabulated limits; PE review recommended.")
    if data.wind_speed_mph > 150:
        warnings.append("Wind speed beyond standard tables; verify with local code official.")
    if pressure > 60:
        warnings.append("Calculated pressure is very high; check exposure and risk category.")
    if load_per_post > 2000:
        warnings.append("Post load exceeds simplified recommendations.")
    return warnings


def _assumptions() -> list[str]:
    return [
        "Loads based on simplified ASCE 7-inspired velocity pressure equation.",
        "Exposure factors are approximations for demo purposes.",
        "Uniform pressure distribution assumed across the bay.",
    ]


__all__ = [
    "calculate",
    "calculate_wind_load",
]
