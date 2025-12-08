"""FastAPI application for windcalc."""

from fastapi import FastAPI, HTTPException

from windcalc.engine import calculate_wind_load
from windcalc.schemas import WindLoadRequest, WindLoadResult

app = FastAPI(
    title="Windcalc API",
    description="Local-first wind load calculator for fence projects",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Windcalc API",
        "version": "0.1.0",
        "endpoints": ["/calculate", "/health"],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/calculate", response_model=WindLoadResult)
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
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")
    except Exception:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during calculation"
        )


@app.get("/api/projects")
async def list_projects():
    """
    List saved projects (placeholder).

    Returns:
        List of saved projects
    """
    return {"projects": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
