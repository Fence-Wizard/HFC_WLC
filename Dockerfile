FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps (reportlab needs some)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY windcalc/ windcalc/
COPY app/ app/

# Create report directory
RUN mkdir -p /app/reports

ENV WINDCALC_REPORT_DIR=/app/reports
ENV WINDCALC_HOST=0.0.0.0
ENV WINDCALC_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.application:app", "--host", "0.0.0.0", "--port", "8000"]
