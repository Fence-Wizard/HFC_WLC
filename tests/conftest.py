"""Test data fixtures and golden test cases."""

import json
from pathlib import Path

GOLDEN_CASES_DIR = Path(__file__).parent / "golden_cases"


def get_golden_case(case_name: str) -> dict:
    """Load a golden test case from JSON file."""
    case_file = GOLDEN_CASES_DIR / f"{case_name}.json"
    with open(case_file, "r") as f:
        return json.load(f)


# Sample test data
SAMPLE_FENCE_SPECS = {
    "height": 6.0,
    "width": 100.0,
    "material": "wood",
    "location": "Test Location",
}

SAMPLE_WIND_CONDITIONS = {
    "wind_speed": 90.0,
    "exposure_category": "B",
    "importance_factor": 1.0,
}

SAMPLE_REQUEST = {
    "fence": SAMPLE_FENCE_SPECS,
    "wind": SAMPLE_WIND_CONDITIONS,
    "project_name": "Test Project",
}
