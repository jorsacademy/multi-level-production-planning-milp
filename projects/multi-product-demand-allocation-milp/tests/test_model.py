"""Regression tests for the core optimization model."""

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model import ModelData, capital_recovery_factor, solve_model
from validation import validate_model_data


def tiny_instance() -> ModelData:
    return ModelData(
        facilities=["Plant_One"],
        products=["Model_A"],
        markets=["Market_01"],
        min_utilization={"Plant_One": 0.0},
        demand={("Market_01", "Model_A"): 12},
        capacity={("Plant_One", "Model_A"): 10},
        production_cost={("Plant_One", "Model_A"): 5.0},
        transportation_cost={("Plant_One", "Market_01", "Model_A"): 2.0},
        route_available={("Plant_One", "Market_01", "Model_A"): 1},
        production_available={("Plant_One", "Model_A"): 1},
        fixed_expansion_cost={("Plant_One", "Model_A"): 100.0},
        variable_expansion_cost={("Plant_One", "Model_A"): 3.0},
        max_additional_capacity={("Plant_One", "Model_A"): 5},
    )


def test_capital_recovery_factor_zero_interest():
    assert capital_recovery_factor(0.0, 5) == 0.2


def test_tiny_instance_requires_capacity_expansion():
    data = tiny_instance()
    validate_model_data(data)

    result, variables, crf = solve_model(data, interest_rate=0.0, horizon_years=1)

    assert result.success
    assert int(round(result.x[variables.x[("Plant_One", "Market_01", "Model_A")]])) == 12
    assert int(round(result.x[variables.y[("Plant_One", "Model_A")]])) == 1
    assert int(round(result.x[variables.a[("Plant_One", "Model_A")]])) == 2

    expected = 12 * (5.0 + 2.0) + crf * (100.0 + 2 * 3.0)
    assert np.isclose(result.fun, expected)


def test_validation_rejects_unreachable_positive_demand():
    data = tiny_instance()
    data.route_available[("Plant_One", "Market_01", "Model_A")] = 0

    try:
        validate_model_data(data)
    except ValueError as exc:
        assert "no eligible production route" in str(exc)
    else:
        raise AssertionError("Validation should reject unreachable positive demand.")
