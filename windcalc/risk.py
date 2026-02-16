"""Risk classification logic for wind load estimates.

Determines GREEN / YELLOW / RED status based on spacing vs table limits
and bending capacity checks.

Thresholds
----------
- GREEN:  utilization < 85%
- YELLOW: utilization 85-100% (marginal, review recommended)
- RED:    utilization > 100% (exceeds limits, action required)
"""

from __future__ import annotations

import logging
from typing import Any

from windcalc.schemas import EstimateOutput

logger = logging.getLogger(__name__)

# Utilization thresholds
_YELLOW_THRESHOLD = 0.85
_RED_THRESHOLD = 1.0


def classify_risk(
    out: EstimateOutput,
    data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Classify risk status (GREEN / YELLOW / RED).

    Uses spacing and bending utilization ratios from the engine output.
    The engine already computes per-block status; this function aggregates
    them and builds human-readable detail strings for the UI and PDF.
    """
    details: dict[str, Any] = {
        "reasons": [],
        "advanced_reasons": [],
        "line_spacing_ratio": None,
        "line_max_spacing_ft": None,
        "terminal_bending_ratio": None,
    }

    # Use engine-computed overall status as the primary source
    status = out.overall_status if hasattr(out, "overall_status") else "GREEN"

    # ── Line spacing info ────────────────────────────────────────────
    if hasattr(out, "line") and out.line.max_spacing_ft:
        spacing_ratio = out.line.spacing_ratio
        if spacing_ratio is None:
            spacing_ft = data.get("post_spacing_ft", 0)
            if isinstance(spacing_ft, str):
                spacing_ft = float(spacing_ft)
            spacing_ratio = spacing_ft / out.line.max_spacing_ft

        details["line_spacing_ratio"] = spacing_ratio
        details["line_max_spacing_ft"] = out.line.max_spacing_ft

        if spacing_ratio > _RED_THRESHOLD:
            details["reasons"].append(
                f"Line spacing at {spacing_ratio * 100:.0f}% of limit "
                f"({data.get('post_spacing_ft', 0)} ft "
                f"vs {out.line.max_spacing_ft:.2f} ft max)"
            )
        elif spacing_ratio > _YELLOW_THRESHOLD:
            details["reasons"].append(
                f"Line spacing near limit at {spacing_ratio * 100:.0f}% "
                f"({data.get('post_spacing_ft', 0)} ft "
                f"vs {out.line.max_spacing_ft:.2f} ft max) "
                "- review recommended"
            )

    # ── Terminal bending info ────────────────────────────────────────
    if hasattr(out, "terminal") and out.terminal.M_allow_ft_lb:
        ratio = out.terminal.moment_ratio
        if ratio is None and out.terminal.M_demand_ft_lb and out.terminal.M_allow_ft_lb:
            ratio = out.terminal.M_demand_ft_lb / out.terminal.M_allow_ft_lb

        details["terminal_bending_ratio"] = ratio
        if ratio is not None:
            msg = (
                f"Terminal bending utilization: {ratio * 100:.0f}% "
                f"({out.terminal.M_demand_ft_lb:.1f} / "
                f"{out.terminal.M_allow_ft_lb:.1f} ft-lb)"
            )
            details["reasons"].append(msg)

    # ── Line bending advisory ────────────────────────────────────────
    if hasattr(out, "line") and out.line.M_allow_ft_lb:
        ratio = out.line.moment_ratio
        if ratio is None and out.line.M_demand_ft_lb and out.line.M_allow_ft_lb:
            ratio = out.line.M_demand_ft_lb / out.line.M_allow_ft_lb

        if ratio is not None:
            msg = (
                "Advisory - Simplified cantilever bending check (conservative): "
                f"{ratio * 100:.0f}% "
                f"({out.line.M_demand_ft_lb:.1f} / "
                f"{out.line.M_allow_ft_lb:.1f} ft-lb)"
            )
            details["advanced_reasons"].append(msg)

    # ── Footing check ─────────────────────────────────────────────────
    for role_name, block in [("Line", out.line), ("Terminal", out.terminal)]:
        if block.footing and not block.footing.footing_ok:
            msg = (
                f"{role_name} footing SF = {block.footing.safety_factor:.2f} "
                f"(need ≥ 1.50). Min embedment: "
                f"{block.footing.min_embedment_ft:.1f} ft."
            )
            details["reasons"].append(msg)
        elif block.footing and block.footing.safety_factor < 2.0:
            msg = (
                f"{role_name} footing SF = {block.footing.safety_factor:.2f} "
                f"(adequate but marginal)."
            )
            details["advanced_reasons"].append(msg)

    # ── Deflection check ──────────────────────────────────────────────
    for role_name, block in [("Line", out.line), ("Terminal", out.terminal)]:
        if block.deflection and not block.deflection.deflection_ok:
            msg = (
                f"{role_name} deflection {block.deflection.deflection_in:.2f} in "
                f"exceeds L/60 limit ({block.deflection.allowable_in:.2f} in)."
            )
            details["advanced_reasons"].append(msg)

    return status, details


__all__ = ["classify_risk"]
