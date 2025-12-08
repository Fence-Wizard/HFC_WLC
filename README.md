# Windcalc - Wind Load Calculator for Fence Projects

A local-first wind load calculator designed for fence projects, providing accurate wind load calculations based on fence specifications and wind conditions.

## Features

- **FastAPI REST API** - Modern, async API for wind load calculations
- **CLI Interface** - Command-line tool for quick calculations
- **Pydantic Schemas** - Type-safe data validation
- **Pandas Integration** - Data analysis and export capabilities
- **PDF Reports** - Generate professional calculation reports
- **Local-First** - All calculations run locally, no cloud dependency

## Installation

```bash
# Clone the repository
git clone https://github.com/Fence-Wizard/HFC_WLC.git
cd HFC_WLC

# Install with pip
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
# Calculate wind load
windcalc calculate \
  --height 6 \
  --width 100 \
  --material wood \
  --location "Chicago, IL" \
  --wind-speed 90 \
  --exposure B \
  --project-name "My Fence Project" \
  --output results.json

# Generate PDF report
windcalc report results.json --output report.pdf

# Start API server
windcalc serve
```

### API

```bash
# Start the API server
uvicorn windcalc.api:app --reload

# Or use the CLI
windcalc serve
```

The API will be available at http://localhost:8000

#### API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /calculate` - Calculate wind load
- `GET /api/projects` - List projects (placeholder)

#### Example API Request

```bash
curl -X POST "http://localhost:8000/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "fence": {
      "height": 6.0,
      "width": 100.0,
      "material": "wood",
      "location": "Chicago, IL"
    },
    "wind": {
      "wind_speed": 90.0,
      "exposure_category": "B",
      "importance_factor": 1.0
    },
    "project_name": "Test Project"
  }'
```

### Python API

```python
from windcalc.schemas import FenceSpecs, WindConditions, WindLoadRequest
from windcalc.engine import calculate_wind_load

# Create fence specifications
fence = FenceSpecs(
    height=6.0,
    width=100.0,
    material="wood",
    location="Chicago, IL"
)

# Define wind conditions
wind = WindConditions(
    wind_speed=90.0,
    exposure_category="B",
    importance_factor=1.0
)

# Calculate wind load
request = WindLoadRequest(fence=fence, wind=wind)
result = calculate_wind_load(request)

print(f"Design Pressure: {result.design_pressure} psf")
print(f"Total Load: {result.total_load} lbs")
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=windcalc

# Run specific test file
pytest tests/test_engine.py
```

### Linting and Formatting

```bash
# Check code with ruff
ruff check windcalc tests

# Format code with black
black windcalc tests

# Type checking with mypy
mypy windcalc
```

## Project Structure

```
HFC_WLC/
├── windcalc/              # Main package
│   ├── __init__.py
│   ├── api.py             # FastAPI application
│   ├── cli.py             # CLI interface
│   ├── schemas.py         # Pydantic data models
│   ├── engine.py          # Wind load calculation engine
│   ├── report.py          # PDF report generation
│   └── tables.py          # Pandas data tables
├── tests/                 # Test suite
│   ├── golden_cases/      # JSON test cases
│   ├── test_api.py
│   ├── test_engine.py
│   ├── test_schemas.py
│   ├── test_tables.py
│   └── test_report.py
├── web-ui/                # Future React frontend
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI
├── pyproject.toml         # Project configuration
├── .gitignore
└── README.md
```

## Technologies

- **FastAPI** - Modern web framework for building APIs
- **Pydantic** - Data validation using Python type annotations
- **Pandas** - Data manipulation and analysis
- **Click** - Command-line interface creation
- **ReportLab** - PDF generation
- **Pytest** - Testing framework

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Disclaimer

This is a tool for preliminary calculations. Always consult with a licensed structural engineer for final designs and ensure compliance with local building codes.
