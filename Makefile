.PHONY: install dev lint format typecheck test serve clean docker-build docker-run

# Install production dependencies
install:
	pip install -e .

# Install with dev dependencies
dev:
	pip install -e ".[dev]"
	pre-commit install

# Lint with ruff
lint:
	ruff check windcalc tests app

# Auto-format with ruff
format:
	ruff format windcalc tests app
	ruff check --fix windcalc tests app

# Type check with mypy
typecheck:
	mypy windcalc

# Run tests with coverage
test:
	pytest --cov=windcalc --cov-report=term-missing

# Run the development server with auto-reload
serve:
	uvicorn app.application:app --reload --host 0.0.0.0 --port 8000

# Remove build artifacts
clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Build Docker image
docker-build:
	docker build -t windcalc .

# Run Docker container
docker-run:
	docker run -p 8000:8000 windcalc
