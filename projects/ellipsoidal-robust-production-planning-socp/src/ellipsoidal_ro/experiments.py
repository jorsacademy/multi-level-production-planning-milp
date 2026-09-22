from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .data import ProductionInstance
from .model import (
    PlanningSolution,
    solve_box_robust,
    solve_deterministic,
    solve_ellipsoidal_robust,
)


@dataclass(frozen=True)
class MethodComparison:
    deterministic: PlanningSolution
    ellipsoidal: PlanningSolution
    box: PlanningSolution

    @property
    def ellipsoidal_price_of_robustness(self) -> float:
        return float(self.deterministic.objective - self.ellipsoidal.objective)

    @property
    def box_price_of_robustness(self) -> float:
        return float(self.deterministic.objective - self.box.objective)

    @property
    def box_conservatism_gap(self) -> float:
        return float(self.ellipsoidal.objective - self.box.objective)


@dataclass(frozen=True)
class RadiusRecord:
    scale: float
    deterministic_objective: float
    ellipsoidal_objective: float
    box_objective: float
    ellipsoidal_output: float
    box_output: float
    ellipsoidal_min_slack: float
    box_min_slack: float


def compare_methods(instance: ProductionInstance) -> MethodComparison:
    return MethodComparison(
        deterministic=solve_deterministic(instance),
        ellipsoidal=solve_ellipsoidal_robust(instance),
        box=solve_box_robust(instance),
    )


def scale_uncertainty_radius(
    instance: ProductionInstance,
    scale: float,
) -> ProductionInstance:
    if scale < 0:
        raise ValueError("scale must be nonnegative")
    return replace(
        instance,
        uncertainty_radius=instance.uncertainty_radius * float(scale),
    )


def run_radius_sensitivity(
    instance: ProductionInstance,
    scales: list[float],
) -> list[RadiusRecord]:
    records: list[RadiusRecord] = []
    deterministic = solve_deterministic(instance)

    for scale in scales:
        scaled = scale_uncertainty_radius(instance, float(scale))
        ellipsoidal = solve_ellipsoidal_robust(scaled)
        box = solve_box_robust(scaled)
        records.append(
            RadiusRecord(
                scale=float(scale),
                deterministic_objective=float(deterministic.objective),
                ellipsoidal_objective=float(ellipsoidal.objective),
                box_objective=float(box.objective),
                ellipsoidal_output=float(np.sum(ellipsoidal.production)),
                box_output=float(np.sum(box.production)),
                ellipsoidal_min_slack=float(np.min(ellipsoidal.capacity_slack)),
                box_min_slack=float(np.min(box.capacity_slack)),
            )
        )
    return records


def format_radius_table(records: list[RadiusRecord]) -> str:
    header = (
        "scale   nominal_profit   ellipsoid_profit   box_profit   "
        "ellipsoid_output   box_output"
    )
    lines = [header]
    for record in records:
        lines.append(
            f"{record.scale:>5.2f}"
            f"{record.deterministic_objective:>17.3f}"
            f"{record.ellipsoidal_objective:>19.3f}"
            f"{record.box_objective:>13.3f}"
            f"{record.ellipsoidal_output:>19.3f}"
            f"{record.box_output:>13.3f}"
        )
    return "\n".join(lines)
