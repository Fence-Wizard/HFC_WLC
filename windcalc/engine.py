"""Wind load calculation engine."""

from __future__ import annotations

from typing import Dict, Optional

from windcalc.post_catalog import (
    POST_TYPES,
    compute_max_spacing_cf,
    compute_max_spacing_from_tables,
    compute_moment_check,
)
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

# Mapping from old display format to new catalog keys
_POST_SIZE_TO_KEY: Dict[str, str] = {
    '2-3/8" SS40': "2_3_8_SS40",
    '2-7/8" SS40': "2_7_8_SS40",
    '3-1/2" SS40': "3_1_2_SS40",
    # New pipe options (what PMs will see in the dropdown)
    '1 7/8" Steel Pipe': "1_7_8_PIPE",
    '2 3/8" Steel Pipe': "2_3_8_SS40",  # synonym
    '2 7/8" Steel Pipe': "2_7_8_SS40",  # synonym
    '3 1/2" Steel Pipe': "3_1_2_SS40",  # synonym
    '4" Steel Pipe': "4_0_PIPE",
    '6 5/8" Steel Pipe': "6_5_8_PIPE",
    '8 5/8" Steel Pipe': "8_5_8_PIPE",
    # New C-shapes
    '1 7/8" x 1 5/8" x .105" C-Shape': "C_1_7_8_X_1_5_8_X_105",
    '1 7/8" x 1 5/8" x .121" C-Shape': "C_1_7_8_X_1_5_8_X_121",
    '2 1/4" x 1 5/8" x .121" C-Shape': "C_2_1_4_X_1_5_8_X_121",
    '3 1/4" x 2 1/2" x .130" C-Shape': "C_3_1_4_X_2_1_2_X_130",
}


def _normalize_post_key(post_size: Optional[str]) -> Optional[str]:
    """Convert display format post size to catalog key."""
    if not post_size:
        return None
    # Check if it's already a key
    if post_size in POST_TYPES:
        return post_size
    # Check if it's in the mapping
    return _POST_SIZE_TO_KEY.get(post_size)


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
    post_key = _normalize_post_key(post_size_override)
    recommended = _recommend_member_with_override(load_per_post_lb, post_size_override, post_key)

    warnings = _build_warnings(data, pressure_psf, load_per_post_lb)

    # Compute max spacing using Cf-based method if post is specified
    max_spacing_ft: Optional[float] = None
    M_demand_lb_in: Optional[float] = None
    M_allow_lb_in: Optional[float] = None
    moment_ok: bool = True

    if post_key and post_key in POST_TYPES:
        # Try table-based value first (more accurate)
        table_spacing = compute_max_spacing_from_tables(
            post_key=post_key,
            wind_speed_mph=data.wind_speed_mph,
            height_ft=data.height_total_ft,
        )

        if table_spacing is not None:
            max_spacing_ft = round(table_spacing, 2)
        else:
            # Fallback to Cf-based approximation if tables are missing
            max_spacing_ft = round(
                compute_max_spacing_cf(
                    post_key=post_key,
                    wind_speed_mph=data.wind_speed_mph,
                    exposure=data.exposure.upper(),
                ),
                2,
            )

        # If current spacing exceeds the computed maximum, flag it
        if data.post_spacing_ft > max_spacing_ft:
            post = POST_TYPES[post_key]
            warnings.append(
                f"For post {post.label} at {data.wind_speed_mph:.0f} mph and "
                f"exposure {data.exposure}, max recommended spacing is about "
                f"{max_spacing_ft:.2f} ft; current spacing {data.post_spacing_ft:.2f} ft "
                "exceeds this simplified limit."
            )

        # Bending moment check
        M_demand_lb_in, M_allow_lb_in, moment_ok = compute_moment_check(
            post_key=post_key,
            height_ft=data.height_total_ft,
            load_per_post_lb=load_per_post_lb,
        )

        if not moment_ok:
            post = POST_TYPES[post_key]
            warnings.append(
                "Simplified bending check indicates the post is above its bending capacity: "
                f"{M_demand_lb_in/12:.1f} ft·lb demand vs "
                f"{M_allow_lb_in/12:.1f} ft·lb simplified capacity for post {post.label} "
                f"({post.fy_ksi:.0f} ksi steel). Consider increasing post size or seeking PE review."
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
        M_demand_ft_lb=round(M_demand_lb_in / 12.0, 1) if M_demand_lb_in is not None else None,
        M_allow_ft_lb=round(M_allow_lb_in / 12.0, 1) if M_allow_lb_in is not None else None,
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
    post_key: Optional[str] = None,
) -> Recommendation:
    """
    Choose post + footing.

    - If no override is given, fall back to the existing simplified _recommend_member().
    - If an override is given and recognized in POST_TYPES:
        * keep that post size,
        * use its footing from the catalog,
        * and let spacing checks / warnings handle overloads.
    """
    if not post_size_override or post_size_override.lower() in {"auto", "recommended", ""}:
        # Behavior exactly as before
        return _recommend_member(load_per_post)

    # Use post_key if provided, otherwise try to normalize
    if not post_key:
        post_key = _normalize_post_key(post_size_override)

    if post_key and post_key in POST_TYPES:
        post = POST_TYPES[post_key]
        # Use default footing values from old catalog for now
        # These should eventually come from POST_TYPES or a separate footing catalog
        footing_map = {
            "2_3_8_SS40": (12.0, 30.0),
            "2_7_8_SS40": (16.0, 36.0),
            "3_1_2_SS40": (18.0, 42.0),
        }
        footing_dia, embedment = footing_map.get(post_key, (12.0, 30.0))

        return Recommendation(
            post_size=post_size_override,  # Keep original display format
            footing_diameter_in=footing_dia,
            embedment_in=embedment,
        )

    # Unknown string -> fall back
    return _recommend_member(load_per_post)


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
