# Windcalc - Wind Load Calculator for Fence Projects

A local-first wind load calculator designed for fence projects, providing accurate wind load calculations based on fence specifications and wind conditions.

## Features

- **Step-by-Step Wizard UI** - Guided form for field estimators (wind speed, exposure, geometry, post selection)
- **JSON REST API** - Programmatic access at `/api/calculate` for integrations
- **Dual Post Analysis** - Separate line and terminal post calculations with bending checks
- **Risk Classification** - GREEN / YELLOW / RED status based on spacing and structural limits
- **PDF Reports** - Professional calculation reports with status banners and assumptions
- **CLI Interface** - Command-line tool for quick calculations
- **Post Catalog** - Comprehensive catalog of pipe and C-shape posts with Cf factor tables
- **Local-First** - All calculations run locally, no cloud dependency

## Requirements

- Python 3.11+

## Installation

```bash
# Clone the repository
git clone https://github.com/Fence-Wizard/HFC_WLC.git
cd HFC_WLC

# Install with pip
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install
```

## Quick Start

### Wizard UI (recommended for field use)

```bash
# Start the server
uvicorn app.application:app --reload

# Or via CLI
windcalc serve
```

Open http://localhost:8000 in your browser. The wizard walks through:
1. **Step 1** – Wind speed, risk category, and exposure (with ASCE 7 map references)
2. **Step 2** – Fence height and post spacing
3. **Step 3** – Soil type and job name
4. **Review** – Results with risk classification, recalculation, and PDF download

### CLI

```bash
# Legacy calculation (outputs JSON)
windcalc calculate \
  --height 6 --width 100 --material wood \
  --location "Chicago, IL" --wind-speed 90 \
  --exposure B --output results.json

# Generate PDF report from JSON
windcalc report results.json --output report.pdf

# Start the full server (wizard + API)
windcalc serve
```

### Python API (recommended for new code)

```python
from windcalc import EstimateInput, calculate

inp = EstimateInput(
    wind_speed_mph=115,
    height_total_ft=8,
    post_spacing_ft=10,
    exposure="C",
)
out = calculate(inp)

print(f"Pressure: {out.shared.pressure_psf} psf")
print(f"Load per post: {out.shared.load_per_post_lb} lb")
print(f"Line post: {out.line.recommended.post_label}")
print(f"Terminal post: {out.terminal.recommended.post_label}")
print(f"Overall status: {out.overall_status}")
```

### JSON REST API

```bash
curl -X POST "http://localhost:8000/api/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "fence": {"height": 6.0, "width": 100.0, "material": "wood", "location": "Chicago, IL"},
    "wind": {"wind_speed": 90.0, "exposure_category": "B", "importance_factor": 1.0},
    "project_name": "Test Project"
  }'
```

#### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Wizard Step 1 (HTML) |
| `/step2` | POST | Wizard Step 2 |
| `/step3` | POST | Wizard Step 3 |
| `/review` | POST | Results & risk classification |
| `/download` | GET | PDF report download |
| `/health` | GET | Wizard health check |
| `/api/` | GET | API info |
| `/api/health` | GET | API health check |
| `/api/calculate` | POST | JSON wind load calculation |
| `/api/projects` | GET | List projects (placeholder) |

## Configuration

All settings are managed via environment variables (prefix `WINDCALC_`) or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `WINDCALC_HOST` | `0.0.0.0` | Server bind address |
| `WINDCALC_PORT` | `8000` | Server port |
| `WINDCALC_STRICT_FOOTING` | `false` | Raise errors instead of warnings for missing footing data |
| `WINDCALC_REPORT_DIR` | `~/Windload Reports` | Directory for generated PDF reports |
| `WINDCALC_CORS_ORIGINS` | `["http://localhost:3000", ...]` | Allowed CORS origins |

## Development

### Running Tests

```bash
# Run all tests with coverage
make test

# Or directly
pytest --cov=windcalc --cov-report=term-missing
```

### Linting and Formatting

```bash
# Lint
make lint

# Auto-format
make format

# Type check
make typecheck
```

### Docker

```bash
make docker-build
make docker-run
```

## Project Structure

```
HFC_WLC/
├── app/                       # Web application
│   ├── __init__.py
│   ├── application.py         # Unified FastAPI app (entry point)
│   ├── main.py                # Wizard UI routes (APIRouter)
│   ├── static/                # CSS, images
│   └── templates/             # Jinja2 HTML templates
├── windcalc/                  # Core calculation package
│   ├── __init__.py
│   ├── api.py                 # JSON REST API routes (APIRouter)
│   ├── cli.py                 # CLI interface (Click)
│   ├── engine.py              # Wind load calculation engine
│   ├── post_catalog.py        # Post types, Cf tables, spacing/bending checks
│   ├── report.py              # PDF report generation (ReportLab)
│   ├── risk.py                # Risk classification (GREEN/YELLOW/RED)
│   ├── schemas.py             # Pydantic data models
│   ├── settings.py            # Application settings (pydantic-settings)
│   └── tables.py              # Pandas data tables / export
├── tests/                     # Test suite
│   ├── golden_cases/          # JSON golden test cases
│   ├── test_api.py
│   ├── test_engine.py
│   ├── test_schemas.py
│   ├── test_tables.py
│   └── test_report.py
├── web-ui/                    # Future React frontend (placeholder)
├── .github/workflows/ci.yml   # GitHub Actions CI
├── .pre-commit-config.yaml    # Pre-commit hooks (ruff)
├── Dockerfile                 # Container image
├── Makefile                   # Developer commands
├── pyproject.toml             # Project & tool configuration
└── README.md
```

## Technologies

- **FastAPI** - Web framework (wizard UI + REST API)
- **Pydantic** / **pydantic-settings** - Data validation and configuration
- **Pandas** - Data export (CSV/Excel)
- **Click** - CLI
- **ReportLab** - PDF generation
- **Ruff** - Linting and formatting
- **Pytest** - Testing
- **Docker** - Containerization

## Disclaimer

This tool provides preliminary wind load estimates for fence projects based on simplified ASCE 7-inspired calculations. These estimates are intended to help field teams prioritize and plan — **they do not replace engineering calculations**. Always consult with a licensed structural engineer for final designs and ensure compliance with local building codes.
