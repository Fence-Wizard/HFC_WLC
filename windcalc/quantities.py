"""Material quantity takeoff for fence projects.

Computes post counts, concrete volumes, top rail, and fabric
quantities for a fence run or multi-segment project.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from windcalc.post_catalog import POST_TYPES


@dataclass(frozen=True)
class SegmentQuantities:
    """Material quantities for a single fence segment."""

    fence_length_ft: float
    height_ft: float
    post_spacing_ft: float

    num_line_posts: int = 0
    num_terminal_posts: int = 0
    num_corner_posts: int = 0
    num_gate_posts: int = 0
    total_posts: int = 0

    top_rail_lf: float = 0.0
    fabric_sf: float = 0.0

    concrete_per_line_cf: float = 0.0
    concrete_per_terminal_cf: float = 0.0
    total_concrete_cf: float = 0.0
    total_concrete_cy: float = 0.0

    line_post_length_ft: float = 0.0
    terminal_post_length_ft: float = 0.0


@dataclass
class ProjectQuantities:
    """Aggregated material quantities across all segments."""

    segments: list[SegmentQuantities] = field(default_factory=list)

    @property
    def total_line_posts(self) -> int:
        return sum(s.num_line_posts for s in self.segments)

    @property
    def total_terminal_posts(self) -> int:
        return sum(s.num_terminal_posts for s in self.segments)

    @property
    def total_corner_posts(self) -> int:
        return sum(s.num_corner_posts for s in self.segments)

    @property
    def total_gate_posts(self) -> int:
        return sum(s.num_gate_posts for s in self.segments)

    @property
    def total_posts(self) -> int:
        return sum(s.total_posts for s in self.segments)

    @property
    def total_top_rail_lf(self) -> float:
        return round(sum(s.top_rail_lf for s in self.segments), 1)

    @property
    def total_fabric_sf(self) -> float:
        return round(sum(s.fabric_sf for s in self.segments), 1)

    @property
    def total_concrete_cf(self) -> float:
        return round(sum(s.total_concrete_cf for s in self.segments), 2)

    @property
    def total_concrete_cy(self) -> float:
        return round(self.total_concrete_cf / 27.0, 2)


def _concrete_volume_cf(diameter_in: float, depth_in: float) -> float:
    """Concrete volume for a cylindrical pier (cubic feet)."""
    r_ft = (diameter_in / 2.0) / 12.0
    d_ft = depth_in / 12.0
    return math.pi * r_ft**2 * d_ft


def compute_segment_quantities(
    fence_length_ft: float,
    height_ft: float,
    post_spacing_ft: float,
    line_post_key: str | None = None,
    terminal_post_key: str | None = None,
    num_terminals: int = 2,
    num_corners: int = 0,
    num_gates: int = 0,
    embedment_override_in: float | None = None,
    footing_diameter_override_in: float | None = None,
) -> SegmentQuantities:
    """Compute material quantities for a single fence segment.

    Parameters
    ----------
    fence_length_ft : float
        Total fence run length in feet.
    height_ft : float
        Fence height above grade in feet.
    post_spacing_ft : float
        On-center post spacing in feet.
    line_post_key : str or None
        Catalog key for line posts (for footing defaults).
    terminal_post_key : str or None
        Catalog key for terminal posts (for footing defaults).
    num_terminals : int
        Number of terminal (end) posts (default 2).
    num_corners : int
        Number of corner posts.
    num_gates : int
        Number of gate posts (typically 2 per gate opening).
    embedment_override_in : float or None
        User override for embedment depth (inches).
    footing_diameter_override_in : float or None
        User override for footing diameter (inches).

    Returns
    -------
    SegmentQuantities
    """
    # Post counts
    total_bays = max(round(fence_length_ft / post_spacing_ft), 1)
    special_posts = num_terminals + num_corners + num_gates
    num_line = max(total_bays - 1, 0)
    total = num_line + special_posts

    # Lookup footing defaults from catalog
    line_post = POST_TYPES.get(line_post_key or "")
    term_post = POST_TYPES.get(terminal_post_key or "")

    line_footing_dia = footing_diameter_override_in or (
        line_post.footing_diameter_in if line_post else 10.0
    )
    line_embed = embedment_override_in or (
        line_post.footing_embedment_in if line_post else 24.0
    )
    term_footing_dia = footing_diameter_override_in or (
        term_post.footing_diameter_in if term_post else 16.0
    )
    term_embed = embedment_override_in or (
        term_post.footing_embedment_in if term_post else 36.0
    )

    # Concrete per footing
    concrete_line = _concrete_volume_cf(line_footing_dia, line_embed)
    concrete_term = _concrete_volume_cf(term_footing_dia, term_embed)

    total_concrete = (
        num_line * concrete_line + special_posts * concrete_term
    )

    # Post total lengths (above grade + embedment)
    line_post_len = height_ft + (line_embed / 12.0)
    term_post_len = height_ft + (term_embed / 12.0)

    # Top rail and fabric
    top_rail = fence_length_ft
    fabric = fence_length_ft * height_ft

    return SegmentQuantities(
        fence_length_ft=round(fence_length_ft, 1),
        height_ft=round(height_ft, 1),
        post_spacing_ft=round(post_spacing_ft, 1),
        num_line_posts=num_line,
        num_terminal_posts=num_terminals,
        num_corner_posts=num_corners,
        num_gate_posts=num_gates,
        total_posts=total,
        top_rail_lf=round(top_rail, 1),
        fabric_sf=round(fabric, 1),
        concrete_per_line_cf=round(concrete_line, 3),
        concrete_per_terminal_cf=round(concrete_term, 3),
        total_concrete_cf=round(total_concrete, 2),
        total_concrete_cy=round(total_concrete / 27.0, 2),
        line_post_length_ft=round(line_post_len, 2),
        terminal_post_length_ft=round(term_post_len, 2),
    )


__all__ = [
    "ProjectQuantities",
    "SegmentQuantities",
    "compute_segment_quantities",
]
