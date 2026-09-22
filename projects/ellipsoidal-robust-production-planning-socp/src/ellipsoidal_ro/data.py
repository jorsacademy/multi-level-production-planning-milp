from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProductionInstance:
    contribution_margin: np.ndarray
    demand_cap: np.ndarray
    nominal_consumption: np.ndarray
    factor_loadings: np.ndarray
    resource_capacity: np.ndarray
    uncertainty_radius: np.ndarray

    def __post_init__(self) -> None:
        fields = {
            "contribution_margin": self.contribution_margin,
            "demand_cap": self.demand_cap,
            "nominal_consumption": self.nominal_consumption,
            "factor_loadings": self.factor_loadings,
            "resource_capacity": self.resource_capacity,
            "uncertainty_radius": self.uncertainty_radius,
        }
        for name, value in fields.items():
            array = np.asarray(value, dtype=float)
            object.__setattr__(self, name, array)
            if not np.all(np.isfinite(array)):
                raise ValueError(f"{name} must contain finite values")

        if self.contribution_margin.ndim != 1:
            raise ValueError("contribution_margin must be one-dimensional")
        if self.demand_cap.shape != self.contribution_margin.shape:
            raise ValueError("demand_cap must match contribution_margin")
        if self.nominal_consumption.ndim != 2:
            raise ValueError("nominal_consumption must be two-dimensional")
        if self.nominal_consumption.shape[1] != self.contribution_margin.size:
            raise ValueError("nominal_consumption product dimension is inconsistent")
        if self.factor_loadings.ndim != 3:
            raise ValueError("factor_loadings must have shape (resources, products, factors)")

        n_resources, n_products = self.nominal_consumption.shape
        if self.factor_loadings.shape[:2] != (n_resources, n_products):
            raise ValueError("factor_loadings must align with resources and products")
        if self.resource_capacity.shape != (n_resources,):
            raise ValueError("resource_capacity must have one value per resource")
        if self.uncertainty_radius.shape != (n_resources,):
            raise ValueError("uncertainty_radius must have one value per resource")

        if np.any(self.contribution_margin <= 0):
            raise ValueError("contribution margins must be strictly positive")
        if np.any(self.demand_cap <= 0):
            raise ValueError("demand caps must be strictly positive")
        if np.any(self.nominal_consumption < 0):
            raise ValueError("nominal consumption coefficients must be nonnegative")
        if np.any(self.resource_capacity <= 0):
            raise ValueError("resource capacities must be strictly positive")
        if np.any(self.uncertainty_radius < 0):
            raise ValueError("uncertainty radii must be nonnegative")

    @property
    def n_products(self) -> int:
        return int(self.contribution_margin.size)

    @property
    def n_resources(self) -> int:
        return int(self.resource_capacity.size)

    @property
    def n_factors(self) -> int:
        return int(self.factor_loadings.shape[2])


def demo_instance() -> ProductionInstance:
    """Return the reproducible synthetic five-product, three-resource benchmark."""
    return ProductionInstance(
        contribution_margin=np.array([42.0, 36.0, 31.0, 48.0, 39.0]),
        demand_cap=np.array([52.0, 48.0, 44.0, 36.0, 46.0]),
        nominal_consumption=np.array(
            [
                [2.10, 1.70, 1.35, 2.55, 1.90],
                [1.20, 1.55, 1.85, 1.35, 1.65],
                [0.85, 1.10, 0.95, 1.45, 1.25],
            ],
            dtype=float,
        ),
        factor_loadings=np.array(
            [
                [
                    [0.18, 0.05, 0.00],
                    [0.10, 0.12, 0.02],
                    [0.05, 0.14, 0.05],
                    [0.22, 0.03, 0.07],
                    [0.12, 0.08, 0.10],
                ],
                [
                    [0.08, 0.09, 0.03],
                    [0.12, 0.05, 0.07],
                    [0.14, 0.11, 0.02],
                    [0.07, 0.13, 0.08],
                    [0.10, 0.06, 0.12],
                ],
                [
                    [0.05, 0.07, 0.04],
                    [0.08, 0.04, 0.06],
                    [0.06, 0.09, 0.05],
                    [0.11, 0.05, 0.08],
                    [0.09, 0.07, 0.07],
                ],
            ],
            dtype=float,
        ),
        resource_capacity=np.array([300.0, 245.0, 190.0]),
        uncertainty_radius=np.array([1.35, 1.20, 1.10]),
    )
