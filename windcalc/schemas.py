"""Pydantic schemas for windcalc data models."""

from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field, computed_field


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
    project_name: Optional[str] = Field(None, description="Optional project identifier")


class WindLoadResult(BaseModel):
    """Result model for wind load calculation."""

    project_name: Optional[str] = None
    design_pressure: float = Field(..., description="Design wind pressure in psf")
    total_load: float = Field(..., description="Total wind load in lbs")
    fence_specs: FenceSpecs
    wind_conditions: WindConditions
    calculation_notes: Optional[str] = None


# Wizard-friendly schemas
class Recommendation(BaseModel):
    """Recommended post and footing selection."""

    post_key: Optional[str] = Field(None, description="Catalog key for the recommended post")
    post_label: Optional[str] = Field(
        None, description="Human-friendly label sourced from POST_TYPES"
    )
    # Kept for backward compatibility with legacy UI strings; prefer post_key/post_label.
    post_size: Optional[str] = Field(
        None, description="Deprecated: legacy post size label (use post_key instead)"
    )
    footing_diameter_in: Optional[float] = Field(None, description="Footing diameter in inches")
    embedment_in: Optional[float] = Field(None, description="Embedment depth in inches")


class EstimateInput(BaseModel):
    """Inputs for a bay-style wind load estimate."""

    wind_speed_mph: float = Field(..., gt=0, description="Design wind speed in mph")
    height_total_ft: float = Field(..., gt=0, description="Total fence height in feet")
    post_spacing_ft: float = Field(..., gt=0, description="Spacing between posts in feet")
    exposure: str = Field(default="C", description="Exposure category (B, C, or D)")
    soil_type: Optional[str] = Field(None, description="Optional soil descriptor")
    post_role: Literal["line", "terminal"] = Field(
        default="line",
        description="Post role (line or terminal) for bending treatment",
    )
    post_key: Optional[str] = Field(
        None, description="Optional post key override (e.g., '2_3_8_SS40')"
    )
    post_size: Optional[str] = Field(
        None,
        description="Legacy post size override string (e.g., '2-3/8\" SS40'); prefer post_key",
    )

    @computed_field
    @property
    def area_per_bay_ft2(self) -> float:
        """Calculated tributary area for a single bay."""

        return self.height_total_ft * self.post_spacing_ft


class EstimateOutput(BaseModel):
    """Wind load estimate for a single bay."""

    pressure_psf: float = Field(..., description="Applied pressure in psf")
    area_per_bay_ft2: float = Field(..., description="Area of a single bay in square feet")
    total_load_lb: float = Field(..., description="Total load on a bay in pounds")
    load_per_post_lb: float = Field(..., description="Load per post in pounds")
    recommended: Recommendation
    warnings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    max_spacing_ft: Optional[float] = Field(None, description="Maximum recommended spacing for the chosen post (if fixed)")
    M_demand_ft_lb: Optional[float] = Field(None, description="Bending moment demand in ft·lb (if post specified)")
    M_allow_ft_lb: Optional[float] = Field(None, description="Allowable bending moment in ft·lb (if post specified)")


__all__ = [
    "FenceSpecs",
    "WindConditions",
    "WindLoadRequest",
    "WindLoadResult",
    "Recommendation",
    "EstimateInput",
    "EstimateOutput",
]
