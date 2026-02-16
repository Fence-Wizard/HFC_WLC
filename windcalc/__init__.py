"""Windcalc - Local-first wind load calculator for fence projects."""

from windcalc.engine import calculate, calculate_project, calculate_wind_load
from windcalc.risk import classify_risk
from windcalc.schemas import (
    EstimateInput,
    EstimateOutput,
    ProjectInput,
    ProjectOutput,
    Recommendation,
    WindConditions,
    WindLoadRequest,
    WindLoadResult,
)

__version__ = "0.1.0"

__all__ = [
    "EstimateInput",
    "EstimateOutput",
    "ProjectInput",
    "ProjectOutput",
    "Recommendation",
    "WindConditions",
    "WindLoadRequest",
    "WindLoadResult",
    "__version__",
    "calculate",
    "calculate_project",
    "calculate_wind_load",
    "classify_risk",
]
