"""Tests for windcalc tables module."""

import pandas as pd
import pytest

from windcalc.tables import (
    create_results_dataframe,
    create_summary_table,
)


def test_create_results_dataframe_empty():
    """Test creating DataFrame from empty results."""
    df = create_results_dataframe([])
    assert df.empty


def test_create_results_dataframe_with_data():
    """Test creating DataFrame from results."""
    results = [
        {
            "design_pressure": 25.0,
            "total_load": 15000.0,
            "project_name": "Project 1",
        },
        {
            "design_pressure": 30.0,
            "total_load": 18000.0,
            "project_name": "Project 2",
        },
    ]

    df = create_results_dataframe(results)
    assert len(df) == 2
    assert "design_pressure" in df.columns
    assert "total_load" in df.columns
    assert df["design_pressure"].iloc[0] == 25.0


def test_create_summary_table_empty():
    """Test creating summary from empty DataFrame."""
    df = pd.DataFrame()
    summary = create_summary_table(df)
    assert summary.empty


def test_create_summary_table_with_data():
    """Test creating summary table."""
    results = [
        {"design_pressure": 25.0, "total_load": 15000.0},
        {"design_pressure": 30.0, "total_load": 18000.0},
    ]
    df = create_results_dataframe(results)
    summary = create_summary_table(df)

    assert len(summary) == 3
    assert "metric" in summary.columns
    assert "value" in summary.columns
