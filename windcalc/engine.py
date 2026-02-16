"""Wind load calculation engine.

Uses ASCE 7-22 velocity pressure and force coefficients for
freestanding fences and walls.  See :mod:`windcalc.asce7` for the
underlying equations and constants.
"""

from __future__ import annotations

import logging
import warnings

from windcalc.asce7 import FENCE_TYPES as ASCE_FENCE_TYPES
from windcalc.asce7 import compute_design_pressure
from windcalc.footing import compute_footing_check
from windcalc.post_catalog import (
    POST_TYPES,
    compute_deflection_check,
    compute_max_spacing_cf,
    compute_max_spacing_from_tables,
    compute_moment_check,
)
from windcalc.quantities import compute_segment_quantities
from windcalc.schemas import (
    BlockResult,
    DeflectionResult,
    DesignParameters,
    EstimateInput,
    EstimateOutput,
    FootingResult,
    ProjectInput,
    ProjectOutput,
    QuantitiesResult,
    Recommendation,
    SegmentOutput,
    SharedResult,
    WindLoadRequest,
    WindLoadResult,
)
from windcalc.settings import get_settings

logger = logging.getLogger(__name__)

# Legacy constants (used ONLY by deprecated calculate_wind_load)
_LEGACY_QZ_COEFF = 0.00256
_LEGACY_PRESSURE_MULT = 1.2
_LEGACY_EXPOSURE: dict[str, float] = {"B": 0.7, "C": 1.0, "D": 1.15}

