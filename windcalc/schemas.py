"""Pydantic schemas for windcalc data models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator


# Legacy schemas retained for backward compatibility with the JSON API.
class FenceSpecs(BaseModel):
    """Fence specifications for wind load calculation."""

    height: float = Field(..., description="Fence height in feet", gt=0)
    width: float = Field(..., description="Fence width/length in feet", gt=0)
    material: str = Field(..., description="Fence material type")
    location: str = Field(..., description="Installation location")


class WindConditions(BaseModel):
    """Wind conditions for calculation."""

    wind_speed: float = Field(..., description="Design wind speed in mph", gt=0)
    exposure_category: str = Field(default="B", description="Exposure category (A, B, C, D)")
    importance_factor: float = Field(default=1.0, description="Importance factor", gt=0)


class WindLoadRequest(BaseModel):
    """Request model for wind load calculation."""

    fence: FenceSpecs
    wind: WindConditions
    project_name: str | None = Field(None, description="Optional project identifier")


class WindLoadResult(BaseModel):
    """Result model for wind load calculation."""

    project_name: str | None = None
    design_pressure: float = Field(..., description="Design wind pressure in psf")
    total_load: float = Field(..., description="Total wind load in lbs")
    fence_specs: FenceSpecs
    wind_conditions: WindConditions
    calculation_notes: str | None = None


# Wizard-friendly schemas
class Recommendation(BaseModel):
    """Recommended post and footing selection."""

    post_key: str | None = Field(None, description="Catalog key for the recommended post")
    post_label: str | None = Field(
        None, description="Human-friendly label sourced from POST_TYPES"
    )
    # Kept for backward compatibility with legacy UI strings; prefer post_key/post_label.
    post_size: str | None = Field(
        None, description="Deprecated: legacy post size label (use post_key instead)"
    )
    footing_diameter_in: float | None = Field(None, description="Footing diameter in inches")
    embedment_in: float | None = Field(None, description="Embedment depth in inches")


class EstimateInput(BaseModel):
    """Inputs for a bay-style wind load estimate."""

    wind_speed_mph: float = Field(
        ..., gt=0, le=300, description="Design wind speed in mph (ASCE 7 range)"
    )
    height_total_ft: float = Field(
        ..., gt=0, le=50, description="Total fence height in feet"
    )
    post_spacing_ft: float = Field(
        ..., gt=0, le=30, description="Spacing between posts in feet"
    )
    fence_length_ft: float | None = Field(
        None,
        gt=0,
        description=(
            "Total fence run length in feet (optional). "
            "Used to compute B/s aspect ratio for Cf lookup. "
            "If omitted, B/s >= 20 (long run) is assumed."
        ),
    )
    exposure: Literal["B", "C", "D"] = Field(
        default="C", description="Exposure category (B, C, or D)"
    )
    fence_type: str = Field(
        default="chain_link_open",
        description="Fence type key (determines solidity ratio and Cf)",
    )
    risk_category: Literal["I", "II", "III", "IV"] = Field(
        default="III",
        description="Risk category (I-IV) per ASCE 7-22 Table 1.5-1",
    )
    soil_type: str | None = Field(
        None, description="Soil class key for footing check (e.g. 'sand', 'clay')"
    )
    # Topographic factor Kzt (ASCE 7-22 Section 26.8)
    kzt: float = Field(
        default=1.0,
        ge=1.0,
        le=3.0,
        description="Topographic factor Kzt (1.0 for flat terrain, >1.0 for hills/ridges)",
    )
    # Embedment overrides
    embedment_depth_in: float | None = Field(
        None, gt=0, le=120, description="User override for embedment depth (inches)"
    )
    footing_diameter_in: float | None = Field(
        None, gt=0, le=60, description="User override for footing diameter (inches)"
    )
    # Dual post selections
    line_post_key: str | None = Field(
        None, description="Optional line post key override (e.g., '2_3_8_SS40')"
    )
    terminal_post_key: str | None = Field(
        None, description="Optional terminal post key override (e.g., '3_1_2_SS40')"
    )
    # Gate / corner post selections
    gate_post_key: str | None = Field(
        None, description="Optional gate post key override"
    )
    corner_post_key: str | None = Field(
        None, description="Optional corner post key override"
    )
    num_gates: int = Field(
        default=0, ge=0, description="Number of gate openings (each needs 2 gate posts)"
    )
    num_corners: int = Field(
        default=0, ge=0, description="Number of corners"
    )
    # Deprecated single selections (kept for backward compatibility)
    post_role: Literal["line", "terminal"] = Field(
        default="line",
        description="Deprecated: single post role; prefer line/terminal post keys",
    )
    post_key: str | None = Field(
        None, description="Deprecated: single post key override (prefer line/terminal keys)"
    )
    post_size: str | None = Field(
        None,
        description="Legacy post size override string (e.g., '2-3/8\" SS40'); prefer post_key",
    )

    @field_validator("exposure", mode="before")
    @classmethod
    def _normalize_exposure(cls, v: str) -> str:
        return v.upper() if isinstance(v, str) else v

    @computed_field
    @property
    def area_per_bay_ft2(self) -> float:
        """Calculated tributary area for a single bay."""
        return self.height_total_ft * self.post_spacing_ft

    @computed_field
    @property
    def aspect_ratio_bs(self) -> float | None:
        """B/s aspect ratio (fence length / height), or None if length unknown."""
        if self.fence_length_ft and self.height_total_ft > 0:
            return self.fence_length_ft / self.height_total_ft
        return None


class DesignParameters(BaseModel):
    """ASCE 7-22 intermediate calculation values for traceability."""

    asce7_edition: str = Field(default="ASCE 7-22", description="Code edition")
    kz: float = Field(..., description="Velocity pressure exposure coefficient")
    kzt: float = Field(default=1.0, description="Topographic factor")
    kd: float = Field(..., description="Wind directionality factor")
    g: float = Field(..., description="Gust-effect factor (rigid)")
    cf_solid: float = Field(
        ..., description="Force coefficient for solid wall (ASCE 7-22 Fig. 29.3-1)"
    )
    cf: float = Field(
        ..., description="Net force coefficient (Cf_solid x solidity)"
    )
    solidity: float = Field(
        ..., description="Solidity ratio epsilon (0-1)"
    )
    fence_type: str = Field(..., description="Fence type key")
    qz_psf: float = Field(..., description="Velocity pressure in psf")


class FootingResult(BaseModel):
    """Results from the IBC 1807.3 lateral soil resistance check."""

    overturning_moment_ft_lb: float = 0.0
    resisting_moment_ft_lb: float = 0.0
    safety_factor: float = 0.0
    footing_ok: bool = True
    min_embedment_ft: float = 0.0
    actual_embedment_ft: float = 0.0
    footing_diameter_in: float = 0.0
    soil_label: str = ""
    concrete_volume_cf: float = 0.0


class DeflectionResult(BaseModel):
    """Results from the post deflection (serviceability) check."""

    deflection_in: float = 0.0
    allowable_in: float = 0.0
    deflection_ok: bool = True
    ratio: float = 0.0


class SharedResult(BaseModel):
    pressure_psf: float
    area_per_bay_ft2: float
    total_load_lb: float
    load_per_post_lb: float
    design_params: DesignParameters | None = None


class BlockResult(BaseModel):
    post_key: str | None = None
    post_label: str | None = None
    recommended: Recommendation
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    max_spacing_ft: float | None = None
    M_demand_ft_lb: float | None = None
    M_allow_ft_lb: float | None = None
    moment_ok: bool | None = None
    spacing_ratio: float | None = Field(
        None, description="Requested spacing / max spacing (>1.0 = over limit)"
    )
    moment_ratio: float | None = Field(
        None, description="M_demand / M_allow (>1.0 = over capacity)"
    )
    footing: FootingResult | None = None
    deflection: DeflectionResult | None = None
    status: Literal["GREEN", "YELLOW", "RED"] = "GREEN"


class QuantitiesResult(BaseModel):
    """Material quantity takeoff for a fence run."""

    fence_length_ft: float = 0.0
    num_line_posts: int = 0
    num_terminal_posts: int = 0
    num_corner_posts: int = 0
    num_gate_posts: int = 0
    total_posts: int = 0
    top_rail_lf: float = 0.0
    fabric_sf: float = 0.0
    total_concrete_cf: float = 0.0
    total_concrete_cy: float = 0.0
    line_post_length_ft: float = 0.0
    terminal_post_length_ft: float = 0.0


class EstimateOutput(BaseModel):
    """Wind load estimate for a single bay."""

    # Combined response
    shared: SharedResult
    line: BlockResult
    terminal: BlockResult
    overall_status: str = "GREEN"
    quantities: QuantitiesResult | None = None
    # Legacy top-level fields (mapped to line block for compatibility)
    pressure_psf: float = Field(
        ..., description="Applied pressure in psf (legacy; line block)"
    )
    area_per_bay_ft2: float = Field(
        ...,
        description="Area of a single bay in square feet (legacy; line block)",
    )
    total_load_lb: float = Field(
        ...,
        description="Total load on a bay in pounds (legacy; line block)",
    )
    load_per_post_lb: float = Field(
        ..., description="Load per post in pounds (legacy; line block)"
    )
    recommended: Recommendation
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    max_spacing_ft: float | None = Field(
        None,
        description="Maximum recommended spacing for the chosen post (legacy; line block)",
    )
    M_demand_ft_lb: float | None = Field(
        None,
        description="Bending moment demand in ft-lb (legacy; line block)",
    )
    M_allow_ft_lb: float | None = Field(
        None,
        description="Allowable bending moment in ft-lb (legacy; line block)",
    )


# ── Multi-segment schemas ────────────────────────────────────────────

class SegmentInput(BaseModel):
    """Input for a single fence segment in a multi-segment project."""

    label: str = Field(default="Segment 1", description="Segment label")
    height_total_ft: float = Field(..., gt=0, le=50)
    post_spacing_ft: float = Field(..., gt=0, le=30)
    fence_length_ft: float = Field(..., gt=0, le=50000)
    fence_type: str = Field(default="chain_link_open")
    line_post_key: str | None = None
    terminal_post_key: str | None = None
    gate_post_key: str | None = None
    corner_post_key: str | None = None
    num_terminals: int = Field(default=2, ge=0)
    num_corners: int = Field(default=0, ge=0)
    num_gates: int = Field(default=0, ge=0)


class ProjectInput(BaseModel):
    """Multi-segment project input with shared wind parameters."""

    wind_speed_mph: float = Field(..., gt=0, le=300)
    exposure: Literal["B", "C", "D"] = Field(default="C")
    risk_category: Literal["I", "II", "III", "IV"] = Field(default="III")
    kzt: float = Field(default=1.0, ge=1.0, le=3.0)
    soil_type: str | None = None
    embedment_depth_in: float | None = None
    footing_diameter_in: float | None = None
    segments: list[SegmentInput] = Field(..., min_length=1)

    # Project metadata
    project_name: str = ""
    location: str = ""
    estimator: str = ""


class SegmentOutput(BaseModel):
    """Output for a single segment in a multi-segment project."""

    label: str = ""
    estimate: EstimateOutput
    quantities: QuantitiesResult | None = None


class ProjectOutput(BaseModel):
    """Multi-segment project output with combined quantities."""

    segments: list[SegmentOutput] = Field(default_factory=list)
    overall_status: str = "GREEN"
    total_quantities: QuantitiesResult | None = None


__all__ = [
    "BlockResult",
    "DeflectionResult",
    "DesignParameters",
    "EstimateInput",
    "EstimateOutput",
    "FenceSpecs",
    "FootingResult",
    "ProjectInput",
    "ProjectOutput",
    "QuantitiesResult",
    "Recommendation",
    "SegmentInput",
    "SegmentOutput",
    "SharedResult",
    "WindConditions",
    "WindLoadRequest",
    "WindLoadResult",
]
