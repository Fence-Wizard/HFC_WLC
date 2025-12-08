"""PDF report generation module."""

from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf_report(data: dict[str, Any], output_path: str) -> None:
    """
    Generate a PDF report for wind load calculation results.

    This is a placeholder implementation that creates a basic PDF.
    Production version should include:
    - Detailed calculation breakdown
    - Code references
    - Diagrams and visualizations
    - Professional formatting

    Args:
        data: Dictionary containing calculation results
        output_path: Path to save the PDF report
    """
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph("Wind Load Calculation Report", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    # Project info
    if data.get("project_name"):
        project = Paragraph(f"<b>Project:</b> {data['project_name']}", styles["Normal"])
        story.append(project)
        story.append(Spacer(1, 12))

    # Fence specifications
    fence_title = Paragraph("<b>Fence Specifications</b>", styles["Heading2"])
    story.append(fence_title)

    fence_specs = data.get("fence_specs", {})
    fence_data = [
        ["Height", f"{fence_specs.get('height', 'N/A')} ft"],
        ["Width", f"{fence_specs.get('width', 'N/A')} ft"],
        ["Material", fence_specs.get("material", "N/A")],
        ["Location", fence_specs.get("location", "N/A")],
    ]

    fence_table = Table(fence_data)
    fence_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(fence_table)
    story.append(Spacer(1, 12))

    # Wind conditions
    wind_title = Paragraph("<b>Wind Conditions</b>", styles["Heading2"])
    story.append(wind_title)

    wind_cond = data.get("wind_conditions", {})
    wind_data = [
        ["Wind Speed", f"{wind_cond.get('wind_speed', 'N/A')} mph"],
        ["Exposure Category", wind_cond.get("exposure_category", "N/A")],
        ["Importance Factor", wind_cond.get("importance_factor", "N/A")],
    ]

    wind_table = Table(wind_data)
    wind_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(wind_table)
    story.append(Spacer(1, 12))

    # Results
    results_title = Paragraph("<b>Calculation Results</b>", styles["Heading2"])
    story.append(results_title)

    results_data = [
        ["Design Pressure", f"{data.get('design_pressure', 'N/A')} psf"],
        ["Total Load", f"{data.get('total_load', 'N/A')} lbs"],
    ]

    results_table = Table(results_data)
    results_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(results_table)
    story.append(Spacer(1, 12))

    # Notes
    if data.get("calculation_notes"):
        notes = Paragraph(f"<b>Notes:</b> {data['calculation_notes']}", styles["Normal"])
        story.append(notes)

    doc.build(story)
