"""Post type catalog and Cf factor tables for wind load calculations."""

from __future__ import annotations

import csv
import itertools
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

PostGroup = Literal["IA_REG", "IA_HIGH", "IC_PIPE", "II_CSHAPE"]


@dataclass
class PostType:
    key: str  # internal key (used in forms / engine)
    label: str  # what PM sees
    group: PostGroup  # Cf1 group
    od_in: float | None = None  # outer diameter (pipe) OR None for C-shapes
    wall_in: float | None = None  # wall thickness (pipe)
    height_base_ft: float = 0.0  # height used in your tabulated spacing S_table
    spacing_base_ft: float = 0.0  # S_table: base spacing from your manual
    fy_ksi: float = 50.0  # yield strength (30 or 50 typically)
    section_modulus_in3: float | None = None  # precomputed for C-shapes
    table_label: str | None = None  # exact label used in the CSV tables
    footing_diameter_in: float | None = None  # default footing diameter
    footing_embedment_in: float | None = None  # default embedment depth


POST_TYPES: dict[str, PostType] = {
    # --- Existing pipe posts (Group IC: steel pipe, 50 ksi) ---
    "2_3_8_SS40": PostType(
        key="2_3_8_SS40",
        label='2-3/8" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=2.375,
        wall_in=0.130,  # confirm from your product data
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        table_label='2 3/8"',  # matches WLC Tables CSV row
        footing_diameter_in=10.0,
        footing_embedment_in=24.0,
    ),
    "2_7_8_SS40": PostType(
        key="2_7_8_SS40",
        label='2-7/8" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=2.875,
        wall_in=0.160,
        height_base_ft=6.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
        table_label='2 7/8"',
        footing_diameter_in=12.0,
        footing_embedment_in=30.0,
    ),
    "3_1_2_SS40": PostType(
        key="3_1_2_SS40",
        label='3-1/2" SS40 (Line Post)',
        group="IC_PIPE",
        od_in=3.5,
        wall_in=0.160,
        height_base_ft=8.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
        table_label='3 1/2"',
        footing_diameter_in=16.0,
        footing_embedment_in=36.0,
    ),
    # --- Additional steel pipe sizes (same group / style) ---
    "1_7_8_PIPE": PostType(
        key="1_7_8_PIPE",
        label='1 7/8" Steel Pipe',
        group="IC_PIPE",
        od_in=1.90,  # TODO: confirm OD from mill certs
        wall_in=0.120,  # TODO: confirm wall
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        table_label='1 7/8"',
        footing_diameter_in=10.0,
        footing_embedment_in=24.0,
    ),
    "4_0_PIPE": PostType(
        key="4_0_PIPE",
        label='4" Steel Pipe',
        group="IC_PIPE",
        od_in=4.00,  # TODO: confirm
        wall_in=0.160,  # TODO: confirm
        height_base_ft=8.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
        table_label='4"',
        footing_diameter_in=18.0,
        footing_embedment_in=42.0,
    ),
    "6_5_8_PIPE": PostType(
        key="6_5_8_PIPE",
        label='6 5/8" Steel Pipe',
        group="IC_PIPE",
        od_in=6.625,  # TODO: confirm
        wall_in=0.280,  # TODO: confirm
        height_base_ft=8.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
        table_label='6 5/8"',
        footing_diameter_in=24.0,
        footing_embedment_in=48.0,
    ),
    "8_5_8_PIPE": PostType(
        key="8_5_8_PIPE",
        label='8 5/8" Steel Pipe',
        group="IC_PIPE",
        od_in=8.625,  # TODO: confirm
        wall_in=0.322,  # TODO: confirm
        height_base_ft=8.0,
        spacing_base_ft=10.0,
        fy_ksi=50.0,
        table_label='8 5/8"',
        footing_diameter_in=30.0,
        footing_embedment_in=54.0,
    ),
    # --- C-shapes (Group II: high strength cold-rolled C-shape, 50 ksi) ---
    "C_1_7_8_X_1_5_8_X_105": PostType(
        key="C_1_7_8_X_1_5_8_X_105",
        label='1 7/8" x 1 5/8" x .105" C-Shape',
        group="II_CSHAPE",
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        section_modulus_in3=None,  # TODO: plug in Sx from manufacturer if you want moment checks
        table_label='1 7/8" x 1 5/8" x .105',
        footing_diameter_in=10.0,
        footing_embedment_in=24.0,
    ),
    "C_1_7_8_X_1_5_8_X_121": PostType(
        key="C_1_7_8_X_1_5_8_X_121",
        label='1 7/8" x 1 5/8" x .121" C-Shape',
        group="II_CSHAPE",
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        section_modulus_in3=None,  # TODO: add Sx
        table_label='1 7/8" x 1 5/8" x .121',
        footing_diameter_in=10.0,
        footing_embedment_in=24.0,
    ),
    "C_2_1_4_X_1_5_8_X_121": PostType(
        key="C_2_1_4_X_1_5_8_X_121",
        label='2 1/4" x 1 5/8" x .121" C-Shape',
        group="II_CSHAPE",
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        section_modulus_in3=None,
        table_label='2 1/4" x 1 5/8" x .121',
        footing_diameter_in=12.0,
        footing_embedment_in=30.0,
    ),
    "C_3_1_4_X_2_1_2_X_130": PostType(
        key="C_3_1_4_X_2_1_2_X_130",
        label='3 1/4" x 2 1/2" x .130" C-Shape',
        group="II_CSHAPE",
        height_base_ft=6.0,
        spacing_base_ft=8.0,
        fy_ksi=50.0,
        section_modulus_in3=None,
        table_label='3 1/4" x 2 1/2" x .130',
        footing_diameter_in=14.0,
        footing_embedment_in=36.0,
    ),
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
    for (ws_lo, cf_lo), (ws_hi, cf_hi) in itertools.pairwise(table):
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
    D = od_in  # noqa: N806
    t = wall_in
    d = D - 2 * t
    S = math.pi * (D**4 - d**4) / (32 * D)  # noqa: N806
    return S


def bending_capacity_lb_in(
    S_in3: float,  # noqa: N803
    fy_ksi: float,
    omega: float = 1.67,
) -> float:
    """Allowable moment in lb-in."""
    fy_psi = fy_ksi * 1000.0
    M_allow = (fy_psi * S_in3) / omega  # noqa: N806
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
        S = post.section_modulus_in3  # noqa: N806
    elif post.od_in is not None and post.wall_in is not None:
        S = section_modulus_pipe(post.od_in, post.wall_in)  # noqa: N806
    else:
        # No geometry -> skip check
        return (0.0, 0.0, True)

    # 2) Allowable moment
    M_allow = bending_capacity_lb_in(S, post.fy_ksi)  # noqa: N806

    # 3) Demand moment (0.6 H above grade, inches)
    lever_arm_in = 0.6 * height_ft * 12.0
    M_demand = load_per_post_lb * lever_arm_in  # noqa: N806

    is_ok = M_demand <= M_allow
    return (M_demand, M_allow, is_ok)


# Table-based spacing lookup
TABLE_DIR = Path(__file__).resolve().parent / "data" / "WLC Tables"

# Available wind speed tables (will be populated if tables exist)
_AVAILABLE_WS: list[int] = []

if TABLE_DIR.exists():
    _AVAILABLE_WS = sorted(
        int(p.stem.replace("mph", "")) for p in TABLE_DIR.glob("*mph.csv")
    )


@lru_cache(maxsize=32)
def _load_ws_tables(ws_mph: int) -> dict[PostGroup, dict[str, dict[float, float]]]:
    """
    Parse one <ws>mph.csv into:
      { group: { table_label: { height_ft: spacing_ft } } }

    Returns empty dicts if file doesn't exist or can't be parsed.
    """
    path = TABLE_DIR / f"{ws_mph}mph.csv"
    tables: dict[PostGroup, dict[str, dict[float, float]]] = {
        "IA_REG": {},
        "IA_HIGH": {},
        "IC_PIPE": {},
        "II_CSHAPE": {},
    }

    if not path.exists():
        return tables

    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            _rows = list(reader)

        # TODO: Implement full CSV parsing logic here
        # The CSV structure needs to be analyzed to properly parse:
        # - Height rows (e.g., "Height -->")
        # - Post size rows with spacing values
        # - Group assignments (IA_REG, IA_HIGH, IC_PIPE, II_CSHAPE)
        # For now, return empty tables - this will fall back to Cf-based calculation

    except Exception:
        # If parsing fails, return empty tables (will use Cf fallback)
        pass

    return tables


def compute_max_spacing_from_tables(
    post_key: str,
    wind_speed_mph: float,
    height_ft: float,
) -> float | None:
    """
    Look up max spacing from CSV tables if available.
    Returns None if tables don't exist or post isn't found.
    """
    post = POST_TYPES[post_key]
    if not post.table_label:
        return None  # nothing to look up

    # Choose conservative wind speed table
    if not _AVAILABLE_WS:
        return None  # no tables available

    ws_candidates = [ws for ws in _AVAILABLE_WS if ws >= wind_speed_mph]
    ws_use = _AVAILABLE_WS[-1] if not ws_candidates else ws_candidates[0]

    all_tables = _load_ws_tables(ws_use)
    group_tables = all_tables.get(post.group, {})
    row = group_tables.get(post.table_label)
    if not row:
        return None

    # Choose height column: smallest tabulated height >= requested height
    heights = sorted(h for h in row if h is not None)
    if not heights:
        return None

    chosen_h = None
    for h in heights:
        if h >= height_ft:
            chosen_h = h
            break
    if chosen_h is None:
        chosen_h = heights[-1]  # if fence taller than table, use most conservative

    spacing = row[chosen_h]
    return spacing


__all__ = [
    "CF1_TABLE",
    "DEFAULT_CF3",
    "EXPOSURE_CF2",
    "POST_TYPES",
    "PostGroup",
    "PostType",
    "bending_capacity_lb_in",
    "compute_max_spacing_cf",
    "compute_max_spacing_from_tables",
    "compute_moment_check",
    "get_cf1",
    "section_modulus_pipe",
]

