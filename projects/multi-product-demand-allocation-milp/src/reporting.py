"""Convert solver output into tabular reports."""

from pathlib import Path

import pandas as pd

from model import ModelData, VariableIndex


def build_reports(data: ModelData, variables: VariableIndex, solution):
    allocation_rows = []
    for (facility, market, product), idx in variables.x.items():
        quantity = int(round(solution[idx]))
        if quantity > 0:
            allocation_rows.append(
                {
                    "facility": facility,
                    "market": market,
                    "product": product,
                    "quantity": quantity,
                }
            )

    expansion_rows = []
    for (facility, product), y_idx in variables.y.items():
        a_idx = variables.a[(facility, product)]
        expansion_rows.append(
            {
                "facility": facility,
                "product": product,
                "expansion_active": int(round(solution[y_idx])),
                "additional_capacity": int(round(solution[a_idx])),
            }
        )

    allocation_df = pd.DataFrame(allocation_rows)
    expansion_df = pd.DataFrame(expansion_rows)

    utilization_rows = []
    for facility in data.facilities:
        base_capacity = sum(data.capacity[(facility, p)] for p in data.products)
        produced = 0
        for market in data.markets:
            for product in data.products:
                produced += int(round(solution[variables.x[(facility, market, product)]]))
        utilization_rows.append(
            {
                "facility": facility,
                "base_capacity": base_capacity,
                "production": produced,
                "utilization": produced / base_capacity if base_capacity > 0 else 0.0,
                "minimum_required_utilization": data.min_utilization[facility],
            }
        )

    utilization_df = pd.DataFrame(utilization_rows)
    return allocation_df, expansion_df, utilization_df


def write_reports(output_dir: Path, allocation_df, expansion_df, utilization_df) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    allocation_df.to_csv(output_dir / "allocation.csv", index=False)
    expansion_df.to_csv(output_dir / "capacity_expansion.csv", index=False)
    utilization_df.to_csv(output_dir / "facility_utilization.csv", index=False)
