from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pulp import LpMinimize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD, lpSum

from .bom import immediate_component_usage, validate_bom_acyclic
from .validation import ensure_nonnegative, normalize_periods, require_columns


@dataclass(frozen=True)
class ObjectiveWeights:
    backlog: float = 1000.0
    inventory: float = 1.0
    production: float = 0.1
    external_supply: float = 2.0


class ProductionPlanner:
    """Finite-capacity multi-level production planning model."""

    def __init__(
        self,
        products: pd.DataFrame,
        bom: pd.DataFrame,
        routing: pd.DataFrame,
        inventory: pd.DataFrame,
        demand: pd.DataFrame,
        capacity: pd.DataFrame,
        external_supply: Optional[pd.DataFrame] = None,
        objective_weights: ObjectiveWeights = ObjectiveWeights(),
    ) -> None:
        self.products = products.copy()
        self.bom = bom.copy()
        self.routing = routing.copy()
        self.inventory = inventory.copy()
        self.demand = normalize_periods(demand.copy())
        self.capacity = normalize_periods(capacity.copy())
        self.external_supply = normalize_periods(external_supply.copy()) if external_supply is not None else None
        self.objective_weights = objective_weights
        self.plan: Optional[pd.DataFrame] = None
        self.status: Optional[str] = None
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        require_columns(self.products, {"product_id", "product_type"}, "products")
        require_columns(self.routing, {"product_id", "resource_id", "runtime_minutes_per_unit"}, "routing")
        require_columns(self.inventory, {"product_id", "on_hand"}, "inventory")
        require_columns(self.demand, {"product_id", "period", "quantity"}, "demand")
        require_columns(self.capacity, {"resource_id", "period", "capacity_hours"}, "capacity")
        validate_bom_acyclic(self.bom)

        ensure_nonnegative(self.routing, ["runtime_minutes_per_unit"], "routing")
        ensure_nonnegative(self.inventory, ["on_hand"], "inventory")
        ensure_nonnegative(self.demand, ["quantity"], "demand")
        ensure_nonnegative(self.capacity, ["capacity_hours"], "capacity")

        if self.external_supply is not None:
            require_columns(self.external_supply, {"product_id", "period", "max_quantity"}, "external_supply")
            ensure_nonnegative(self.external_supply, ["max_quantity"], "external_supply")

        product_ids = set(self.products["product_id"].astype(str))
        referenced = set(self.bom["parent_id"].astype(str)).union(set(self.bom["component_id"].astype(str)))
        referenced.update(self.routing["product_id"].astype(str))
        referenced.update(self.inventory["product_id"].astype(str))
        referenced.update(self.demand["product_id"].astype(str))
        if self.external_supply is not None:
            referenced.update(self.external_supply["product_id"].astype(str))

        unknown = referenced.difference(product_ids)
        if unknown:
            raise ValueError(f"Unknown product IDs referenced by input data: {sorted(unknown)}")

    def solve(self, horizon_periods: Optional[int] = None) -> pd.DataFrame:
        product_ids = self.products["product_id"].astype(str).tolist()
        product_type = self.products.set_index("product_id")["product_type"].astype(str).to_dict()
        resource_ids = sorted(set(self.capacity["resource_id"].astype(str)))
        max_period = max(int(self.demand["period"].max()), int(self.capacity["period"].max()))
        horizon = int(horizon_periods or max_period)
        periods = list(range(1, horizon + 1))

        demand_map = self.demand.groupby(["product_id", "period"])["quantity"].sum().to_dict()
        initial_inventory = self.inventory.set_index("product_id")["on_hand"].astype(float).to_dict()
        capacity_map = self.capacity.groupby(["resource_id", "period"])["capacity_hours"].sum().to_dict()
        runtime_map = self.routing.groupby(["product_id", "resource_id"])["runtime_minutes_per_unit"].sum().to_dict()
        component_usage = immediate_component_usage(self.bom, product_ids)

        external_supply_max: dict[tuple[str, int], float] = {}
        if self.external_supply is not None:
            external_supply_max = self.external_supply.groupby(["product_id", "period"])["max_quantity"].sum().to_dict()

        model = LpProblem("multi_level_production_planning", LpMinimize)

        production = {
            (p, t): LpVariable(f"production_{p}_{t}", lowBound=0)
            for p in product_ids
            for t in periods
            if product_type[p] != "purchased"
        }
        inventory = {
            (p, t): LpVariable(f"inventory_{p}_{t}", lowBound=0)
            for p in product_ids
            for t in periods
        }
        backlog = {
            (p, t): LpVariable(f"backlog_{p}_{t}", lowBound=0)
            for p in product_ids
            for t in periods
        }
        supply = {
            (p, t): LpVariable(
                f"external_supply_{p}_{t}",
                lowBound=0,
                upBound=float(external_supply_max.get((p, t), 0.0)),
            )
            for p in product_ids
            for t in periods
            if (p, t) in external_supply_max
        }

        for p in product_ids:
            for t in periods:
                previous_inventory = float(initial_inventory.get(p, 0.0)) if t == 1 else inventory[(p, t - 1)]
                previous_backlog = 0.0 if t == 1 else backlog[(p, t - 1)]
                produced = production.get((p, t), 0.0)
                supplied = supply.get((p, t), 0.0)
                independent_demand = float(demand_map.get((p, t), 0.0))

                dependent_demand = lpSum(
                    production.get((parent, t), 0.0) * usage
                    for (parent, component), usage in component_usage.items()
                    if component == p
                )

                model += (
                    previous_inventory
                    + produced
                    + supplied
                    + backlog[(p, t)]
                    == inventory[(p, t)]
                    + independent_demand
                    + dependent_demand
                    + previous_backlog
                ), f"material_balance_{p}_{t}"

        for resource in resource_ids:
            for t in periods:
                model += (
                    lpSum(
                        production.get((p, t), 0.0)
                        * float(runtime_map.get((p, resource), 0.0))
                        / 60.0
                        for p in product_ids
                    )
                    <= float(capacity_map.get((resource, t), 0.0))
                ), f"capacity_{resource}_{t}"

        weights = self.objective_weights
        model += (
            weights.backlog * lpSum(backlog.values())
            + weights.inventory * lpSum(inventory.values())
            + weights.production * lpSum(production.values())
            + weights.external_supply * lpSum(supply.values())
        )

        model.solve(PULP_CBC_CMD(msg=False))
        self.status = LpStatus[model.status]
        if self.status != "Optimal":
            raise RuntimeError(f"Optimization did not return an optimal solution. Status: {self.status}")

        rows: list[dict[str, float | int | str]] = []
        for p in product_ids:
            for t in periods:
                rows.append(
                    {
                        "product_id": p,
                        "period": t,
                        "production": float(production[(p, t)].value()) if (p, t) in production else 0.0,
                        "external_supply": float(supply[(p, t)].value()) if (p, t) in supply else 0.0,
                        "ending_inventory": float(inventory[(p, t)].value()),
                        "backlog": float(backlog[(p, t)].value()),
                        "independent_demand": float(demand_map.get((p, t), 0.0)),
                    }
                )

        self.plan = pd.DataFrame(rows)
        return self.plan
