"""Application settings using pydantic-settings.

All configuration is centralized here. Values can be overridden
via environment variables prefixed with ``WINDCALC_``.

Example:
    export WINDCALC_STRICT_FOOTING=true
    export WINDCALC_REPORT_DIR="~/custom_reports"
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Windcalc application settings."""

    model_config = SettingsConfigDict(
        env_prefix="WINDCALC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Calculation behaviour
    strict_footing: bool = False

    # File paths
    report_dir: Path = Path.home() / "Windload Reports"

    # CORS origins (comma-separated in env var)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
