"""Run a utilization-cost sensitivity analysis for the MILP model."""

from copy import deepcopy
from pathlib import Path

import pandas as pd

from generate_data import generate
from model import load_data, solve_model
from validation import validate_model_data

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"


def run_scenarios(utilization_levels=(0.0, 0.4, 0.5, 0.6, 0.7)) -> pd.DataFrame:
    if not (DATA_DIR / "facilities.csv").exists():
        generate()

    base_data = load_data(DATA_DIR)
    validate_model_data(base_data)

    rows = []
    for level in utilization_levels:
        scenario_data = deepcopy(base_data)
        scenario_data.min_utilization = {
            facility: float(level) for facility in scenario_data.facilities
        }

        result, variables, _ = solve_model(scenario_data)
        row = {
            "minimum_utilization": float(level),
            "success": bool(result.success),
            "status": int(result.status),
            "message": str(result.message),
            "objective_value": float(result.fun) if result.success else None,
        }

        if result.success:
            total_added_capacity = sum(
                int(round(result.x[idx])) for idx in variables.a.values()
            )
            activated_expansions = sum(
                int(round(result.x[idx])) for idx in variables.y.values()
            )
            row["total_added_capacity"] = total_added_capacity
            row["activated_expansions"] = activated_expansions
        else:
            row["total_added_capacity"] = None
            row["activated_expansions"] = None

        rows.append(row)

    results = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_DIR / "utilization_scenarios.csv", index=False)
    return results


def main() -> None:
    results = run_scenarios()
    print(results.to_string(index=False))
    print(f"Scenario results written to {OUTPUT_DIR / 'utilization_scenarios.csv'}")


if __name__ == "__main__":
    main()
