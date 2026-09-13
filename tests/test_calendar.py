import pandas as pd
import pytest

from production_planning import capacity_calendar_to_periods


def test_capacity_calendar_maps_dates_and_aggregates_shifts():
    calendar = pd.DataFrame(
        {
            "resource_id": ["M1", "M1", "M1", "LAB"],
            "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
            "capacity_hours": [8.0, 8.0, 0.0, 40.0],
        }
    )

    result = capacity_calendar_to_periods(calendar, "2026-01-01")

    m1_period_1 = result[(result.resource_id == "M1") & (result.period == 1)].iloc[0]
    m1_period_2 = result[(result.resource_id == "M1") & (result.period == 2)].iloc[0]
    lab_period_2 = result[(result.resource_id == "LAB") & (result.period == 2)].iloc[0]

    assert m1_period_1.capacity_hours == 16.0
    assert m1_period_2.capacity_hours == 0.0
    assert lab_period_2.capacity_hours == 40.0


def test_capacity_calendar_respects_horizon():
    calendar = pd.DataFrame(
        {
            "resource_id": ["M1", "M1", "M1"],
            "date": ["2026-01-01", "2026-01-02", "2026-01-05"],
            "capacity_hours": [8.0, 8.0, 8.0],
        }
    )

    result = capacity_calendar_to_periods(calendar, "2026-01-01", horizon_periods=2)
    assert result["period"].tolist() == [1, 2]


def test_capacity_calendar_rejects_invalid_inputs():
    before_start = pd.DataFrame(
        {
            "resource_id": ["M1"],
            "date": ["2025-12-31"],
            "capacity_hours": [8.0],
        }
    )
    with pytest.raises(ValueError, match="before planning_start"):
        capacity_calendar_to_periods(before_start, "2026-01-01")

    negative = pd.DataFrame(
        {
            "resource_id": ["M1"],
            "date": ["2026-01-01"],
            "capacity_hours": [-1.0],
        }
    )
    with pytest.raises(ValueError, match="cannot contain negative"):
        capacity_calendar_to_periods(negative, "2026-01-01")
