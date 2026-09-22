"""Validation utilities for the synthetic optimization dataset."""

from __future__ import annotations

from math import isfinite


def validate_model_data(data) -> None:
    """Validate structural completeness and basic numerical consistency.

    The function intentionally accepts a ModelData-like object instead of
    importing ModelData. This keeps validation independent from the solver
    implementation and avoids circular imports.
    """
    if not data.facilities or not data.products or not data.markets:
        raise ValueError("Facilities, products, and markets must be non-empty.")

    if len(set(data.facilities)) != len(data.facilities):
        raise ValueError("Facility names must be unique.")
    if len(set(data.products)) != len(data.products):
        raise ValueError("Product names must be unique.")
    if len(set(data.markets)) != len(data.markets):
        raise ValueError("Market names must be unique.")

    for facility in data.facilities:
        if facility not in data.min_utilization:
            raise ValueError(f"Missing minimum utilization for {facility}.")
        utilization = float(data.min_utilization[facility])
        if not isfinite(utilization) or not 0.0 <= utilization <= 1.0:
            raise ValueError(
                f"Minimum utilization for {facility} must be between 0 and 1."
            )

    for market in data.markets:
        for product in data.products:
            key = (market, product)
            if key not in data.demand:
                raise ValueError(f"Missing demand value for {key}.")
            if data.demand[key] < 0:
                raise ValueError(f"Demand cannot be negative for {key}.")

    for facility in data.facilities:
        for product in data.products:
            key = (facility, product)
            required_maps = {
                "capacity": data.capacity,
                "production_cost": data.production_cost,
                "production_available": data.production_available,
                "fixed_expansion_cost": data.fixed_expansion_cost,
                "variable_expansion_cost": data.variable_expansion_cost,
                "max_additional_capacity": data.max_additional_capacity,
            }
            for name, mapping in required_maps.items():
                if key not in mapping:
                    raise ValueError(f"Missing {name} value for {key}.")

            if data.capacity[key] < 0:
                raise ValueError(f"Capacity cannot be negative for {key}.")
            if data.production_cost[key] < 0:
                raise ValueError(f"Production cost cannot be negative for {key}.")
            if data.fixed_expansion_cost[key] < 0:
                raise ValueError(f"Fixed expansion cost cannot be negative for {key}.")
            if data.variable_expansion_cost[key] < 0:
                raise ValueError(f"Variable expansion cost cannot be negative for {key}.")
            if data.max_additional_capacity[key] < 0:
                raise ValueError(f"Additional capacity bound cannot be negative for {key}.")
            if data.production_available[key] not in (0, 1):
                raise ValueError(f"Production availability must be binary for {key}.")

            if data.production_available[key] == 0:
                if data.capacity[key] != 0 or data.max_additional_capacity[key] != 0:
                    raise ValueError(
                        f"Unavailable production pair {key} must have zero base and additional capacity."
                    )

    for facility in data.facilities:
        for market in data.markets:
            for product in data.products:
                key = (facility, market, product)
                if key not in data.transportation_cost:
                    raise ValueError(f"Missing transportation cost for {key}.")
                if key not in data.route_available:
                    raise ValueError(f"Missing route availability for {key}.")
                if data.transportation_cost[key] < 0:
                    raise ValueError(f"Transportation cost cannot be negative for {key}.")
                if data.route_available[key] not in (0, 1):
                    raise ValueError(f"Route availability must be binary for {key}.")

    for market in data.markets:
        for product in data.products:
            if data.demand[(market, product)] == 0:
                continue
            feasible_origins = [
                facility
                for facility in data.facilities
                if data.production_available[(facility, product)] == 1
                and data.route_available[(facility, market, product)] == 1
                and (
                    data.capacity[(facility, product)]
                    + data.max_additional_capacity[(facility, product)]
                    > 0
                )
            ]
            if not feasible_origins:
                raise ValueError(
                    f"Positive demand for {(market, product)} has no eligible production route."
                )
