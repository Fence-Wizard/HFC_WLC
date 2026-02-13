"""Unified FastAPI application.

Single entry point that mounts both the wizard UI and the JSON API.
Run with: uvicorn app.application:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.main import STATIC_DIR
from app.main import router as wizard_router
from windcalc.api import router as api_router
from windcalc.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="HFC Windload Calculator",
    description=(
        "Local-first wind load calculator for fence projects. "
        "Provides both a step-by-step wizard UI and a JSON REST API."
    ),
    version="0.1.0",
)

# CORS - configurable via WINDCALC_CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for the wizard UI
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount routers
app.include_router(api_router)     # /api/calculate, /api/health, /api/projects
app.include_router(wizard_router)  # /, /step2, /step3, /review, /download, /health


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
