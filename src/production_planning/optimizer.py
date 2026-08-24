from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

import pandas as pd
from pulp import LpBinary, LpMinimize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD, lpSum

from .bom import explode_bom, immediate_component_usage, validate_bom_acyclic
from .validation import ensure_nonnegative, normalize_periods, require_columns


@dataclass(frozen=True)
class ObjectiveWeights:
    backlog: float = 1000.0
    inventory: float = 1.0
    production: float = 0.1
    external_supply: float = 2.0
    setup: float = 1.0


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

        optional_product_columns = [
            column
            for column in ["lead_time_periods", "min_lot_size", "max_lot_size", "setup_cost"]
            if column in self.products.columns
        ]
        ensure_nonnegative(self.products, optional_product_columns, "products")

        optional_routing_columns = [column for column in ["setup_minutes"] if column in self.routing.columns]
        ensure_nonnegative(self.routing, ["runtime_minutes_per_unit", *optional_routing_columns], "routing")
        ensure_nonnegative(self.inventory, ["on_hand"], "inventory")
        ensure_nonnegative(self.demand, ["quantity"], "demand")
        ensure_nonnegative(self.capacity, ["capacity_hours"], "capacity")

        if "lead_time_periods" in self.products.columns:
            lead_times = self.products["lead_time_periods"].fillna(0)
            if (lead_times != lead_times.astype(int)).any():
                raise ValueError("lead_time_periods must contain whole numbers.")

        if "min_lot_size" in self.products.columns and "max_lot_size" in self.products.columns:
            minimum = self.products["min_lot_size"].fillna(0.0).astype(float)
            maximum = self.products["max_lot_size"].fillna(float("inf")).astype(float)
            invalid = maximum < minimum
            if invalid.any():
                products = self.products.loc[invalid, "product_id"].astype(str).tolist()
                raise ValueError(f"max_lot_size is smaller than min_lot_size for: {products}")

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

    def _gross_requirement_bounds(self, product_ids: list[str]) -> dict[str, float]:
        """Build safe production upper bounds from independent demand and the BOM."""
        bounds = {product_id: 0.0 for product_id in product_ids}
        total_demand = self.demand.groupby("product_id")["quantity"].sum().to_dict()

        for demanded_product, quantity in total_demand.items():
            demanded_product = str(demanded_product)
            quantity = float(quantity)
            bounds[demanded_product] = bounds.get(demanded_product, 0.0) + quantity
            for component, required in explode_bom(self.bom, demanded_product, quantity).items():
                bounds[component] = bounds.get(component, 0.0) + float(required)

        return bounds

    def solve(self, horizon_periods: Optional[int] = None) -> pd.DataFrame:
        product_table = self.products.copy()
        product_table["product_id"] = product_table["product_id"].astype(str)
        product_ids = product_table["product_id"].tolist()
        product_type = product_table.set_index("product_id")["product_type"].astype(str).to_dict()

        lead_time = {
            row.product_id: int(getattr(row, "lead_time_periods", 0) or 0)
            for row in product_table.itertuples(index=False)
        }
        min_lot = {
            row.product_id: float(getattr(row, "min_lot_size", 0.0) or 0.0)
            for row in product_table.itertuples(index=False)
        }
        max_lot = {
            row.product_id: float(getattr(row, "max_lot_size", float("inf")))
            if pd.notna(getattr(row, "max_lot_size", float("inf")))
            else float("inf")
            for row in product_table.itertuples(index=False)
        }
        setup_cost = {
            row.product_id: float(getattr(row, "setup_cost", 0.0) or 0.0)
            for row in product_table.itertuples(index=False)
        }

        resource_ids = sorted(set(self.capacity["resource_id"].astype(str)))
        max_period = max(int(self.demand["period"].max()), int(self.capacity["period"].max()))
        horizon = int(horizon_periods or max_period)
        periods = list(range(1, horizon + 1))

        demand_map = self.demand.groupby(["product_id", "period"])["quantity"].sum().to_dict()
        initial_inventory = self.inventory.set_index("product_id")["on_hand"].astype(float).to_dict()
        capacity_map = self.capacity.groupby(["resource_id", "period"])["capacity_hours"].sum().to_dict()
        runtime_map = self.routing.groupby(["product_id", "resource_id"])["runtime_minutes_per_unit"].sum().to_dict()
        setup_time_map = (
            self.routing.groupby(["product_id", "resource_id"])["setup_minutes"].sum().to_dict()
            if "setup_minutes" in self.routing.columns
            else {}
        )
        component_usage = immediate_component_usage(self.bom, product_ids)
        gross_requirement = self._gross_requirement_bounds(product_ids)

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
        setup = {
            (p, t): LpVariable(f"setup_{p}_{t}", cat=LpBinary)
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
        fulfilled = {
            (p, t): LpVariable(f"fulfilled_demand_{p}_{t}", lowBound=0)
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
            if product_type[p] == "purchased":
                continue

            gross_bound = float(gross_requirement.get(p, 0.0))
            production_bound = max(gross_bound, min_lot[p]) if gross_bound > 0.0 else 0.0
            for t in periods:
                release_period = t - lead_time[p]
                if release_period < 1 or production_bound <= 0.0:
                    model += production[(p, t)] == 0.0, f"pre_horizon_or_zero_requirement_{p}_{t}"
                    model += setup[(p, t)] == 0.0, f"no_setup_{p}_{t}"
                    continue

                upper_bound = production_bound
                if isfinite(max_lot[p]):
                    upper_bound = min(upper_bound, max_lot[p])

                model += production[(p, t)] <= upper_bound * setup[(p, t)], f"setup_link_upper_{p}_{t}"
                if min_lot[p] > 0.0:
                    model += production[(p, t)] >= min_lot[p] * setup[(p, t)], f"setup_link_lower_{p}_{t}"

        for p in product_ids:
            for t in periods:
                previous_backlog = 0.0 if t == 1 else backlog[(p, t - 1)]
                independent_demand = float(demand_map.get((p, t), 0.0))
                model += (
                    previous_backlog + independent_demand
                    == fulfilled[(p, t)] + backlog[(p, t)]
                ), f"demand_balance_{p}_{t}"

                previous_inventory = float(initial_inventory.get(p, 0.0)) if t == 1 else inventory[(p, t - 1)]
                produced = production.get((p, t), 0.0)
                supplied = supply.get((p, t), 0.0)

                dependent_demand_terms = []
                for (parent, component), usage in component_usage.items():
                    if component != p or product_type[parent] == "purchased":
                        continue
                    completion_period = t + lead_time[parent]
                    if completion_period in periods:
                        dependent_demand_terms.append(production[(parent, completion_period)] * usage)
                dependent_demand = lpSum(dependent_demand_terms)

                model += (
                    previous_inventory + produced + supplied
                    == inventory[(p, t)] + fulfilled[(p, t)] + dependent_demand
                ), f"material_balance_{p}_{t}"

        for resource in resource_ids:
            for t in periods:
                capacity_terms = []
                for p in product_ids:
                    if product_type[p] == "purchased":
                        continue
                    completion_period = t + lead_time[p]
                    if completion_period not in periods:
                        continue
                    runtime = float(runtime_map.get((p, resource), 0.0))
                    setup_minutes = float(setup_time_map.get((p, resource), 0.0))
                    capacity_terms.append(production[(p, completion_period)] * runtime / 60.0)
                    if setup_minutes > 0.0:
                        capacity_terms.append(setup[(p, completion_period)] * setup_minutes / 60.0)

                model += lpSum(capacity_terms) <= float(capacity_map.get((resource, t), 0.0)), f"capacity_{resource}_{t}"

        weights = self.objective_weights
        model += (
            weights.backlog * lpSum(backlog.values())
            + weights.inventory * lpSum(inventory.values())
            + weights.production * lpSum(production.values())
            + weights.external_supply * lpSum(supply.values())
            + weights.setup
            * lpSum(setup[(p, t)] * setup_cost[p] for (p, t) in setup)
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
                        "release_period": t - lead_time[p] if product_type[p] != "purchased" else t,
                        "production": float(production[(p, t)].value()) if (p, t) in production else 0.0,
                        "setup": int(round(setup[(p, t)].value() or 0.0)) if (p, t) in setup else 0,
                        "external_supply": float(supply[(p, t)].value()) if (p, t) in supply else 0.0,
                        "fulfilled_demand": float(fulfilled[(p, t)].value()),
                        "ending_inventory": float(inventory[(p, t)].value()),
                        "backlog": float(backlog[(p, t)].value()),
                        "independent_demand": float(demand_map.get((p, t), 0.0)),
                    }
                )

        self.plan = pd.DataFrame(rows)
        return self.plan
