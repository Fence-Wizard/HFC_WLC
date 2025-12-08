"""Pydantic schemas for windcalc data models."""

from typing import Optional

from pydantic import BaseModel, Field


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
