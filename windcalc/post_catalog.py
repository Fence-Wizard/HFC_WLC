"""Post type catalog and Cf factor tables for wind load calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

PostGroup = Literal["IA_REG", "IA_HIGH", "IC_PIPE", "II_CSHAPE"]


@dataclass
class PostType:
    key: str  # internal key (used in forms / engine)
    label: str  # what PM sees
    group: PostGroup  # Cf1 group
    od_in: Optional[float] = None  # outer diameter (pipe) OR None for C-shapes
    wall_in: Optional[float] = None  # wall thickness (pipe)
    height_base_ft: float = 0.0  # height used in your tabulated spacing S_table
    spacing_base_ft: float = 0.0  # S_table: base spacing from your manual
    fy_ksi: float = 50.0  # yield strength (30 or 50 typically)
    section_modulus_in3: Optional[float] = None  # precomputed for C-shapes


POST_TYPES: dict[str, PostType] = {
    # --- Pipe posts (Group IC: steel pipe 50 ksi) ---
    "2_3_8_SS40": PostType(
        key="2_3_8_SS40",
        label='2-3/8" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=2.375,
        wall_in=0.130,  # adjust to your actual SS40 wall
        height_base_ft=6.0,
        spacing_base_ft=8.0,  # S_table for that height/post from your manual
        fy_ksi=50.0,
    ),
    "2_7_8_SS40": PostType(
        key="2_7_8_SS40",
        label='2-7/8" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=2.875,
        wall_in=0.160,  # adjust
        height_base_ft=6.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
    ),
    "3_1_2_SS40": PostType(
        key="3_1_2_SS40",
        label='3-1/2" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=3.5,
        wall_in=0.160,  # adjust
        height_base_ft=8.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
    ),
    # --- C-shapes (Group II: high strength cold-rolled C-shape 50 ksi) ---
    "C_1_7_8_X_1_5_8_X_105": PostType(
        key="C_1_7_8_X_1_5_8_X_105",
        label='1 7/8" x 1 5/8" x .105" C-Shape',
        group="II_CSHAPE",
        od_in=None,
        wall_in=None,
        height_base_ft=6.0,
        spacing_base_ft=8.0,  # from your table
        fy_ksi=50.0,
        section_modulus_in3=1.23,  # example; fill from your manual
    ),
    # Add more post types as needed...
}

# Cf1 values per group & wind speed (mph)
# From your CSV:
#  WS   Group IA Regular   Group IA High   Group IC Pipe   Group II C-Shape
# 105   2.2                3.7             3.1             (from sheet)
# 110   2.0                3.4             2.8             ...
# 120   1.7                2.8             2.4             ...
# 130   1.4                2.4             2.0             ...

CF1_TABLE = {
    "IA_REG": [
        (105.0, 2.2),
        (110.0, 2.0),
        (120.0, 1.7),
        (130.0, 1.4),
    ],
    "IA_HIGH": [
        (105.0, 3.7),
        (110.0, 3.4),
        (120.0, 2.8),
        (130.0, 2.4),
    ],
    "IC_PIPE": [
        (105.0, 3.1),
        (110.0, 2.8),
        (120.0, 2.4),
        (130.0, 2.0),
    ],
    "II_CSHAPE": [
        # Fill from your sheet for Group II C-shape
        # Example structure:
        (105.0, 3.1),
        (110.0, 2.8),
        (120.0, 2.4),
        (130.0, 2.0),
    ],
}

# Exposure factor Cf2 (from your sheet: 1.0 / 0.69 / 0.57)
EXPOSURE_CF2 = {
    "B": 1.0,
    "C": 0.69,
    "D": 0.57,
}

# Cf3 reserved for future adjustments (fabric, site, etc.)
DEFAULT_CF3 = 1.0


def get_cf1(group: PostGroup, wind_speed_mph: float) -> float:
    """Interpolate Cf1 for a given group and wind speed."""
    table = CF1_TABLE[group]
    # Sort just in case
    table = sorted(table, key=lambda t: t[0])

    # Below minimum or above maximum -> clamp
    if wind_speed_mph <= table[0][0]:
        return table[0][1]
    if wind_speed_mph >= table[-1][0]:
        return table[-1][1]

    # Linear interpolation
    for (ws_lo, cf_lo), (ws_hi, cf_hi) in zip(table, table[1:]):
        if ws_lo <= wind_speed_mph <= ws_hi:
            t = (wind_speed_mph - ws_lo) / (ws_hi - ws_lo)
            return cf_lo + t * (cf_hi - cf_lo)

    # Fallback (should never hit)
    return table[-1][1]


def compute_max_spacing_cf(
    post_key: str,
    wind_speed_mph: float,
    exposure: str,
    cf3: float = DEFAULT_CF3,
) -> float:
    """
    Given a chosen post type, wind speed, and exposure,
    compute the max recommended spacing S_max (ft)
    based on your Cf1/Cf2 method and the base table spacing.
    """
    post = POST_TYPES[post_key]

    cf1 = get_cf1(post.group, wind_speed_mph)  # from CF1_TABLE
    cf2 = EXPOSURE_CF2[exposure]  # 1.0 / 0.69 / 0.57
    s_table = post.spacing_base_ft  # S_table from your manual

    s_max = s_table * cf1 * cf2 * cf3
    return s_max


def section_modulus_pipe(od_in: float, wall_in: float) -> float:
    """Section modulus S (in^3) for hollow circular tube."""
    D = od_in
    t = wall_in
    d = D - 2 * t
    S = math.pi * (D**4 - d**4) / (32 * D)
    return S


def bending_capacity_lb_in(
    S_in3: float,
    fy_ksi: float,
    omega: float = 1.67,
) -> float:
    """Allowable moment in lb-in."""
    fy_psi = fy_ksi * 1000.0
    M_allow = (fy_psi * S_in3) / omega
    return M_allow


def compute_moment_check(
    post_key: str,
    height_ft: float,
    load_per_post_lb: float,
) -> tuple[float, float, bool]:
    """
    Return (M_demand_lb_in, M_allow_lb_in, is_ok).
    """
    post = POST_TYPES[post_key]

    # 1) Determine section modulus
    if post.section_modulus_in3 is not None:
        # For C-shapes or custom sections, you can pre-store S directly
        S = post.section_modulus_in3
    elif post.od_in is not None and post.wall_in is not None:
        S = section_modulus_pipe(post.od_in, post.wall_in)
    else:
        # No geometry -> skip check
        return (0.0, 0.0, True)

    # 2) Allowable moment
    M_allow = bending_capacity_lb_in(S, post.fy_ksi)

    # 3) Demand moment (0.6 H above grade, inches)
    lever_arm_in = 0.6 * height_ft * 12.0
    M_demand = load_per_post_lb * lever_arm_in

    is_ok = M_demand <= M_allow
    return (M_demand, M_allow, is_ok)


__all__ = [
    "PostGroup",
    "PostType",
    "POST_TYPES",
    "CF1_TABLE",
    "EXPOSURE_CF2",
    "DEFAULT_CF3",
    "get_cf1",
    "compute_max_spacing_cf",
    "section_modulus_pipe",
    "bending_capacity_lb_in",
    "compute_moment_check",
]

