import numpy as np

from ellipsoidal_ro.data import demo_instance
from ellipsoidal_ro.uncertainty import (
    box_support,
    ellipsoidal_support,
    realized_resource_usage,
    worst_box_factor,
    worst_ellipsoidal_factor,
)


def test_ellipsoidal_adversary_attains_support_function() -> None:
    instance = demo_instance()
    production = np.array([30.0, 24.0, 18.0, 20.0, 22.0])

    for resource in range(instance.n_resources):
        nominal = float(
            np.dot(instance.nominal_consumption[resource], production)
        )
        factor = worst_ellipsoidal_factor(instance, resource, production)
        realized = realized_resource_usage(
            instance,
            resource,
            production,
            factor,
        )
        expected = nominal + ellipsoidal_support(
            instance,
            resource,
            production,
        )
        np.testing.assert_allclose(realized, expected, rtol=1e-10, atol=1e-10)
        assert np.linalg.norm(factor, 2) <= instance.uncertainty_radius[resource] + 1e-10


def test_box_adversary_attains_support_function() -> None:
    instance = demo_instance()
    production = np.array([30.0, 24.0, 18.0, 20.0, 22.0])

    for resource in range(instance.n_resources):
        nominal = float(
            np.dot(instance.nominal_consumption[resource], production)
        )
        factor = worst_box_factor(instance, resource, production)
        realized = realized_resource_usage(
            instance,
            resource,
            production,
            factor,
        )
        expected = nominal + box_support(instance, resource, production)
        np.testing.assert_allclose(realized, expected, rtol=1e-10, atol=1e-10)
        assert np.max(np.abs(factor)) <= instance.uncertainty_radius[resource] + 1e-10


def test_random_ellipsoid_boundary_samples_do_not_exceed_support() -> None:
    instance = demo_instance()
    production = np.array([34.0, 22.0, 21.0, 18.0, 26.0])
    rng = np.random.default_rng(2026)

    for resource in range(instance.n_resources):
        nominal = float(
            np.dot(instance.nominal_consumption[resource], production)
        )
        exact = nominal + ellipsoidal_support(instance, resource, production)
        for _ in range(1000):
            direction = rng.normal(size=instance.n_factors)
            direction /= np.linalg.norm(direction)
            factor = instance.uncertainty_radius[resource] * direction
            realized = realized_resource_usage(
                instance,
                resource,
                production,
                factor,
            )
            assert realized <= exact + 1e-9
