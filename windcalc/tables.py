"""Pandas-based data tables for windcalc."""

from typing import Any

import pandas as pd


def create_results_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from wind load calculation results.

    Args:
        results: List of calculation result dictionaries

    Returns:
        DataFrame with calculation results
    """
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df


def create_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a summary table from results DataFrame.

    Args:
        df: DataFrame with calculation results

    Returns:
        Summary DataFrame with aggregated statistics
    """
    if df.empty:
        return pd.DataFrame()

    summary = pd.DataFrame(
        {
            "metric": ["count", "mean_design_pressure", "mean_total_load"],
            "value": [
                len(df),
                df["design_pressure"].mean() if "design_pressure" in df.columns else 0,
                df["total_load"].mean() if "total_load" in df.columns else 0,
            ],
        }
    )
    return summary


def export_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    Export DataFrame to CSV file.

    Args:
        df: DataFrame to export
        filepath: Path to save CSV file
    """
    df.to_csv(filepath, index=False)


def export_to_excel(df: pd.DataFrame, filepath: str) -> None:
    """
    Export DataFrame to Excel file.

    Args:
        df: DataFrame to export
        filepath: Path to save Excel file
    """
    df.to_excel(filepath, index=False, engine="openpyxl")
