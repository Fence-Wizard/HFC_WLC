"""ASCE 7-22 wind load calculations for freestanding fences and walls.

Implements velocity pressure (Eq. 26.10-1), gust-effect factor,
and force coefficients for solid and porous freestanding walls
per ASCE 7-22 Chapters 26 and 29.

References
----------
ASCE/SEI 7-22, *Minimum Design Loads and Associated Criteria
for Buildings and Other Structures*.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── ASCE 7-22 Edition Tag ────────────────────────────────────────────
ASCE7_EDITION = "ASCE 7-22"

# ── Exposure parameters (ASCE 7-22 Table 26.11-1) ───────────────────
#   exposure: (alpha, zg_ft)
_EXPOSURE_CONSTANTS: dict[str, tuple[float, float]] = {
    "B": (7.0, 1200.0),
    "C": (9.5, 900.0),
    "D": (11.5, 700.0),
}

# ── Wind directionality factor (ASCE 7-22 Table 26.6-1) ─────────────
#   "Open signs and lattice framework" -> Kd = 0.85
KD_FENCE = 0.85

# ── Gust-effect factor for rigid structures (Section 26.11) ─────────
G_RIGID = 0.85

# ── Cf for solid freestanding walls at ground level ──────────────────
#   ASCE 7-22 Figure 29.3-1, Case A, s/h = 0 (ground-mounted).
#   Interpolation table: (B/s ratio, Cf)
_CF_SOLID_TABLE: list[tuple[float, float]] = [
    (2.0, 1.2),
    (5.0, 1.3),
    (10.0, 1.4),
    (20.0, 1.5),
    (45.0, 1.75),
]

# Default for long fence runs where total length is not known.
# B/s >= 20 is typical for commercial fence runs (e.g. 200 ft / 8 ft = 25).
CF_SOLID_LONG_FENCE = 1.5


# ── Fence Types ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class FenceTypeInfo:
    """Definition of a fence type with its solidity ratio."""

    key: str
    label: str
    solidity: float
    description: str


FENCE_TYPES: dict[str, FenceTypeInfo] = {
    "chain_link_open": FenceTypeInfo(
        key="chain_link_open",
        label="Open Chain Link",
        solidity=0.35,
        description=(
            "Standard chain link fabric, no screen or slats. "
            "Approximately 35% solid."
        ),
    ),
    "chain_link_windscreen_50": FenceTypeInfo(
        key="chain_link_windscreen_50",
        label="Chain Link w/ 50% Windscreen",
        solidity=0.50,
        description="Chain link with 50% windscreen mesh.",
    ),
    "chain_link_windscreen_80": FenceTypeInfo(
        key="chain_link_windscreen_80",
        label="Chain Link w/ 80% Windscreen",
        solidity=0.80,
        description="Chain link with 80% privacy windscreen.",
    ),
    "chain_link_slats": FenceTypeInfo(
        key="chain_link_slats",
        label="Chain Link w/ Privacy Slats",
        solidity=0.85,
        description=(
            "Chain link with vertical privacy slats. "
            "Approximately 85% solid."
        ),
    ),
    "solid_panel": FenceTypeInfo(
        key="solid_panel",
        label="Solid Panel (Wood / Vinyl / Metal)",
        solidity=1.0,
        description="Solid fence panel. 100% solid.",
    ),
}


# ── Core Calculation Functions ───────────────────────────────────────


def compute_kz(height_ft: float, exposure: str) -> float:
    """Velocity pressure exposure coefficient Kz.

    Per ASCE 7-22 Table 26.10-1:
        Kz = 2.01 * (z / zg) ^ (2 / alpha)

    For z <= 15 ft, use z = 15 ft (table minimum).

    Parameters
    ----------
    height_ft : float
        Height above ground level in feet.
    exposure : str
        Exposure category: ``"B"``, ``"C"``, or ``"D"``.

    Returns
    -------
    float
        Dimensionless Kz coefficient.

    Raises
    ------
    KeyError
        If *exposure* is not B, C, or D.
    """
    alpha, zg = _EXPOSURE_CONSTANTS[exposure.upper()]
    z = max(height_ft, 15.0)
    return 2.01 * (z / zg) ** (2.0 / alpha)


def compute_qz(
    wind_speed_mph: float,
    height_ft: float,
    exposure: str,
    kzt: float = 1.0,
) -> float:
    """Velocity pressure qz in pounds per square foot (psf).

    Per ASCE 7-22 Eq. 26.10-1::

        qz = 0.00256 * Kz * Kzt * Kd * V^2

    Parameters
    ----------
    wind_speed_mph : float
        Basic wind speed V in mph (3-second gust at 33 ft).
    height_ft : float
        Reference height in feet.
    exposure : str
        Exposure category (B, C, or D).
    kzt : float
        Topographic factor. 1.0 for flat terrain (default).

    Returns
    -------
    float
        Velocity pressure in psf.
    """
    kz = compute_kz(height_ft, exposure)
    return 0.00256 * kz * kzt * KD_FENCE * wind_speed_mph**2


def compute_cf_solid(aspect_ratio_bs: float | None = None) -> float:
    """Force coefficient Cf for a **solid** freestanding wall at ground level.

    Per ASCE 7-22 Figure 29.3-1, Case A, s/h = 0.

    Parameters
    ----------
    aspect_ratio_bs : float or None
        B/s where B = fence run length, s = fence height.
        If ``None``, assumes a long fence run (B/s >= 20, Cf = 1.5).

    Returns
    -------
    float
        Cf for solid wall.
    """
    if aspect_ratio_bs is None:
        return CF_SOLID_LONG_FENCE

    # Clamp to table range
    if aspect_ratio_bs <= _CF_SOLID_TABLE[0][0]:
        return _CF_SOLID_TABLE[0][1]
    if aspect_ratio_bs >= _CF_SOLID_TABLE[-1][0]:
        return _CF_SOLID_TABLE[-1][1]

    # Linear interpolation
    for i in range(len(_CF_SOLID_TABLE) - 1):
        bs_lo, cf_lo = _CF_SOLID_TABLE[i]
        bs_hi, cf_hi = _CF_SOLID_TABLE[i + 1]
        if bs_lo <= aspect_ratio_bs <= bs_hi:
            t = (aspect_ratio_bs - bs_lo) / (bs_hi - bs_lo)
            return cf_lo + t * (cf_hi - cf_lo)

    return _CF_SOLID_TABLE[-1][1]  # pragma: no cover


def compute_cf(
    solidity: float,
    aspect_ratio_bs: float | None = None,
) -> float:
    """Effective force coefficient Cf adjusted for fence porosity.

    For porous fences, the force coefficient is reduced linearly
    by the solidity ratio::

        Cf = Cf_solid * epsilon

    This is a simplified but commonly used approach for fence design.

    Parameters
    ----------
    solidity : float
        Solidity ratio epsilon (0.0 to 1.0). 1.0 = fully solid.
    aspect_ratio_bs : float or None
        Optional B/s ratio. ``None`` = long fence run.

    Returns
    -------
    float
        Effective net force coefficient.
    """
    cf_solid = compute_cf_solid(aspect_ratio_bs)
    return cf_solid * max(solidity, 0.0)


@dataclass(frozen=True)
class DesignPressureResult:
    """Container for the full ASCE 7 design pressure breakdown."""

    design_pressure_psf: float
    qz_psf: float
    kz: float
    kzt: float
    kd: float
    g: float
    cf_solid: float
    cf: float
    solidity: float
    fence_type: str
    asce7_edition: str = ASCE7_EDITION


def compute_design_pressure(
    wind_speed_mph: float,
    height_ft: float,
    exposure: str,
    solidity: float,
    kzt: float = 1.0,
    fence_type: str = "chain_link_open",
    aspect_ratio_bs: float | None = None,
) -> DesignPressureResult:
    """Full design wind pressure on a fence surface.

    Combines all ASCE 7-22 factors::

        p = qz * G * Cf  (psf)

    where qz = 0.00256 * Kz * Kzt * Kd * V^2.

    Parameters
    ----------
    wind_speed_mph : float
        Basic wind speed V in mph.
    height_ft : float
        Fence height in feet.
    exposure : str
        Exposure category (B, C, or D).
    solidity : float
        Solidity ratio (0.0 to 1.0).
    kzt : float
        Topographic factor (default 1.0).
    fence_type : str
        Fence type key for documentation.
    aspect_ratio_bs : float or None
        Optional B/s ratio.

    Returns
    -------
    DesignPressureResult
        Dataclass with design pressure and all intermediate values.
    """
    kz = compute_kz(height_ft, exposure)
    qz = compute_qz(wind_speed_mph, height_ft, exposure, kzt)
    cf_solid = compute_cf_solid(aspect_ratio_bs)
    cf = compute_cf(solidity, aspect_ratio_bs)
    pressure = qz * G_RIGID * cf

    return DesignPressureResult(
        design_pressure_psf=round(pressure, 2),
        qz_psf=round(qz, 2),
        kz=round(kz, 4),
        kzt=kzt,
        kd=KD_FENCE,
        g=G_RIGID,
        cf_solid=round(cf_solid, 3),
        cf=round(cf, 3),
        solidity=solidity,
        fence_type=fence_type,
    )


__all__ = [
    "ASCE7_EDITION",
    "CF_SOLID_LONG_FENCE",
    "FENCE_TYPES",
    "G_RIGID",
    "KD_FENCE",
    "DesignPressureResult",
    "FenceTypeInfo",
    "compute_cf",
    "compute_cf_solid",
    "compute_design_pressure",
    "compute_kz",
    "compute_qz",
]
