"""Fence concrete takeoff calculator."""

from __future__ import annotations

import math

from windcalc.schemas import (
    ConcreteEstimateInput,
    ConcreteEstimateOutput,
    ConcreteHoleSpecOutput,
)

# Typical nominal yield for a 60 lb bag in cubic feet.
BAG_60LB_YIELD_CF = 0.45


def _volume_per_hole_cf(hole_diameter_in: float, hole_depth_in: float) -> float:
    """Cylindrical hole volume in cubic feet."""
    radius_ft = hole_diameter_in / 24.0
    depth_ft = hole_depth_in / 12.0
    return math.pi * (radius_ft**2) * depth_ft


def calculate_concrete_estimate(request: ConcreteEstimateInput) -> ConcreteEstimateOutput:
    """Calculate fence concrete takeoff across multiple hole specification rows."""
    rows: list[ConcreteHoleSpecOutput] = []
    warnings: list[str] = []
    assumptions = [
        "Hole volume modeled as a full cylinder.",
        "No bell/bulb footing shape included.",
        f"60 lb bag yield assumed as {BAG_60LB_YIELD_CF:.2f} cf per bag.",
    ]

    subtotal_cf = 0.0
    total_holes = 0

    for spec in request.hole_specs:
        per_hole_cf = _volume_per_hole_cf(spec.hole_diameter_in, spec.hole_depth_in)
        row_total_cf = per_hole_cf * spec.hole_count
        row_total_cy = row_total_cf / 27.0
        row_bags = math.ceil(row_total_cf / BAG_60LB_YIELD_CF)

        rows.append(
            ConcreteHoleSpecOutput(
                post_type=spec.post_type.strip() or "Post",
                hole_diameter_in=spec.hole_diameter_in,
                hole_depth_in=spec.hole_depth_in,
                hole_count=spec.hole_count,
                volume_per_hole_cf=round(per_hole_cf, 3),
                total_volume_cf=round(row_total_cf, 3),
                total_volume_cy=round(row_total_cy, 3),
                bags_60lb=row_bags,
            )
        )

        if spec.hole_depth_in > 72:
            warnings.append(
                f"{spec.post_type or 'Row'} depth {spec.hole_depth_in:.0f} in is unusually deep."
            )
        if spec.hole_diameter_in > 24:
            warnings.append(
                f"{spec.post_type or 'Row'} diameter "
                f"{spec.hole_diameter_in:.0f} in is unusually large."
            )

        subtotal_cf += row_total_cf
        total_holes += spec.hole_count

    waste_percent = request.waste_percent if request.include_waste else 0.0
    waste_cf = subtotal_cf * (waste_percent / 100.0)
    total_cf = subtotal_cf + waste_cf
    total_cy = total_cf / 27.0
    total_bags = math.ceil(total_cf / BAG_60LB_YIELD_CF)

    return ConcreteEstimateOutput(
        rows=rows,
        total_holes=total_holes,
        subtotal_volume_cf=round(subtotal_cf, 3),
        waste_percent=round(waste_percent, 2),
        waste_volume_cf=round(waste_cf, 3),
        total_volume_cf=round(total_cf, 3),
        total_volume_cy=round(total_cy, 3),
        bags_60lb=total_bags,
        assumptions=assumptions,
        warnings=warnings,
    )

