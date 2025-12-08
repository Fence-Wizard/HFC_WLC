"""Tests for windcalc report module."""

import tempfile
from pathlib import Path

from windcalc import EstimateInput, calculate
from windcalc.report import draw_pdf, generate_pdf_report


def test_draw_pdf_from_estimate():
    inp = EstimateInput(
        wind_speed_mph=100,
        height_total_ft=6,
        post_spacing_ft=8,
        exposure="C",
    )
    result = calculate(inp)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = Path(f.name)

    try:
        draw_pdf(output_path, inp, result)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    finally:
        output_path.unlink(missing_ok=True)


def test_generate_pdf_report_legacy():
    data = {
        "project_name": "Test Project",
        "design_pressure": 25.0,
        "total_load": 15000.0,
        "fence_specs": {
            "height": 6.0,
            "width": 100.0,
            "material": "wood",
            "location": "Test Location",
        },
        "wind_conditions": {
            "wind_speed": 90.0,
            "exposure_category": "B",
            "importance_factor": 1.0,
        },
        "calculation_notes": "Test notes",
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = Path(f.name)

    try:
        generate_pdf_report(data, str(output_path))
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    finally:
        output_path.unlink(missing_ok=True)
