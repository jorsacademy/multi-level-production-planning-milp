from __future__ import annotations

import pandas as pd


def require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing required columns: {sorted(missing)}")


def ensure_nonnegative(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    for column in columns:
        if (frame[column] < 0).any():
            raise ValueError(f"{name}.{column} cannot contain negative values.")


def normalize_periods(frame: pd.DataFrame, column: str = "period") -> pd.DataFrame:
    result = frame.copy()
    result[column] = result[column].astype(int)
    if (result[column] < 1).any():
        raise ValueError("Planning periods must start at 1 or greater.")
    return result
