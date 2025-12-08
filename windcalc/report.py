"""PDF report generation module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from windcalc.schemas import EstimateInput, EstimateOutput


def generate_pdf_report(data: dict[str, Any], output_path: str) -> None:
    """Legacy wrapper kept for backward compatibility."""

    path = Path(output_path)
    draw_pdf(path, None, None, extra=data)


def draw_pdf(
    output_path: Path, input_data: EstimateInput | None, result: EstimateOutput | None, extra: dict[str, Any] | None = None
) -> None:
    """Generate a PDF report for wind load calculation results."""

    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("Wind Load Calculation Report", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.25 * inch))

    if input_data:
        story.extend(_input_section(input_data, styles))

    if result:
        story.extend(_result_section(result, styles))

    if extra:
        story.extend(_legacy_section(extra, styles))

    doc.build(story)


def _input_section(data: EstimateInput, styles: dict[str, ParagraphStyle]):
    story = []
    story.append(Paragraph("<b>Inputs</b>", styles["Heading2"]))

    rows = [
        ["Wind speed", f"{data.wind_speed_mph} mph"],
        ["Exposure", data.exposure],
        ["Fence height", f"{data.height_total_ft} ft"],
        ["Post spacing", f"{data.post_spacing_ft} ft"],
        ["Soil type", data.soil_type or "default"],
        ["Bay area", f"{data.area_per_bay_ft2:.1f} ft^2"],
    ]

    table = Table(rows)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))
    return story


def _result_section(result: EstimateOutput, styles: dict[str, ParagraphStyle]):
    story = []
    story.append(Paragraph("<b>Results</b>", styles["Heading2"]))

    rows = [
        ["Pressure", f"{result.pressure_psf:.2f} psf"],
        ["Total load per bay", f"{result.total_load_lb:.0f} lb"],
        ["Load per post", f"{result.load_per_post_lb:.0f} lb"],
        [
            "Recommendation",
            f"{result.recommended.post_size or 'N/A'} footing {result.recommended.footing_diameter_in or 'N/A'}"  # type: ignore[str-format]
            f" in dia x {result.recommended.embedment_in or 'N/A'} in",
        ],
    ]

    table = Table(rows)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))

    if result.warnings:
        story.append(Paragraph("<b>Warnings</b>", styles["Heading3"]))
        for warning in result.warnings:
            story.append(Paragraph(f"- {warning}", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))

    if result.assumptions:
        story.append(Paragraph("<b>Assumptions</b>", styles["Heading3"]))
        for assumption in result.assumptions:
            story.append(Paragraph(f"- {assumption}", styles["Normal"]))

    return story


def _legacy_section(data: dict[str, Any], styles: dict[str, ParagraphStyle]):
    story = []
    story.append(Paragraph("<b>Legacy Summary</b>", styles["Heading2"]))

    fence_specs = data.get("fence_specs", {})
    wind_cond = data.get("wind_conditions", {})
    results_data = [
        ["Design Pressure", f"{data.get('design_pressure', 'N/A')} psf"],
        ["Total Load", f"{data.get('total_load', 'N/A')} lbs"],
    ]

    fence_data = [
        ["Height", f"{fence_specs.get('height', 'N/A')} ft"],
        ["Width", f"{fence_specs.get('width', 'N/A')} ft"],
        ["Material", fence_specs.get("material", "N/A")],
        ["Location", fence_specs.get("location", "N/A")],
    ]

    wind_data = [
        ["Wind Speed", f"{wind_cond.get('wind_speed', 'N/A')} mph"],
        ["Exposure Category", wind_cond.get("exposure_category", "N/A")],
        ["Importance Factor", wind_cond.get("importance_factor", "N/A")],
    ]

    for title, rows in (
        ("Fence Specifications", fence_data),
        ("Wind Conditions", wind_data),
        ("Calculation Results", results_data),
    ):
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
        table = Table(rows)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.1 * inch))

    if data.get("calculation_notes"):
        story.append(Paragraph(f"<b>Notes:</b> {data['calculation_notes']}", styles["Normal"]))

    return story


__all__ = ["draw_pdf", "generate_pdf_report"]
