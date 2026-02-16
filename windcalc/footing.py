"""Lateral soil resistance / footing check per IBC 1807.3.

Simplified prescriptive method for round concrete pier footings
supporting fence posts subject to lateral wind loads.

The overturning resistance is computed from the allowable lateral
soil-bearing pressure (IBC Table 1806.2) and compared against the
wind-induced overturning moment at grade.

References
----------
- IBC 2021 Section 1807.3
- IBC 2021 Table 1806.2 (Allowable Foundation and Lateral Pressure)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ── Soil Classes per IBC Table 1806.2 ───────────────────────────────
# Lateral bearing pressure in psf per foot of depth below grade.
SOIL_CLASSES: dict[str, tuple[str, float]] = {
    "rock_crystalline": ("Crystalline bedrock (Class 1)", 1200.0),
    "rock_sedimentary": ("Sedimentary rock (Class 2)", 400.0),
    "gravel": ("Sandy gravel, GW/GP (Class 3)", 200.0),
    "sand": ("Sand, silty sand, SW/SP/SM (Class 4)", 150.0),
    "clay": ("Clay, sandy clay, CL/ML (Class 5)", 100.0),
    "default": ("Default - stiff soil (conservative)", 150.0),
}


@dataclass(frozen=True)
class FootingCheckResult:
    """Result of the footing lateral resistance check."""

    overturning_moment_ft_lb: float
    resisting_moment_ft_lb: float
    safety_factor: float
    footing_ok: bool
    min_embedment_ft: float
    actual_embedment_ft: float
    footing_diameter_in: float
    soil_class: str
    soil_label: str
    lateral_bearing_psf_per_ft: float
    concrete_volume_cf: float


def compute_footing_check(
    load_per_post_lb: float,
    height_above_grade_ft: float,
    footing_diameter_in: float,
    embedment_depth_in: float,
    soil_class: str = "default",
    required_sf: float = 1.5,
) -> FootingCheckResult:
    """Check footing lateral resistance against overturning.

    Uses a simplified triangular soil pressure distribution where
    lateral bearing increases linearly with depth at the rate given
    by IBC Table 1806.2 for the selected soil class.

    The resisting moment about the ground surface is::

        M_resist = (S1 * b * d^2) / 3

    where:
    - S1 = allowable lateral bearing (psf per ft of depth)
    - b  = footing diameter (ft)
    - d  = embedment depth (ft)

    Parameters
    ----------
    load_per_post_lb : float
        Tributary wind load on one post (lb).
    height_above_grade_ft : float
        Fence height above grade (ft). Load resultant at H/2.
    footing_diameter_in : float
        Footing diameter in inches.
    embedment_depth_in : float
        Embedment depth below grade in inches.
    soil_class : str
        Soil class key from :data:`SOIL_CLASSES`.
    required_sf : float
        Required safety factor (default 1.5).

    Returns
    -------
    FootingCheckResult
    """
    soil_label, s1 = SOIL_CLASSES.get(soil_class, SOIL_CLASSES["default"])

    # Convert units
    d_ft = embedment_depth_in / 12.0
    b_ft = footing_diameter_in / 12.0

    # Overturning moment at grade (lb-ft)
    m_ot = load_per_post_lb * (height_above_grade_ft / 2.0)

    # Resisting moment from triangular soil pressure distribution (lb-ft)
    m_resist = (s1 * b_ft * d_ft**2) / 3.0

    sf = m_resist / m_ot if m_ot > 0 else 999.0
    footing_ok = sf >= required_sf

    # Minimum embedment for the required SF (solve d from M_resist = SF * M_ot)
    if s1 > 0 and b_ft > 0 and m_ot > 0:
        d_min_ft = math.sqrt(3.0 * required_sf * m_ot / (s1 * b_ft))
    else:
        d_min_ft = d_ft

    # Concrete volume (cylindrical pier)
    radius_ft = b_ft / 2.0
    concrete_cf = math.pi * radius_ft**2 * d_ft

    return FootingCheckResult(
        overturning_moment_ft_lb=round(m_ot, 1),
        resisting_moment_ft_lb=round(m_resist, 1),
        safety_factor=round(sf, 2),
        footing_ok=footing_ok,
        min_embedment_ft=round(d_min_ft, 2),
        actual_embedment_ft=round(d_ft, 2),
        footing_diameter_in=footing_diameter_in,
        soil_class=soil_class,
        soil_label=soil_label,
        lateral_bearing_psf_per_ft=s1,
        concrete_volume_cf=round(concrete_cf, 3),
    )


__all__ = [
    "SOIL_CLASSES",
    "FootingCheckResult",
    "compute_footing_check",
]
