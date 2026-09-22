"""Generate a reproducible synthetic demand-allocation instance.

All names and numerical values in this dataset are fictional and are created
solely for educational and research use.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

FACILITIES = ["Plant_North", "Plant_Central", "Plant_Coastal", "Plant_West"]
PRODUCTS = ["Model_A", "Model_B", "Model_C"]
MARKETS = ["Market_01", "Market_02", "Market_03", "Market_04", "Market_05", "Market_06"]


def generate() -> None:
    rng = np.random.default_rng(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    facilities = pd.DataFrame(
        {
            "facility": FACILITIES,
            "min_utilization": [0.45, 0.50, 0.42, 0.48],
        }
    )
    facilities.to_csv(DATA_DIR / "facilities.csv", index=False)

    pd.DataFrame({"product": PRODUCTS}).to_csv(DATA_DIR / "products.csv", index=False)
    pd.DataFrame({"market": MARKETS}).to_csv(DATA_DIR / "markets.csv", index=False)

    demand_rows = []
    for market in MARKETS:
        for product in PRODUCTS:
            demand_rows.append(
                {
                    "market": market,
                    "product": product,
                    "demand": int(rng.integers(70, 145)),
                }
            )
    pd.DataFrame(demand_rows).to_csv(DATA_DIR / "demand.csv", index=False)

    production_availability = {
        "Plant_North": {"Model_A": 1, "Model_B": 1, "Model_C": 0},
        "Plant_Central": {"Model_A": 1, "Model_B": 1, "Model_C": 1},
        "Plant_Coastal": {"Model_A": 0, "Model_B": 1, "Model_C": 1},
        "Plant_West": {"Model_A": 1, "Model_B": 0, "Model_C": 1},
    }

    capacity_rows = []
    prod_cost_rows = []
    prod_avail_rows = []
    expansion_rows = []
    for facility in FACILITIES:
        for product in PRODUCTS:
            available = production_availability[facility][product]
            base_capacity = int(rng.integers(180, 330)) if available else 0
            capacity_rows.append(
                {"facility": facility, "product": product, "capacity": base_capacity}
            )
            prod_cost_rows.append(
                {
                    "facility": facility,
                    "product": product,
                    "production_cost": float(rng.integers(40, 76)) if available else 0.0,
                }
            )
            prod_avail_rows.append(
                {"facility": facility, "product": product, "available": available}
            )
            expansion_rows.append(
                {
                    "facility": facility,
                    "product": product,
                    "fixed_cost": float(rng.integers(12000, 26000)) if available else 0.0,
                    "variable_cost": float(rng.integers(45, 95)) if available else 0.0,
                    "max_additional_capacity": int(rng.integers(80, 180)) if available else 0,
                }
            )

    pd.DataFrame(capacity_rows).to_csv(DATA_DIR / "production_capacity.csv", index=False)
    pd.DataFrame(prod_cost_rows).to_csv(DATA_DIR / "production_cost.csv", index=False)
    pd.DataFrame(prod_avail_rows).to_csv(DATA_DIR / "production_availability.csv", index=False)
    pd.DataFrame(expansion_rows).to_csv(DATA_DIR / "capacity_expansion.csv", index=False)

    transport_rows = []
    route_rows = []
    for facility in FACILITIES:
        for market in MARKETS:
            route_open = int(rng.random() > 0.18)
            for product in PRODUCTS:
                transport_rows.append(
                    {
                        "facility": facility,
                        "market": market,
                        "product": product,
                        "transportation_cost": float(rng.integers(8, 36)),
                    }
                )
                route_rows.append(
                    {
                        "facility": facility,
                        "market": market,
                        "product": product,
                        "available": route_open,
                    }
                )

    route_df = pd.DataFrame(route_rows)
    for market in MARKETS:
        for product in PRODUCTS:
            eligible = [
                f
                for f in FACILITIES
                if production_availability[f][product] == 1
            ]
            mask = (
                (route_df["market"] == market)
                & (route_df["product"] == product)
                & (route_df["facility"].isin(eligible))
            )
            if route_df.loc[mask, "available"].sum() == 0:
                first_idx = route_df.loc[mask].index[0]
                route_df.loc[first_idx, "available"] = 1

    pd.DataFrame(transport_rows).to_csv(DATA_DIR / "transportation_cost.csv", index=False)
    route_df.to_csv(DATA_DIR / "route_availability.csv", index=False)

    print(f"Synthetic dataset written to {DATA_DIR}")


if __name__ == "__main__":
    generate()