_LEGACY_POST_SIZE_TO_KEY: dict[str, str] = {
    # Legacy wizard strings (kept only for backward compatibility).
    # Current labels use '2-3/8" SS40' style; older labels had
    # "(Line Post)" suffix or "Steel Pipe" suffix.
    '2-3/8" SS40 (Line Post)': "2_3_8_SS40",
    '2-7/8" SS40 (Line Post)': "2_7_8_SS40",
    '3-1/2" SS40 (Line Post)': "3_1_2_SS40",
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

_LABEL_TO_KEY: dict[str, str] = {post.label: key for key, post in POST_TYPES.items()}

# Pipe posts ordered by increasing bending capacity (smallest to largest).
# Used by the capacity-based auto-selector.
_PIPE_POSTS_BY_SIZE: tuple[str, ...] = (
    "1_7_8_PIPE",
    "2_3_8_SS40",
    "2_7_8_SS40",
    "3_1_2_SS40",
    "4_0_PIPE",
    "6_5_8_PIPE",
    "8_5_8_PIPE",
)


def _normalize_post_key(post_size: str | None) -> str | None:
    """Convert any display string (legacy) to a catalog key."""
    if not post_size:
        return None
    # Check if it's already a key
    if post_size in POST_TYPES:
        return post_size
    # Check label-based mapping first, then legacy fallbacks
    normalized = _LABEL_TO_KEY.get(post_size) or _LEGACY_POST_SIZE_TO_KEY.get(post_size)
    if not normalized:
        warnings.warn(
            f"Unknown post label '{post_size}', falling back to auto selection.",
            stacklevel=2,
        )
    return normalized


def _build_recommendation(post_key: str, source_label: str | None = None) -> Recommendation:
    """
    Build a Recommendation from a catalog key, pulling labels/footings from catalogs.
    """
    post = POST_TYPES.get(post_key)
    strict_footing = get_settings().strict_footing

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
            warnings.warn(msg, stacklevel=2)
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


def _recommend_auto_by_capacity(
    load_per_post_lb: float,
    height_ft: float,
) -> Recommendation:
    """Auto-select the lightest commercial pipe with adequate bending capacity.

    Iterates pipe posts from smallest (1-7/8") to largest (8-5/8")
    and picks the first one where M_allow >= M_demand based on the
    actual section properties per ASTM F1083 Group IC.

    Falls back to the largest pipe if nothing is adequate.
    """
    for key in _PIPE_POSTS_BY_SIZE:
        _m_demand, _m_allow, ok = compute_moment_check(
            key, height_ft, load_per_post_lb,
        )
        if ok:
            return _build_recommendation(key)

    # Nothing adequate -> recommend the largest pipe with a warning
    logger.warning(
        "No standard pipe post has adequate bending capacity for "
        "%.0f lb at %.1f ft; recommending largest available (%s).",
        load_per_post_lb,
        height_ft,
        _PIPE_POSTS_BY_SIZE[-1],
    )
    return _build_recommendation(_PIPE_POSTS_BY_SIZE[-1])


def calculate_wind_load(request: WindLoadRequest) -> WindLoadResult:
    """
    Calculate wind load for a fence project (legacy API).

    .. deprecated:: 0.2.0
        Use :func:`calculate` with :class:`EstimateInput` instead.

    This is a simplified placeholder implementation. The actual calculation should follow
    relevant building codes (ASCE 7, etc.) for wind load on fences.
    """
    warnings.warn(
        "calculate_wind_load() is deprecated; use calculate() with EstimateInput instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    wind_speed = request.wind.wind_speed
    importance = request.wind.importance_factor

    velocity_pressure = _LEGACY_QZ_COEFF * (wind_speed**2) * importance
    design_pressure = velocity_pressure * _LEGACY_PRESSURE_MULT

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
    post_key: str | None,
    load_per_post_lb: float,
    data: EstimateInput,
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
        recommended = _recommend_auto_by_capacity(
            load_per_post_lb, data.height_total_ft,
        )
        effective_key = recommended.post_key

    max_spacing_ft: float | None = None
    M_demand_lb_in: float | None = None  # noqa: N806
    M_allow_lb_in: float | None = None  # noqa: N806
    moment_ok: bool | None = None
    footing_result: FootingResult | None = None
    deflection_result: DeflectionResult | None = None

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

        M_demand_lb_in, M_allow_lb_in, moment_ok = compute_moment_check(  # noqa: N806
            post_key=effective_key,
            height_ft=data.height_total_ft,
            load_per_post_lb=load_per_post_lb,
        )

        # Footing check (IBC 1807.3)
        post_obj = POST_TYPES[effective_key]
        embed_in = data.embedment_depth_in or (
            recommended.embedment_in if recommended else (post_obj.footing_embedment_in or 30.0)
        )
        _default_dia = post_obj.footing_diameter_in or 12.0
        footing_dia_in = data.footing_diameter_in or (
            recommended.footing_diameter_in if recommended else _default_dia
        )

        try:
            fc = compute_footing_check(
                load_per_post_lb=load_per_post_lb,
                height_above_grade_ft=data.height_total_ft,
                footing_diameter_in=footing_dia_in,
                embedment_depth_in=embed_in,
                soil_class=data.soil_type or "default",
            )
            footing_result = FootingResult(
                overturning_moment_ft_lb=fc.overturning_moment_ft_lb,
                resisting_moment_ft_lb=fc.resisting_moment_ft_lb,
                safety_factor=fc.safety_factor,
                footing_ok=fc.footing_ok,
                min_embedment_ft=fc.min_embedment_ft,
                actual_embedment_ft=fc.actual_embedment_ft,
                footing_diameter_in=fc.footing_diameter_in,
                soil_label=fc.soil_label,
                concrete_volume_cf=fc.concrete_volume_cf,
            )
            if not fc.footing_ok:
                warnings_list.append(
                    f"Footing SF = {fc.safety_factor:.2f} (need >= 1.50). "
                    f"Min embedment: {fc.min_embedment_ft:.1f} ft "
                    f"({fc.min_embedment_ft * 12:.0f} in)."
                )
        except Exception:
            logger.debug("Footing check skipped for %s", effective_key, exc_info=True)

        # Deflection check (serviceability)
        try:
            defl_in, defl_allow_in, defl_ok = compute_deflection_check(
                post_key=effective_key,
                height_ft=data.height_total_ft,
                load_per_post_lb=load_per_post_lb,
            )
            defl_ratio = round(defl_in / defl_allow_in, 3) if defl_allow_in > 0 else 0.0
            deflection_result = DeflectionResult(
                deflection_in=defl_in,
                allowable_in=defl_allow_in,
                deflection_ok=defl_ok,
                ratio=defl_ratio,
            )
            if not defl_ok:
                warnings_list.append(
                    f"Deflection {defl_in:.2f} in exceeds L/60 limit of "
                    f"{defl_allow_in:.2f} in. Consider a stiffer post."
                )
        except Exception:
            logger.debug("Deflection check skipped for %s", effective_key, exc_info=True)

    # Compute utilization ratios
    spacing_ratio: float | None = None
    moment_ratio: float | None = None

    if max_spacing_ft is not None and max_spacing_ft > 0:
        spacing_ratio = round(data.post_spacing_ft / max_spacing_ft, 3)

    if M_demand_lb_in is not None and M_allow_lb_in is not None and M_allow_lb_in > 0:
        moment_ratio = round(M_demand_lb_in / M_allow_lb_in, 3)

    # Status logic with YELLOW band
    status: str = "GREEN"

    # Spacing check
    if spacing_ratio is not None:
        if spacing_ratio > 1.0:
            status = "RED"
        elif spacing_ratio > 0.85:
            status = "YELLOW"

    # Terminal bending check (overrides spacing if worse)
    if role == "terminal" and moment_ratio is not None:
        if moment_ratio > 1.0:
            status = "RED"
            warnings_list.append(
                "Terminal bending exceeds capacity; "
                "increase post size or reduce spacing."
            )
        elif moment_ratio > 0.80 and status != "RED":
            status = "YELLOW"

    # Footing check is advisory - does not escalate status.
    # The user should review the footing warning and increase embedment
    # if needed. This keeps the primary status focused on spacing/bending.

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
        spacing_ratio=spacing_ratio,
        moment_ratio=moment_ratio,
        footing=footing_result,
        deflection=deflection_result,
        status=status,
    )


def calculate(data: EstimateInput) -> EstimateOutput:
    """Calculate bay-level loads with separate line and terminal post results.

    Uses ASCE 7-22 velocity pressure and force coefficients.
    """
    # Resolve fence solidity
    fence_info = ASCE_FENCE_TYPES.get(data.fence_type)
    solidity = fence_info.solidity if fence_info else 1.0

    # Compute B/s aspect ratio for Cf lookup (None = long run assumed)
    aspect_ratio_bs = data.aspect_ratio_bs

    # User-specified Kzt or default 1.0
    kzt = data.kzt if data.kzt else 1.0

    # ASCE 7-22 design pressure
    dp = compute_design_pressure(
        wind_speed_mph=data.wind_speed_mph,
        height_ft=data.height_total_ft,
        exposure=data.exposure,
        solidity=solidity,
        kzt=kzt,
        fence_type=data.fence_type,
        aspect_ratio_bs=aspect_ratio_bs,
    )
    pressure_psf = dp.design_pressure_psf

    area = data.area_per_bay_ft2
    total_load_lb = round(pressure_psf * area, 2)
    load_per_post_lb = round(total_load_lb / 2, 2)

    # Resolve post_key from legacy post_size if needed.
    # Treat "auto" / "recommended" as no override (auto-select by capacity).
    _raw_key = data.post_key
    effective_post_key: str | None = None
    if _raw_key and _raw_key.lower() not in {"auto", "recommended", ""}:
        effective_post_key = _raw_key
    if not effective_post_key and data.post_size:
        effective_post_key = _normalize_post_key(data.post_size)

    # Resolve line/terminal keys (fall back to deprecated single key if provided)
    line_post_key = data.line_post_key or effective_post_key
    terminal_post_key = data.terminal_post_key or effective_post_key

    design_params = DesignParameters(
        asce7_edition=dp.asce7_edition,
        kz=dp.kz,
        kzt=dp.kzt,
        kd=dp.kd,
        g=dp.g,
        cf_solid=dp.cf_solid,
        cf=dp.cf,
        solidity=dp.solidity,
        fence_type=dp.fence_type,
        qz_psf=dp.qz_psf,
    )

    shared = SharedResult(
        pressure_psf=pressure_psf,
        area_per_bay_ft2=round(area, 2),
        total_load_lb=total_load_lb,
        load_per_post_lb=load_per_post_lb,
        design_params=design_params,
    )

    line_block = _compute_block(
        role="line",
        post_key=line_post_key,
        load_per_post_lb=load_per_post_lb,
        data=data,
        pressure_psf=pressure_psf,
        area=area,
        total_load_lb=total_load_lb,
    )

    terminal_block = _compute_block(
        role="terminal",
        post_key=terminal_post_key,
        load_per_post_lb=load_per_post_lb,
        data=data,
        pressure_psf=pressure_psf,
        area=area,
        total_load_lb=total_load_lb,
    )

    overall_status = "GREEN"
    if line_block.status == "RED" or terminal_block.status == "RED":
        overall_status = "RED"
    elif line_block.status == "YELLOW" or terminal_block.status == "YELLOW":
        overall_status = "YELLOW"

    # Compute quantities when fence length is provided
    quantities: QuantitiesResult | None = None
    if data.fence_length_ft and data.fence_length_ft > 0:
        sq = compute_segment_quantities(
            fence_length_ft=data.fence_length_ft,
            height_ft=data.height_total_ft,
            post_spacing_ft=data.post_spacing_ft,
            line_post_key=line_post_key,
            terminal_post_key=terminal_post_key,
            num_terminals=2,
            num_corners=data.num_corners,
            num_gates=data.num_gates * 2,
            embedment_override_in=data.embedment_depth_in,
            footing_diameter_override_in=data.footing_diameter_in,
        )
        quantities = QuantitiesResult(
            fence_length_ft=sq.fence_length_ft,
            num_line_posts=sq.num_line_posts,
            num_terminal_posts=sq.num_terminal_posts,
            num_corner_posts=sq.num_corner_posts,
            num_gate_posts=sq.num_gate_posts,
            total_posts=sq.total_posts,
            top_rail_lf=sq.top_rail_lf,
            fabric_sf=sq.fabric_sf,
            total_concrete_cf=sq.total_concrete_cf,
            total_concrete_cy=sq.total_concrete_cy,
            line_post_length_ft=sq.line_post_length_ft,
            terminal_post_length_ft=sq.terminal_post_length_ft,
        )

    # Legacy compatibility: map to line block
    return EstimateOutput(
        shared=shared,
        line=line_block,
        terminal=terminal_block,
        overall_status=overall_status,
        quantities=quantities,
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


def calculate_project(project: ProjectInput) -> ProjectOutput:
    """Calculate wind loads for a multi-segment fence project.

    Each segment is computed independently using the shared wind
    parameters, then results and quantities are aggregated.
    """
    segment_outputs: list[SegmentOutput] = []
    worst_status = "GREEN"

    total_q = QuantitiesResult()
    _line = 0
    _term = 0
    _corner = 0
    _gate = 0
    _posts = 0
    _rail = 0.0
    _fabric = 0.0
    _concrete = 0.0
    _length = 0.0

    for seg in project.segments:
        inp = EstimateInput(
            wind_speed_mph=project.wind_speed_mph,
            height_total_ft=seg.height_total_ft,
            post_spacing_ft=seg.post_spacing_ft,
            fence_length_ft=seg.fence_length_ft,
            exposure=project.exposure,
            fence_type=seg.fence_type,
            risk_category=project.risk_category,
            kzt=project.kzt,
            soil_type=project.soil_type,
            embedment_depth_in=project.embedment_depth_in,
            footing_diameter_in=project.footing_diameter_in,
            line_post_key=seg.line_post_key,
            terminal_post_key=seg.terminal_post_key,
            gate_post_key=seg.gate_post_key,
            corner_post_key=seg.corner_post_key,
            num_gates=seg.num_gates,
            num_corners=seg.num_corners,
        )
        est = calculate(inp)

        segment_outputs.append(SegmentOutput(
            label=seg.label,
            estimate=est,
            quantities=est.quantities,
        ))

        # Aggregate status
        if est.overall_status == "RED":
            worst_status = "RED"
        elif est.overall_status == "YELLOW" and worst_status != "RED":
            worst_status = "YELLOW"

        # Aggregate quantities
        if est.quantities:
            q = est.quantities
            _line += q.num_line_posts
            _term += q.num_terminal_posts
            _corner += q.num_corner_posts
            _gate += q.num_gate_posts
            _posts += q.total_posts
            _rail += q.top_rail_lf
            _fabric += q.fabric_sf
            _concrete += q.total_concrete_cf
            _length += q.fence_length_ft

    total_q = QuantitiesResult(
        fence_length_ft=round(_length, 1),
        num_line_posts=_line,
        num_terminal_posts=_term,
        num_corner_posts=_corner,
        num_gate_posts=_gate,
        total_posts=_posts,
        top_rail_lf=round(_rail, 1),
        fabric_sf=round(_fabric, 1),
        total_concrete_cf=round(_concrete, 2),
        total_concrete_cy=round(_concrete / 27.0, 2),
    )

    return ProjectOutput(
        segments=segment_outputs,
        overall_status=worst_status,
        total_quantities=total_q,
    )


def _recommend_member_with_override(
    load_per_post: float,
    post_size_override: str | None,
    post_key: str | None = None,
    height_ft: float = 8.0,
) -> Recommendation:
    """
    Choose post + footing.

    .. deprecated:: 0.2.0
        Internal function retained for backward compatibility only.
        New code should use :func:`_compute_block` which handles post selection.

    - If no override is given, fall back to the capacity-based auto selector.
    - If an override is given and recognized in POST_TYPES:
        * keep that post size,
        * use its footing from the catalog,
        * and let spacing checks / warnings handle overloads.
    """
    # Explicit post_key wins, regardless of post_size_override
    if post_key and post_key in POST_TYPES:
        return _build_recommendation_for_post_key(post_key, source="manual")

    if not post_size_override or post_size_override.lower() in {"auto", "recommended", ""}:
        return _recommend_auto_by_capacity(load_per_post, height_ft)

    # Use post_key if provided, otherwise try to normalize
    normalized_key = post_key or _normalize_post_key(post_size_override)

    if normalized_key and normalized_key in POST_TYPES:
        post = POST_TYPES[normalized_key]
        return _build_recommendation(post_key=normalized_key, source_label=post.label)

    # Unknown string -> fall back
    return _recommend_auto_by_capacity(load_per_post, height_ft)


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
    fence_info = ASCE_FENCE_TYPES.get(data.fence_type)
    solidity = fence_info.solidity if fence_info else 1.0
    fence_label = fence_info.label if fence_info else data.fence_type

    aspect_ratio_bs = data.aspect_ratio_bs
    kzt = data.kzt if data.kzt else 1.0
    dp = compute_design_pressure(
        wind_speed_mph=data.wind_speed_mph,
        height_ft=data.height_total_ft,
        exposure=data.exposure,
        solidity=solidity,
        kzt=kzt,
        fence_type=data.fence_type,
        aspect_ratio_bs=aspect_ratio_bs,
    )

    bs_note = (
        f"B/s = {aspect_ratio_bs:.1f} "
        f"(fence length {data.fence_length_ft:.0f} ft / "
        f"height {data.height_total_ft} ft)"
        if aspect_ratio_bs is not None
        else "B/s >= 20 assumed (long run; fence length not specified)"
    )

    kzt_note = (
        f"Kzt = {dp.kzt} (user-specified topographic factor, Section 26.8)."
        if kzt > 1.0
        else f"Kzt = {dp.kzt} (flat terrain assumed)."
    )

    assumptions = [
        f"Design wind speed V = {data.wind_speed_mph} mph "
        f"(3-sec gust at 33 ft) for Risk Category {data.risk_category}, "
        "entered by user from ASCE 7 wind maps or project drawings.",
        f"Velocity pressure per ASCE 7-22 Eq. 26.10-1: "
        f"qz = 0.00256 x Kz x Kzt x Kd x V^2 = {dp.qz_psf:.2f} psf.",
        f"Kz = {dp.kz:.3f} (Exposure {data.exposure}, "
        f"h = {data.height_total_ft} ft, Table 26.10-1).",
        f"Kd = {dp.kd} (fences/signs, Table 26.6-1).",
        kzt_note,
        f"G = {dp.g} (rigid structure gust-effect factor, Section 26.11).",
        f"Cf = {dp.cf:.3f} ({fence_label}, "
        f"solidity = {solidity:.2f}, {bs_note}, "
        "Figure 29.3-1).",
        "Uniform pressure distribution assumed across the bay.",
        "Post tributary load = total bay load / 2.",
        "Bending demand: M = P x (H/2), uniform load resultant at mid-height.",
        "Allowable bending: M_allow = Fy x S / omega, "
        "omega = 1.67 (ASD, AISC F1).",
        "Deflection check: delta_max = P*L^3 / (8*E*I), limit L/60.",
        "Footing check per IBC 1807.3: triangular soil pressure, SF >= 1.5.",
        "Pipe posts per ASTM F1083 Group IC (commercial chain-link). "
        "Fy = 50 ksi.",
        "Terminal posts modeled as cantilevers fixed at grade; "
        "line posts restrained by top rail and fabric (advisory check).",
        "Status: GREEN (<85% utilization), "
        "YELLOW (85-100%), RED (>100%).",
    ]
    return assumptions


__all__ = [
    "calculate",
    "calculate_project",
    "calculate_wind_load",
]
