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
    """Check footing lateral resistance per IBC 1807.3.1.

    Uses the IBC 1807.3.1 non-constrained pier formula to compute
    the required embedment depth, then compares against actual::

        d = 0.5 * A * (1 + sqrt(1 + 4.36 * h / A))

    where:
    - A  = 2.34 * P / (S1 * b)
    - P  = lateral load (lb)
    - S1 = lateral soil bearing (psf per ft of depth)
    - b  = footing diameter (ft)
    - h  = distance from ground to load resultant (ft) = H/2

    This method properly accounts for the interaction between pier
    diameter, embedment depth, and load height for round concrete
    piers, giving realistic results for commercial fence posts.

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
    p_lb = load_per_post_lb
    h_ft = height_above_grade_ft / 2.0  # resultant at mid-height

    # IBC 1807.3.1 required embedment (non-constrained)
    if s1 > 0 and b_ft > 0 and p_lb > 0:
        a_val = 2.34 * p_lb / (s1 * b_ft)
        d_min_ft = 0.5 * a_val * (1.0 + math.sqrt(1.0 + 4.36 * h_ft / a_val))
    else:
        a_val = 0.0
        d_min_ft = d_ft

    # Apply safety factor to required depth
    d_required_ft = d_min_ft * math.sqrt(required_sf)

    # Compute actual resisting capacity using the same formula inverted.
    # For the actual embedment d, the maximum lateral load the pier can
    # resist is found from the IBC relationship. We express as SF ratio.
    sf = (d_ft / d_min_ft) ** 2 if d_min_ft > 0 else 999.0
    footing_ok = sf >= required_sf

    # Overturning moment (for reporting)
    m_ot = p_lb * h_ft

    # Resisting moment estimate (using actual embedment in simplified form)
    m_resist = m_ot * sf if m_ot > 0 else 0.0

    # Concrete volume (cylindrical pier)
    radius_ft = b_ft / 2.0
    concrete_cf = math.pi * radius_ft**2 * d_ft

    return FootingCheckResult(
        overturning_moment_ft_lb=round(m_ot, 1),
        resisting_moment_ft_lb=round(m_resist, 1),
        safety_factor=round(sf, 2),
        footing_ok=footing_ok,
        min_embedment_ft=round(d_required_ft, 2),
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
