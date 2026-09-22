from dataclasses import replace

import numpy as np

from ellipsoidal_ro.data import demo_instance
from ellipsoidal_ro.model import (
    solve_box_robust,
    solve_deterministic,
    solve_ellipsoidal_robust,
)
from ellipsoidal_ro.uncertainty import (
    audit_box_solution,
    audit_ellipsoidal_solution,
)


def test_zero_radius_collapses_to_nominal_problem() -> None:
    instance = demo_instance()
    zero = replace(
        instance,
        uncertainty_radius=np.zeros(instance.n_resources),
    )

    deterministic = solve_deterministic(zero)
    ellipsoidal = solve_ellipsoidal_robust(zero)
    box = solve_box_robust(zero)

    np.testing.assert_allclose(
        ellipsoidal.objective,
        deterministic.objective,
        rtol=1e-7,
        atol=1e-7,
    )
    np.testing.assert_allclose(
        box.objective,
        deterministic.objective,
        rtol=1e-7,
        atol=1e-7,
    )


def test_uncertainty_geometry_objective_ordering() -> None:
    instance = demo_instance()
    deterministic = solve_deterministic(instance)
    ellipsoidal = solve_ellipsoidal_robust(instance)
    box = solve_box_robust(instance)

    assert deterministic.objective >= ellipsoidal.objective - 1e-6
    assert ellipsoidal.objective >= box.objective - 1e-6


def test_robust_solutions_pass_exact_adversarial_audits() -> None:
    instance = demo_instance()
    ellipsoidal = solve_ellipsoidal_robust(instance)
    box = solve_box_robust(instance)

    for audit in audit_ellipsoidal_solution(instance, ellipsoidal.production):
        assert audit.slack >= -2e-6

    for audit in audit_box_solution(instance, box.production):
        assert audit.slack >= -1e-7
