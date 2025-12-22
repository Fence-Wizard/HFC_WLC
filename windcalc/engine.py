"""Wind load calculation engine."""

from __future__ import annotations

import os
import warnings
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
    SharedResult,
    BlockResult,
    WindConditions,
    WindLoadRequest,
    WindLoadResult,
)

# Placeholder constants - replace with proper ASCE 7 calculations for production use
VELOCITY_PRESSURE_COEFFICIENT = 0.00256
DESIGN_PRESSURE_MULTIPLIER = 1.2  # Simplified multiplier - replace with proper Cf coefficients
EXPOSURE_FACTORS: Dict[str, float] = {"B": 0.7, "C": 1.0, "D": 1.15}

_LEGACY_POST_SIZE_TO_KEY: Dict[str, str] = {
    # Legacy wizard strings (kept only for backward compatibility)
    '2-3/8" SS40': "2_3_8_SS40",
    '2-7/8" SS40': "2_7_8_SS40",
    '3-1/2" SS40': "3_1_2_SS40",
    '1 7/8" Steel Pipe': "1_7_8_PIPE",
    '2 3/8" Steel Pipe': "2_3_8_SS40",
    '2 7/8" Steel Pipe': "2_7_8_SS40",
    '3 1/2" Steel Pipe': "3_1_2_SS40",
    '4" Steel Pipe': "4_0_PIPE",
    '6 5/8" Steel Pipe': "6_5_8_PIPE",
    '8 5/8" Steel Pipe': "8_5_8_PIPE",
    '1 7/8" x 1 5/8" x .105" C-Shape': "C_1_7_8_X_1_5_8_X_105",
    '1 7/8" x 1 5/8" x .121" C-Shape': "C_1_7_8_X_1_5_8_X_121",
    '2 1/4" x 1 5/8" x .121" C-Shape': "C_2_1_4_X_1_5_8_X_121",
    '3 1/4" x 2 1/2" x .130" C-Shape': "C_3_1_4_X_2_1_2_X_130",
    # Additional legacy display variants observed in templates/UI/docs
    '1 7/8" x 1 5/8" x 0.105" C-Shape': "C_1_7_8_X_1_5_8_X_105",
    '1 7/8" x 1 5/8" x 0.121" C-Shape': "C_1_7_8_X_1_5_8_X_121",
    '2 1/4" x 1 5/8" x 0.121" C-Shape': "C_2_1_4_X_1_5_8_X_121",
    '3 1/4" x 2 1/2" x 0.130" C-Shape': "C_3_1_4_X_2_1_2_X_130",
    '1-7/8" Steel Pipe': "1_7_8_PIPE",
    '2-3/8" Steel Pipe': "2_3_8_SS40",
    '2-7/8" Steel Pipe': "2_7_8_SS40",
    '3-1/2" Steel Pipe': "3_1_2_SS40",
    '4.0" Steel Pipe': "4_0_PIPE",
    '6-5/8" Steel Pipe': "6_5_8_PIPE",
    '8-5/8" Steel Pipe': "8_5_8_PIPE",
}

_LABEL_TO_KEY: Dict[str, str] = {post.label: key for key, post in POST_TYPES.items()}
_RECOMMENDATION_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (500, "2_3_8_SS40"),
    (1000, "2_7_8_SS40"),
    (float("inf"), "3_1_2_SS40"),
)


def _normalize_post_key(post_size: Optional[str]) -> Optional[str]:
    """Convert any display string (legacy) to a catalog key."""
    if not post_size:
        return None
    # Check if it's already a key
    if post_size in POST_TYPES:
        return post_size
    # Check label-based mapping first, then legacy fallbacks
    normalized = _LABEL_TO_KEY.get(post_size) or _LEGACY_POST_SIZE_TO_KEY.get(post_size)
    if not normalized:
        warnings.warn(f"Unknown post label '{post_size}', falling back to auto selection.")
    return normalized


