from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import numpy as np
from scipy.optimize import linprog

from .data import ProductionInstance
from .uncertainty import (
    audit_box_solution,
    audit_ellipsoidal_solution,
    box_support,
    ellipsoidal_support,
)


@dataclass(frozen=True)
class PlanningSolution:
    method: str
    objective: float
    production: np.ndarray
    nominal_usage: np.ndarray
    robust_usage: np.ndarray
    capacity_slack: np.ndarray
    solver: str
    status: str


def _nominal_usage(
    instance: ProductionInstance,
    production: np.ndarray,
) -> np.ndarray:
    return instance.nominal_consumption @ np.asarray(production, dtype=float)


def solve_deterministic(instance: ProductionInstance) -> PlanningSolution:
    """Solve the nominal production-planning LP."""
    result = linprog(
        c=-instance.contribution_margin,
        A_ub=instance.nominal_consumption,
        b_ub=instance.resource_capacity,
        bounds=[
            (0.0, float(instance.demand_cap[j]))
            for j in range(instance.n_products)
        ],
        method="highs",
    )
    if not result.success or result.x is None or result.fun is None:
        raise RuntimeError(f"deterministic LP failed: {result.message}")

    production = np.asarray(result.x, dtype=float)
    usage = _nominal_usage(instance, production)
    return PlanningSolution(
        method="deterministic",
        objective=float(-result.fun),
        production=production,
        nominal_usage=usage,
        robust_usage=usage.copy(),
        capacity_slack=instance.resource_capacity - usage,
        solver="HiGHS",
        status=str(result.message),
    )


def solve_box_robust(instance: ProductionInstance) -> PlanningSolution:
    """
    Solve the exact factor-box robust counterpart as an LP.

    For ||u_r||_inf <= rho_r, the support function is
    rho_r ||P_r^T x||_1. Auxiliary variables linearize the absolute values.
    """
    n_products = instance.n_products
    n_resources = instance.n_resources
    n_factors = instance.n_factors

    t_start = n_products
    n_vars = n_products + n_resources * n_factors

    def t_idx(resource: int, factor: int) -> int:
        return t_start + resource * n_factors + factor

    objective = np.zeros(n_vars, dtype=float)
    objective[:n_products] = -instance.contribution_margin

    rows: list[np.ndarray] = []
    rhs: list[float] = []

    for resource in range(n_resources):
        row = np.zeros(n_vars, dtype=float)
        row[:n_products] = instance.nominal_consumption[resource]
        for factor in range(n_factors):
            row[t_idx(resource, factor)] = instance.uncertainty_radius[resource]
        rows.append(row)
        rhs.append(float(instance.resource_capacity[resource]))

        for factor in range(n_factors):
            loading = instance.factor_loadings[resource, :, factor]

            positive = np.zeros(n_vars, dtype=float)
            positive[:n_products] = loading
            positive[t_idx(resource, factor)] = -1.0
            rows.append(positive)
            rhs.append(0.0)

            negative = np.zeros(n_vars, dtype=float)
            negative[:n_products] = -loading
            negative[t_idx(resource, factor)] = -1.0
            rows.append(negative)
            rhs.append(0.0)

    bounds = [
        (0.0, float(instance.demand_cap[j]))
        for j in range(n_products)
    ]
    bounds.extend((0.0, None) for _ in range(n_resources * n_factors))

    result = linprog(
        c=objective,
        A_ub=np.asarray(rows),
        b_ub=np.asarray(rhs),
        bounds=bounds,
        method="highs",
    )
    if not result.success or result.x is None or result.fun is None:
        raise RuntimeError(f"box robust LP failed: {result.message}")

    production = np.asarray(result.x[:n_products], dtype=float)
    nominal = _nominal_usage(instance, production)
    robust = np.array(
        [
            nominal[r] + box_support(instance, r, production)
            for r in range(n_resources)
        ],
        dtype=float,
    )
    audit_box_solution(instance, production)
    return PlanningSolution(
        method="box_robust_lp",
        objective=float(-result.fun),
        production=production,
        nominal_usage=nominal,
        robust_usage=robust,
        capacity_slack=instance.resource_capacity - robust,
        solver="HiGHS",
        status=str(result.message),
    )


def solve_ellipsoidal_robust(instance: ProductionInstance) -> PlanningSolution:
    """
    Solve the ellipsoidal robust counterpart as an SOCP.

    If a_r = abar_r + P_r u_r and ||u_r||_2 <= rho_r, then

        max a_r^T x
        = abar_r^T x + rho_r ||P_r^T x||_2.

    The resulting resource constraints are second-order-cone constraints.
    """
    x = cp.Variable(instance.n_products, nonneg=True, name="production")
    constraints: list[cp.Constraint] = [x <= instance.demand_cap]

    for resource in range(instance.n_resources):
        nominal = instance.nominal_consumption[resource] @ x
        factor_exposure = instance.factor_loadings[resource].T @ x
        constraints.append(
            nominal
            + instance.uncertainty_radius[resource] * cp.norm(factor_exposure, 2)
            <= instance.resource_capacity[resource]
        )

    problem = cp.Problem(
        cp.Maximize(instance.contribution_margin @ x),
        constraints,
    )
    value = problem.solve(
        solver=cp.CLARABEL,
        tol_gap_abs=1e-9,
        tol_feas=1e-9,
        tol_gap_rel=1e-9,
    )
    if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        raise RuntimeError(f"ellipsoidal SOCP failed with status {problem.status}")
    if x.value is None or value is None:
        raise RuntimeError("ellipsoidal SOCP returned no primal solution")

    production = np.maximum(np.asarray(x.value, dtype=float), 0.0)
    nominal = _nominal_usage(instance, production)
    robust = np.array(
        [
            nominal[r] + ellipsoidal_support(instance, r, production)
            for r in range(instance.n_resources)
        ],
        dtype=float,
    )
    audit_ellipsoidal_solution(instance, production)

    violation = robust - instance.resource_capacity
    if np.max(violation) > 2e-6:
        raise RuntimeError(
            f"ellipsoidal SOCP returned a robustly infeasible solution: {violation}"
        )

    return PlanningSolution(
        method="ellipsoidal_robust_socp",
        objective=float(instance.contribution_margin @ production),
        production=production,
        nominal_usage=nominal,
        robust_usage=robust,
        capacity_slack=instance.resource_capacity - robust,
        solver="CLARABEL",
        status=str(problem.status),
    )
