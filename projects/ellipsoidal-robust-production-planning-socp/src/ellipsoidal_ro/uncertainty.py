from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import ProductionInstance


@dataclass(frozen=True)
class ResourceAudit:
    resource: int
    nominal_usage: float
    robust_usage: float
    capacity: float
    slack: float
    adversarial_factor: np.ndarray


def _factor_gradient(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
) -> np.ndarray:
    x = np.asarray(production, dtype=float)
    if x.shape != (instance.n_products,):
        raise ValueError("production has the wrong shape")
    return instance.factor_loadings[resource].T @ x


def ellipsoidal_support(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
) -> float:
    gradient = _factor_gradient(instance, resource, production)
    return float(instance.uncertainty_radius[resource] * np.linalg.norm(gradient, ord=2))


def box_support(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
) -> float:
    gradient = _factor_gradient(instance, resource, production)
    return float(instance.uncertainty_radius[resource] * np.linalg.norm(gradient, ord=1))


def worst_ellipsoidal_factor(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
) -> np.ndarray:
    gradient = _factor_gradient(instance, resource, production)
    norm = float(np.linalg.norm(gradient, ord=2))
    if norm <= 1e-14:
        return np.zeros(instance.n_factors, dtype=float)
    return instance.uncertainty_radius[resource] * gradient / norm


def worst_box_factor(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
) -> np.ndarray:
    gradient = _factor_gradient(instance, resource, production)
    return instance.uncertainty_radius[resource] * np.sign(gradient)


def realized_resource_usage(
    instance: ProductionInstance,
    resource: int,
    production: np.ndarray,
    factor: np.ndarray,
) -> float:
    x = np.asarray(production, dtype=float)
    u = np.asarray(factor, dtype=float)
    if x.shape != (instance.n_products,):
        raise ValueError("production has the wrong shape")
    if u.shape != (instance.n_factors,):
        raise ValueError("factor has the wrong shape")

    coefficients = (
        instance.nominal_consumption[resource]
        + instance.factor_loadings[resource] @ u
    )
    return float(np.dot(coefficients, x))


def audit_ellipsoidal_solution(
    instance: ProductionInstance,
    production: np.ndarray,
) -> list[ResourceAudit]:
    audits: list[ResourceAudit] = []
    for resource in range(instance.n_resources):
        nominal = float(
            np.dot(instance.nominal_consumption[resource], production)
        )
        factor = worst_ellipsoidal_factor(instance, resource, production)
        realized = realized_resource_usage(instance, resource, production, factor)
        robust = nominal + ellipsoidal_support(instance, resource, production)
        if abs(realized - robust) > 1e-8 * max(1.0, abs(robust)):
            raise RuntimeError("ellipsoidal support-function audit failed")
        capacity = float(instance.resource_capacity[resource])
        audits.append(
            ResourceAudit(
                resource=resource,
                nominal_usage=nominal,
                robust_usage=robust,
                capacity=capacity,
                slack=capacity - robust,
                adversarial_factor=factor,
            )
        )
    return audits


def audit_box_solution(
    instance: ProductionInstance,
    production: np.ndarray,
) -> list[ResourceAudit]:
    audits: list[ResourceAudit] = []
    for resource in range(instance.n_resources):
        nominal = float(
            np.dot(instance.nominal_consumption[resource], production)
        )
        factor = worst_box_factor(instance, resource, production)
        realized = realized_resource_usage(instance, resource, production, factor)
        robust = nominal + box_support(instance, resource, production)
        if abs(realized - robust) > 1e-8 * max(1.0, abs(robust)):
            raise RuntimeError("box support-function audit failed")
        capacity = float(instance.resource_capacity[resource])
        audits.append(
            ResourceAudit(
                resource=resource,
                nominal_usage=nominal,
                robust_usage=robust,
                capacity=capacity,
                slack=capacity - robust,
                adversarial_factor=factor,
            )
        )
    return audits
