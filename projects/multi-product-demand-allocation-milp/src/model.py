"""Build the mixed-integer linear programming model."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass
class ModelData:
    facilities: list[str]
    products: list[str]
    markets: list[str]
    min_utilization: Dict[str, float]
    demand: Dict[Tuple[str, str], int]
    capacity: Dict[Tuple[str, str], int]
    production_cost: Dict[Tuple[str, str], float]
    transportation_cost: Dict[Tuple[str, str, str], float]
    route_available: Dict[Tuple[str, str, str], int]
    production_available: Dict[Tuple[str, str], int]
    fixed_expansion_cost: Dict[Tuple[str, str], float]
    variable_expansion_cost: Dict[Tuple[str, str], float]
    max_additional_capacity: Dict[Tuple[str, str], int]


@dataclass
class VariableIndex:
    x: Dict[Tuple[str, str, str], int]
    y: Dict[Tuple[str, str], int]
    a: Dict[Tuple[str, str], int]
    n_variables: int


def _to_dict(df: pd.DataFrame, key_cols: list[str], value_col: str):
    return {
        tuple(row[col] for col in key_cols): row[value_col]
        for _, row in df.iterrows()
    }


def load_data(data_dir: Path) -> ModelData:
    facilities_df = pd.read_csv(data_dir / "facilities.csv")
    products_df = pd.read_csv(data_dir / "products.csv")
    markets_df = pd.read_csv(data_dir / "markets.csv")

    demand_df = pd.read_csv(data_dir / "demand.csv")
    capacity_df = pd.read_csv(data_dir / "production_capacity.csv")
    production_cost_df = pd.read_csv(data_dir / "production_cost.csv")
    transportation_cost_df = pd.read_csv(data_dir / "transportation_cost.csv")
    route_df = pd.read_csv(data_dir / "route_availability.csv")
    production_availability_df = pd.read_csv(data_dir / "production_availability.csv")
    expansion_df = pd.read_csv(data_dir / "capacity_expansion.csv")

    facilities = facilities_df["facility"].tolist()
    products = products_df["product"].tolist()
    markets = markets_df["market"].tolist()

    return ModelData(
        facilities=facilities,
        products=products,
        markets=markets,
        min_utilization=dict(zip(facilities_df["facility"], facilities_df["min_utilization"])),
        demand=_to_dict(demand_df, ["market", "product"], "demand"),
        capacity=_to_dict(capacity_df, ["facility", "product"], "capacity"),
        production_cost=_to_dict(production_cost_df, ["facility", "product"], "production_cost"),
        transportation_cost=_to_dict(
            transportation_cost_df,
            ["facility", "market", "product"],
            "transportation_cost",
        ),
        route_available=_to_dict(
            route_df,
            ["facility", "market", "product"],
            "available",
        ),
        production_available=_to_dict(
            production_availability_df,
            ["facility", "product"],
            "available",
        ),
        fixed_expansion_cost=_to_dict(
            expansion_df,
            ["facility", "product"],
            "fixed_cost",
        ),
        variable_expansion_cost=_to_dict(
            expansion_df,
            ["facility", "product"],
            "variable_cost",
        ),
        max_additional_capacity=_to_dict(
            expansion_df,
            ["facility", "product"],
            "max_additional_capacity",
        ),
    )


def build_variable_index(data: ModelData) -> VariableIndex:
    x = {}
    y = {}
    a = {}
    idx = 0

    for i in data.facilities:
        for j in data.markets:
            for p in data.products:
                x[(i, j, p)] = idx
                idx += 1

    for i in data.facilities:
        for p in data.products:
            y[(i, p)] = idx
            idx += 1

    for i in data.facilities:
        for p in data.products:
            a[(i, p)] = idx
            idx += 1

    return VariableIndex(x=x, y=y, a=a, n_variables=idx)


def capital_recovery_factor(interest_rate: float, horizon_years: int) -> float:
    if horizon_years <= 0:
        raise ValueError("Investment horizon must be positive.")
    if interest_rate == 0:
        return 1.0 / horizon_years
    factor = (1 + interest_rate) ** horizon_years
    return interest_rate * factor / (factor - 1)


def solve_model(
    data: ModelData,
    interest_rate: float = 0.08,
    horizon_years: int = 5,
):
    variables = build_variable_index(data)
    n = variables.n_variables
    crf = capital_recovery_factor(interest_rate, horizon_years)

    c = np.zeros(n, dtype=float)
    lower_bounds = np.zeros(n, dtype=float)
    upper_bounds = np.full(n, np.inf, dtype=float)
    integrality = np.ones(n, dtype=int)

    for key, idx in variables.x.items():
        i, j, p = key
        c[idx] = data.production_cost[(i, p)] + data.transportation_cost[(i, j, p)]
        if data.production_available[(i, p)] == 0 or data.route_available[(i, j, p)] == 0:
            upper_bounds[idx] = 0.0

    for key, idx in variables.y.items():
        i, p = key
        c[idx] = crf * data.fixed_expansion_cost[(i, p)]
        upper_bounds[idx] = 1.0 if data.production_available[(i, p)] == 1 else 0.0

    for key, idx in variables.a.items():
        i, p = key
        c[idx] = crf * data.variable_expansion_cost[(i, p)]
        upper_bounds[idx] = float(data.max_additional_capacity[(i, p)])
        if data.production_available[(i, p)] == 0:
            upper_bounds[idx] = 0.0

    rows = []
    lb = []
    ub = []

    # Demand must be satisfied exactly for every market-product pair.
    for j in data.markets:
        for p in data.products:
            coeff = {}
            for i in data.facilities:
                coeff[variables.x[(i, j, p)]] = 1.0
            rows.append(coeff)
            demand = float(data.demand[(j, p)])
            lb.append(demand)
            ub.append(demand)

    # Product-specific production cannot exceed base capacity plus added capacity.
    for i in data.facilities:
        for p in data.products:
            coeff = {variables.a[(i, p)]: -1.0}
            for j in data.markets:
                coeff[variables.x[(i, j, p)]] = 1.0
            rows.append(coeff)
            lb.append(-np.inf)
            ub.append(float(data.capacity[(i, p)]))

    # Added capacity can only be positive when the binary expansion decision is active.
    for i in data.facilities:
        for p in data.products:
            coeff = {
                variables.a[(i, p)]: 1.0,
                variables.y[(i, p)]: -float(data.max_additional_capacity[(i, p)]),
            }
            rows.append(coeff)
            lb.append(-np.inf)
            ub.append(0.0)

    # Minimum utilization is defined against installed base capacity.
    for i in data.facilities:
        total_base_capacity = sum(data.capacity[(i, p)] for p in data.products)
        required_output = data.min_utilization[i] * total_base_capacity
        coeff = {}
        for j in data.markets:
            for p in data.products:
                coeff[variables.x[(i, j, p)]] = 1.0
        rows.append(coeff)
        lb.append(float(required_output))
        ub.append(np.inf)

    matrix = lil_matrix((len(rows), n), dtype=float)
    for r, coeffs in enumerate(rows):
        for col, value in coeffs.items():
            matrix[r, col] = value

    constraints = LinearConstraint(matrix.tocsr(), np.asarray(lb), np.asarray(ub))
    bounds = Bounds(lower_bounds, upper_bounds)

    result = milp(
        c=c,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={"disp": False},
    )

    return result, variables, crf
