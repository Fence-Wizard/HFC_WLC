"""Wind load calculation engine."""

from __future__ import annotations

from typing import Dict, Optional

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

# Post catalog with structural capacities
_POST_CATALOG: Dict[str, Dict[str, float]] = {
    '2-3/8" SS40': {
        "max_load_lb": 700.0,   # allowable load per post (tune from your Excel or PE tables)
        "footing_diameter_in": 12.0,
        "embedment_in": 30.0,
    },
    '2-7/8" SS40': {
        "max_load_lb": 1200.0,
        "footing_diameter_in": 16.0,
        "embedment_in": 36.0,
    },
    '3-1/2" SS40': {
        "max_load_lb": 1800.0,
        "footing_diameter_in": 18.0,
        "embedment_in": 42.0,
    },
}


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

    # Honour post override when selecting member
    post_size_override = getattr(data, "post_size", None)
    recommended = _recommend_member_with_override(load_per_post_lb, post_size_override)

    warnings = _build_warnings(data, pressure_psf, load_per_post_lb)

    # Compute max spacing for a fixed post, if we know its capacity
    max_spacing_ft: Optional[float] = None
    if post_size_override and post_size_override in _POST_CATALOG:
        cap = _POST_CATALOG[post_size_override]["max_load_lb"]
        if pressure_psf > 0 and data.height_total_ft > 0:
            max_spacing_ft = round(
                2 * cap / (pressure_psf * data.height_total_ft),
                2,
            )

            # If current spacing exceeds the computed maximum, flag it
            if data.post_spacing_ft > max_spacing_ft:
                warnings.append(
                    f"At {data.wind_speed_mph:.0f} mph and {data.height_total_ft:.1f} ft, "
                    f'post {post_size_override} should not exceed about {max_spacing_ft:.2f} ft spacing. '
                    f'Current spacing {data.post_spacing_ft:.2f} ft is outside this simplified limit. '
                    "Consider decreasing spacing, increasing post size, or obtaining an engineered design."
                )

    assumptions = _assumptions(data)

    return EstimateOutput(
        pressure_psf=pressure_psf,
        area_per_bay_ft2=round(area, 2),
        total_load_lb=total_load_lb,
        load_per_post_lb=load_per_post_lb,
        recommended=recommended,
        warnings=warnings,
        assumptions=assumptions,
        max_spacing_ft=max_spacing_ft,
    )


def _recommend_member(load_per_post: float) -> Recommendation:
    if load_per_post < 500:
        return Recommendation(post_size="2-3/8\" SS40", footing_diameter_in=10, embedment_in=24)
    if load_per_post < 1000:
        return Recommendation(post_size="2-7/8\" SS40", footing_diameter_in=12, embedment_in=30)
    return Recommendation(post_size="3-1/2\" SS40", footing_diameter_in=16, embedment_in=36)


def _recommend_member_with_override(
    load_per_post: float,
    post_size_override: Optional[str],
) -> Recommendation:
    """
    Choose post + footing.

    - If no override is given, fall back to the existing simplified _recommend_member().
    - If an override is given and recognized in _POST_CATALOG:
        * keep that post size,
        * use its footing from the catalog,
        * and let spacing checks / warnings handle overloads.
    """
    if not post_size_override or post_size_override.lower() in {"auto", "recommended", ""}:
        # Behavior exactly as before
        return _recommend_member(load_per_post)

    cfg = _POST_CATALOG.get(post_size_override)
    if cfg is None:
        # Unknown string -> fall back
        return _recommend_member(load_per_post)

    return Recommendation(
        post_size=post_size_override,
        footing_diameter_in=cfg["footing_diameter_in"],
        embedment_in=cfg["embedment_in"],
    )


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


def _assumptions(data: EstimateInput) -> list[str]:
    assumptions = [
        f"Design wind speed V = {data.wind_speed_mph} mph "
        "(3-sec gust at 33 ft), provided by user from ASCE wind maps "
        "and/or project drawings.",
        "Loads based on simplified ASCE 7-inspired velocity pressure equation.",
        "Exposure factors are approximations for demo purposes.",
        "Uniform pressure distribution assumed across the bay.",
    ]
    return assumptions


__all__ = [
    "calculate",
    "calculate_wind_load",
]
