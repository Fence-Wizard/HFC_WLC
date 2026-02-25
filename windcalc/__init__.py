"""Windcalc - Local-first wind load calculator for fence projects."""

from windcalc.concrete import calculate_concrete_estimate
from windcalc.engine import calculate, calculate_project, calculate_wind_load
from windcalc.risk import classify_risk
from windcalc.schemas import (
    ConcreteEstimateInput,
    ConcreteEstimateOutput,
    ConcreteHoleSpecInput,
    ConcreteHoleSpecOutput,
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
    "ConcreteEstimateInput",
    "ConcreteEstimateOutput",
    "ConcreteHoleSpecInput",
    "ConcreteHoleSpecOutput",
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
    "calculate_concrete_estimate",
    "calculate_project",
    "calculate_wind_load",
    "classify_risk",
]
