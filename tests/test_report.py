"""Tests for windcalc report module."""

import tempfile
from pathlib import Path

from windcalc.report import generate_pdf_report


def test_generate_pdf_report_basic():
    """Test basic PDF report generation."""
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
        output_path = f.name

    try:
        generate_pdf_report(data, output_path)
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_generate_pdf_report_no_project_name():
    """Test PDF generation without project name."""
    data = {
        "design_pressure": 25.0,
        "total_load": 15000.0,
        "fence_specs": {"height": 6.0, "width": 100.0, "material": "wood", "location": "Test"},
        "wind_conditions": {"wind_speed": 90.0, "exposure_category": "B", "importance_factor": 1.0},
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    try:
        generate_pdf_report(data, output_path)
        assert Path(output_path).exists()
    finally:
        Path(output_path).unlink(missing_ok=True)
