"""CLI interface for windcalc."""

import json
from pathlib import Path

import click

from windcalc.engine import calculate_wind_load
from windcalc.report import generate_pdf_report
from windcalc.schemas import FenceSpecs, WindConditions, WindLoadRequest


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Windcalc - Local-first wind load calculator for fence projects."""
    pass


@main.command()
@click.option("--height", type=float, required=True, help="Fence height in feet")
@click.option("--width", type=float, required=True, help="Fence width in feet")
@click.option("--material", type=str, required=True, help="Fence material")
@click.option("--location", type=str, required=True, help="Installation location")
@click.option("--wind-speed", type=float, required=True, help="Design wind speed in mph")
@click.option("--exposure", type=str, default="B", help="Exposure category (A, B, C, D)")
@click.option("--importance", type=float, default=1.0, help="Importance factor")
@click.option("--project-name", type=str, help="Project name")
@click.option("--output", type=click.Path(), help="Output JSON file path")
def calculate(
    height: float,
    width: float,
    material: str,
    location: str,
    wind_speed: float,
    exposure: str,
    importance: float,
    project_name: str | None,
    output: str | None,
):
    """Calculate wind load for a fence project."""
    fence = FenceSpecs(height=height, width=width, material=material, location=location)
    wind = WindConditions(
        wind_speed=wind_speed,
        exposure_category=exposure,
        importance_factor=importance,
    )
    request = WindLoadRequest(fence=fence, wind=wind, project_name=project_name)

    result = calculate_wind_load(request)

    result_dict = result.model_dump()

    if output:
        output_path = Path(output)
        output_path.write_text(json.dumps(result_dict, indent=2))
        click.echo(f"Results saved to {output}")
    else:
        click.echo(json.dumps(result_dict, indent=2))


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", type=click.Path(), help="Output PDF file path")
def report(input_file: str, output: str | None):
    """Generate PDF report from calculation results."""
    input_path = Path(input_file)
    data = json.loads(input_path.read_text())

    output_path = output or "wind_load_report.pdf"

    generate_pdf_report(data, output_path)
    click.echo(f"Report generated: {output_path}")


@main.command()
def serve():
    """Start the FastAPI server (wizard UI + JSON API)."""
    import uvicorn

    click.echo("Starting Windcalc server on http://localhost:8000")
    click.echo("  Wizard UI:  http://localhost:8000/")
    click.echo("  JSON API:   http://localhost:8000/api/")
    uvicorn.run("app.application:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
