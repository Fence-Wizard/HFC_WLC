"""Windcalc - Local-first wind load calculator for fence projects."""

from windcalc.engine import calculate, calculate_wind_load
from windcalc.schemas import (
    EstimateInput,
    EstimateOutput,
    Recommendation,
    WindConditions,
    WindLoadRequest,
    WindLoadResult,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "calculate",
    "calculate_wind_load",
    "EstimateInput",
    "EstimateOutput",
    "Recommendation",
    "WindConditions",
    "WindLoadRequest",
    "WindLoadResult",
]
