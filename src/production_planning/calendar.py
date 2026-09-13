from __future__ import annotations

import pandas as pd

from .validation import ensure_nonnegative, require_columns


def capacity_calendar_to_periods(
    calendar: pd.DataFrame,
    planning_start: str | pd.Timestamp,
    *,
    horizon_periods: int | None = None,
) -> pd.DataFrame:
    """Convert dated resource-capacity records into planner periods.

    Multiple rows for the same resource/date are summed, which allows a source
    calendar to represent separate shifts. Zero-capacity rows are retained so
    maintenance or shutdown days remain explicit in the planner input.

    Parameters
    ----------
    calendar:
        DataFrame with ``resource_id``, ``date``, and ``capacity_hours``.
    planning_start:
        Date corresponding to planning period 1.
    horizon_periods:
        Optional positive integer. Rows beyond this horizon are discarded.

    Returns
    -------
    pd.DataFrame
        Columns ``resource_id``, ``period``, and ``capacity_hours``.

    Notes
    -----
    The production planner interprets missing resource-period combinations as
    zero capacity. A source calendar should therefore contain every date on
    which a resource has available capacity.
    """
    require_columns(calendar, {"resource_id", "date", "capacity_hours"}, "capacity_calendar")

    result = calendar.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    if result["date"].isna().any():
        raise ValueError("capacity_calendar.date contains invalid dates.")

    ensure_nonnegative(result, ["capacity_hours"], "capacity_calendar")

    if result["resource_id"].isna().any() or (result["resource_id"].astype(str).str.len() == 0).any():
        raise ValueError("capacity_calendar.resource_id must contain non-empty values.")

    try:
        start = pd.Timestamp(planning_start).normalize()
    except (TypeError, ValueError) as exc:
        raise ValueError("planning_start must be a valid date.") from exc

    if pd.isna(start):
        raise ValueError("planning_start must be a valid date.")

    result["period"] = (result["date"].dt.normalize() - start).dt.days + 1
    if (result["period"] < 1).any():
        raise ValueError("capacity calendar contains dates before planning_start.")

    if horizon_periods is not None:
        if (
            not isinstance(horizon_periods, int)
            or isinstance(horizon_periods, bool)
            or horizon_periods < 1
        ):
            raise ValueError("horizon_periods must be a positive integer.")
        result = result.loc[result["period"] <= horizon_periods]

    result = (
        result.groupby(["resource_id", "period"], as_index=False)["capacity_hours"]
        .sum()
        .sort_values(["resource_id", "period"])
        .reset_index(drop=True)
    )
    result["period"] = result["period"].astype(int)
    return result[["resource_id", "period", "capacity_hours"]]
