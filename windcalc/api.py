"""FastAPI REST API router for windcalc."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from windcalc.concrete import calculate_concrete_estimate
from windcalc.engine import calculate, calculate_project, calculate_wind_load
from windcalc.schemas import (
    ConcreteEstimateInput,
    ConcreteEstimateOutput,
    EstimateInput,
    EstimateOutput,
    ProjectInput,
    ProjectOutput,
    WindLoadRequest,
    WindLoadResult,
)

logger = logging.getLogger(__name__)

# ── Legacy API (backward compatible) ─────────────────────────────────
router = APIRouter(prefix="/api", tags=["api"])


@router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Windcalc API",
        "version": "0.2.0",
        "endpoints": [
            "/api/calculate",
            "/api/health",
            "/api/v1/estimate",
            "/api/v1/concrete-estimate",
        ],
    }


@router.get("/health")
async def api_health():
    """API health check endpoint."""
    return {"status": "healthy"}


@router.post("/calculate", response_model=WindLoadResult)
async def legacy_calculate(request: WindLoadRequest):
    """Calculate wind load (legacy endpoint).

    .. deprecated:: 0.2.0
        Use ``POST /api/v1/estimate`` with :class:`EstimateInput` instead.
    """
    try:
        result = calculate_wind_load(request)
        return result
    except ValueError as e:
        logger.warning("Calculation error: %s", e)
        raise HTTPException(status_code=400, detail=f"Calculation error: {e!s}") from e
    except Exception:
        logger.exception("Unexpected error during calculation")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during calculation"
        ) from None


# ── Modern API v1 ────────────────────────────────────────────────────
v1_router = APIRouter(prefix="/api/v1", tags=["api-v1"])


@v1_router.post("/estimate", response_model=EstimateOutput)
async def estimate(request: EstimateInput):
    """Calculate ASCE 7-22 wind load estimate for a fence bay.

    Accepts full :class:`EstimateInput` with dual line/terminal post
    selection, fence type, exposure, and optional fence run length
    for B/s aspect ratio.

    Returns :class:`EstimateOutput` with pressure, loads, bending checks,
    spacing checks, utilization ratios, and status (GREEN/YELLOW/RED).
    """
    try:
        result = calculate(request)
        return result
    except ValueError as e:
        logger.warning("Estimate error: %s", e)
        raise HTTPException(status_code=400, detail=f"Estimate error: {e!s}") from e
    except Exception:
        logger.exception("Unexpected error during estimate")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred"
        ) from None


@v1_router.post("/concrete-estimate", response_model=ConcreteEstimateOutput)
async def concrete_estimate(request: ConcreteEstimateInput):
    """Calculate fence concrete takeoff for one or more hole-spec rows."""
    try:
        return calculate_concrete_estimate(request)
    except ValueError as e:
        logger.warning("Concrete estimate error: %s", e)
        raise HTTPException(status_code=400, detail=f"Concrete estimate error: {e!s}") from e
    except Exception:
        logger.exception("Unexpected error during concrete estimate")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred"
        ) from None


@v1_router.get("/fence-types")
async def list_fence_types():
    """List available fence types with solidity ratios."""
    from windcalc.asce7 import FENCE_TYPES

    return {
        "fence_types": [
            {
                "key": ft.key,
                "label": ft.label,
                "solidity": ft.solidity,
                "description": ft.description,
            }
            for ft in FENCE_TYPES.values()
        ]
    }


@v1_router.get("/post-types")
async def list_post_types():
    """List available post types with section properties."""
    from windcalc.post_catalog import POST_TYPES

    return {
        "post_types": [
            {
                "key": p.key,
                "label": p.label,
                "group": p.group,
                "od_in": p.od_in,
                "wall_in": p.wall_in,
                "fy_ksi": p.fy_ksi,
            }
            for p in POST_TYPES.values()
            if p.group == "IC_PIPE"
        ]
    }


@v1_router.post("/project", response_model=ProjectOutput)
async def project_estimate(request: ProjectInput):
    """Multi-segment fence project analysis.

    Accepts a project with shared wind parameters and multiple fence
    segments. Returns per-segment results, combined quantities, and
    overall status.
    """
    try:
        return calculate_project(request)
    except ValueError as e:
        logger.warning("Project estimate error: %s", e)
        raise HTTPException(status_code=400, detail=f"Project error: {e!s}") from e
    except Exception:
        logger.exception("Unexpected error during project estimate")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred"
        ) from None


@v1_router.get("/wind-speed-lookup")
async def wind_speed_lookup(zip_code: str, risk_category: str = "II"):
    """Look up approximate ASCE 7-22 wind speed from ZIP code."""
    from windcalc.wind_speed_lookup import lookup_wind_speed

    speed, region = lookup_wind_speed(zip_code, risk_category)
    return {
        "zip_code": zip_code,
        "risk_category": risk_category,
        "wind_speed_mph": speed,
        "region": region,
    }


@v1_router.get("/soil-classes")
async def list_soil_classes():
    """List available soil classes for footing checks."""
    from windcalc.footing import SOIL_CLASSES

    return {
        "soil_classes": [
            {"key": k, "label": label, "lateral_bearing_psf_per_ft": value}
            for k, (label, value) in SOIL_CLASSES.items()
        ]
    }