def _build_recommendation(post_key: str, source_label: Optional[str] = None) -> Recommendation:
    """
    Build a Recommendation from a catalog key, pulling labels/footings from catalogs.
    """
    post = POST_TYPES.get(post_key)
    strict_footing = os.getenv("WINDCALC_STRICT_FOOTING", "").lower() in {"1", "true", "yes"}

    if post is None:
        footing_dia, embedment = (12.0, 30.0)
        label = source_label or post_key
    else:
        label = source_label or post.label
        if post.footing_diameter_in is None or post.footing_embedment_in is None:
            msg = (
                f"Footing data missing for post_key={post_key}; "
                "using conservative default footing 12 in dia x 30 in embedment."
            )
            if strict_footing:
                raise ValueError(msg)
            warnings.warn(msg)
            footing_dia = post.footing_diameter_in or 12.0
            embedment = post.footing_embedment_in or 30.0
        else:
            footing_dia = post.footing_diameter_in
            embedment = post.footing_embedment_in
    return Recommendation(
        post_key=post_key,
        post_label=label,
        post_size=label,  # legacy field mirrors the label for compatibility
        footing_diameter_in=footing_dia,
        embedment_in=embedment,
    )


def _build_recommendation_for_post_key(post_key: str, source: str | None = None) -> Recommendation:
    """Explicit recommendation helper when caller provides a post_key override."""
    post = POST_TYPES.get(post_key)
    label = post.label if post else post_key
    return _build_recommendation(post_key=post_key, source_label=label)


def _recommend_auto_by_load(load_per_post: float) -> Recommendation:
    """Auto-select a post based on load thresholds, returning a post_key-backed recommendation."""
    for limit, key in _RECOMMENDATION_THRESHOLDS:
        if load_per_post < limit:
            return _build_recommendation(key)
    # Fallback (should not happen)
    return _build_recommendation(_RECOMMENDATION_THRESHOLDS[-1][1])


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


def _compute_block(
    role: str,
    post_key: Optional[str],
    load_per_post_lb: float,
    data: EstimateInput,
    exposure_factor: float,
    pressure_psf: float,
    area: float,
    total_load_lb: float,
) -> BlockResult:
    """Compute block results for a given role and post key."""
    warnings_list = _build_warnings(data, pressure_psf, load_per_post_lb)

    effective_key = None
    recommended = None

    if post_key:
        recommended = _build_recommendation_for_post_key(post_key, source="manual")
        effective_key = post_key
    else:
        recommended = _recommend_auto_by_load(load_per_post_lb)
        effective_key = recommended.post_key

    max_spacing_ft: Optional[float] = None
    M_demand_lb_in: Optional[float] = None
    M_allow_lb_in: Optional[float] = None
    moment_ok: Optional[bool] = None

    if effective_key and effective_key in POST_TYPES:
        table_spacing = compute_max_spacing_from_tables(
            post_key=effective_key,
            wind_speed_mph=data.wind_speed_mph,
            height_ft=data.height_total_ft,
        )

        if table_spacing is not None:
            max_spacing_ft = round(table_spacing, 2)
        else:
            max_spacing_ft = round(
                compute_max_spacing_cf(
                    post_key=effective_key,
                    wind_speed_mph=data.wind_speed_mph,
                    exposure=data.exposure.upper(),
                ),
                2,
            )

        if data.post_spacing_ft > max_spacing_ft:
            post = POST_TYPES[effective_key]
            warnings_list.append(
                f"For post {post.label} at {data.wind_speed_mph:.0f} mph and "
                f"exposure {data.exposure}, max recommended spacing is about "
                f"{max_spacing_ft:.2f} ft; current spacing {data.post_spacing_ft:.2f} ft "
                "exceeds this simplified limit."
            )

        M_demand_lb_in, M_allow_lb_in, moment_ok = compute_moment_check(
            post_key=effective_key,
            height_ft=data.height_total_ft,
            load_per_post_lb=load_per_post_lb,
        )

    # Status logic
    status = "GREEN"
    if max_spacing_ft is not None and data.post_spacing_ft > max_spacing_ft:
        status = "RED"
    if role == "terminal" and moment_ok is False:
        status = "RED"
        warnings_list.append(
            "Terminal bending exceeds capacity; increase post size or adjust configuration."
        )

    return BlockResult(
        post_key=effective_key,
        post_label=recommended.post_label if recommended else None,
        recommended=recommended,
        warnings=warnings_list,
        assumptions=_assumptions(data),
        max_spacing_ft=max_spacing_ft,
        M_demand_ft_lb=round(M_demand_lb_in / 12.0, 1) if M_demand_lb_in is not None else None,
        M_allow_ft_lb=round(M_allow_lb_in / 12.0, 1) if M_allow_lb_in is not None else None,
        moment_ok=moment_ok,
        status=status,
    )


