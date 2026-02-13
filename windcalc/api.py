"""FastAPI REST API router for windcalc."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from windcalc.engine import calculate_wind_load
from windcalc.schemas import WindLoadRequest, WindLoadResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Windcalc API",
        "version": "0.1.0",
        "endpoints": ["/api/calculate", "/api/health", "/api/projects"],
    }


@router.get("/health")
async def api_health():
    """API health check endpoint."""
    return {"status": "healthy"}


@router.post("/calculate", response_model=WindLoadResult)
async def calculate(request: WindLoadRequest):
    """
    Calculate wind load for fence project.

    Args:
        request: WindLoadRequest with fence specs and wind conditions

    Returns:
        WindLoadResult with calculated wind loads

    Raises:
        HTTPException: 400 for calculation errors
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


@router.get("/projects")
async def list_projects():
    """
    List saved projects (placeholder).

    Returns:
        List of saved projects
    """
    return {"projects": []}
