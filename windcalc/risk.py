"""Risk classification logic for wind load estimates.

Determines GREEN / YELLOW / RED status based on spacing vs table limits
and bending capacity checks.
"""

from __future__ import annotations

import logging
from typing import Any

from windcalc.schemas import EstimateOutput

logger = logging.getLogger(__name__)


def classify_risk(
    out: EstimateOutput,
    data: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Classify risk status (GREEN/YELLOW/RED).

    GREEN / YELLOW / RED are based on spacing vs table limits.
    Bending check is kept as advisory information only and does
    NOT override the spacing-based status.
    """
    details: dict[str, Any] = {
        "reasons": [],
        "advanced_reasons": [],
        "line_spacing_ratio": None,
        "line_max_spacing_ft": None,
        "terminal_bending_ratio": None,
    }

    status = out.overall_status if hasattr(out, "overall_status") else "GREEN"

    # Line spacing info
    if hasattr(out, "line") and out.line.max_spacing_ft:
        spacing_ratio = data.get("post_spacing_ft", 0) / out.line.max_spacing_ft
        details["line_spacing_ratio"] = spacing_ratio
        details["line_max_spacing_ft"] = out.line.max_spacing_ft
        if spacing_ratio > 1.15:
            details["reasons"].append(
                f"Line spacing at {spacing_ratio*100:.0f}% of limit "
                f"({data.get('post_spacing_ft', 0):.2f} ft vs {out.line.max_spacing_ft:.2f} ft max)"
            )
        elif spacing_ratio > 1.0:
            details["reasons"].append(
                f"Line spacing slightly above limit "
                f"({data.get('post_spacing_ft', 0):.2f} ft vs {out.line.max_spacing_ft:.2f} ft max)"
            )

    # Terminal bending info
    if hasattr(out, "terminal") and out.terminal.M_allow_ft_lb:
        ratio = (
            out.terminal.M_demand_ft_lb / out.terminal.M_allow_ft_lb
            if out.terminal.M_demand_ft_lb and out.terminal.M_allow_ft_lb
            else None
        )
        details["terminal_bending_ratio"] = ratio
        if ratio is not None:
            msg = (
                f"Terminal bending utilization: {ratio*100:.0f}% "
                f"({out.terminal.M_demand_ft_lb:.1f} / {out.terminal.M_allow_ft_lb:.1f} ft·lb)"
            )
            details["reasons"].append(msg)

    # Line bending advisory
    if hasattr(out, "line") and out.line.M_allow_ft_lb:
        ratio = (
            out.line.M_demand_ft_lb / out.line.M_allow_ft_lb
            if out.line.M_demand_ft_lb and out.line.M_allow_ft_lb
            else None
        )
        if ratio is not None:
            msg = (
                "Advisory - Simplified cantilever bending check (conservative): "
                f"{ratio*100:.0f}% "
                f"({out.line.M_demand_ft_lb:.1f} / {out.line.M_allow_ft_lb:.1f} ft·lb)"
            )
            details["advanced_reasons"].append(msg)

    return status, details


__all__ = ["classify_risk"]