def calculate(data: EstimateInput) -> EstimateOutput:
    """
    Calculate bay-level loads with separate line and terminal post results.
    """
    exposure_factor = EXPOSURE_FACTORS.get(data.exposure.upper(), EXPOSURE_FACTORS["C"])
    velocity_pressure = VELOCITY_PRESSURE_COEFFICIENT * (data.wind_speed_mph**2)
    pressure_psf = round(velocity_pressure * DESIGN_PRESSURE_MULTIPLIER * exposure_factor, 2)

    area = data.area_per_bay_ft2
    total_load_lb = round(pressure_psf * area, 2)
    load_per_post_lb = round(total_load_lb / 2, 2)

    # Resolve line/terminal keys (fall back to deprecated single key if provided)
    line_post_key = data.line_post_key or data.post_key
    terminal_post_key = data.terminal_post_key or data.post_key

    shared = SharedResult(
        pressure_psf=pressure_psf,
        area_per_bay_ft2=round(area, 2),
        total_load_lb=total_load_lb,
        load_per_post_lb=load_per_post_lb,
    )

    line_block = _compute_block(
        role="line",
        post_key=line_post_key,
        load_per_post_lb=load_per_post_lb,
        data=data,
        exposure_factor=exposure_factor,
        pressure_psf=pressure_psf,
        area=area,
        total_load_lb=total_load_lb,
    )

    terminal_block = _compute_block(
        role="terminal",
        post_key=terminal_post_key,
        load_per_post_lb=load_per_post_lb,
        data=data,
        exposure_factor=exposure_factor,
        pressure_psf=pressure_psf,
        area=area,
        total_load_lb=total_load_lb,
    )

    overall_status = "GREEN"
    if line_block.status == "RED" or terminal_block.status == "RED":
        overall_status = "RED"
    elif line_block.status == "YELLOW" or terminal_block.status == "YELLOW":
        overall_status = "YELLOW"

    # Legacy compatibility: map to line block
    return EstimateOutput(
        shared=shared,
        line=line_block,
        terminal=terminal_block,
        overall_status=overall_status,
        pressure_psf=shared.pressure_psf,
        area_per_bay_ft2=shared.area_per_bay_ft2,
        total_load_lb=shared.total_load_lb,
        load_per_post_lb=shared.load_per_post_lb,
        recommended=line_block.recommended,
        warnings=(line_block.warnings or []) + (terminal_block.warnings or []),
        assumptions=line_block.assumptions,
        max_spacing_ft=line_block.max_spacing_ft,
        M_demand_ft_lb=line_block.M_demand_ft_lb,
        M_allow_ft_lb=line_block.M_allow_ft_lb,
    )


def _recommend_member_with_override(
    load_per_post: float,
    post_size_override: Optional[str],
    post_key: Optional[str] = None,
) -> Recommendation:
    """
    Choose post + footing.

    - If no override is given, fall back to the load-based auto selector.
    - If an override is given and recognized in POST_TYPES:
        * keep that post size,
        * use its footing from the catalog,
        * and let spacing checks / warnings handle overloads.
    """
    # Explicit post_key wins, regardless of post_size_override
    if post_key and post_key in POST_TYPES:
        return _build_recommendation_for_post_key(post_key, source="manual")

    if not post_size_override or post_size_override.lower() in {"auto", "recommended", ""}:
        # Behavior exactly as before but now returns a post_key-driven recommendation
        return _recommend_auto_by_load(load_per_post)

    # Use post_key if provided, otherwise try to normalize
    normalized_key = post_key or _normalize_post_key(post_size_override)

    if normalized_key and normalized_key in POST_TYPES:
        post = POST_TYPES[normalized_key]
        return _build_recommendation(post_key=normalized_key, source_label=post.label)

    # Unknown string -> fall back
    return _recommend_auto_by_load(load_per_post)


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
