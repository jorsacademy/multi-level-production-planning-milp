from __future__ import annotations

import argparse

import numpy as np

from .data import demo_instance
from .experiments import compare_methods, format_radius_table, run_radius_sensitivity
from .uncertainty import audit_box_solution, audit_ellipsoidal_solution


def _vector(values: np.ndarray) -> str:
    return "[" + ", ".join(f"{float(v):.3f}" for v in values) + "]"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ellipsoidal robust production planning with an SOCP counterpart."
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run the default uncertainty-radius sensitivity sweep.",
    )
    args = parser.parse_args()

    instance = demo_instance()
    comparison = compare_methods(instance)

    print("Ellipsoidal Robust Production Planning")
    print("======================================")
    print(
        f"Deterministic profit:       {comparison.deterministic.objective:12.6f}"
    )
    print(
        f"Ellipsoidal robust profit:  {comparison.ellipsoidal.objective:12.6f}"
    )
    print(
        f"Box robust profit:          {comparison.box.objective:12.6f}"
    )
    print(
        f"Ellipsoid price robustness: "
        f"{comparison.ellipsoidal_price_of_robustness:12.6f}"
    )
    print(
        f"Box conservatism gap:       {comparison.box_conservatism_gap:12.6f}"
    )
    print()
    print(
        f"Deterministic production: {_vector(comparison.deterministic.production)}"
    )
    print(
        f"Ellipsoidal production:   {_vector(comparison.ellipsoidal.production)}"
    )
    print(f"Box production:           {_vector(comparison.box.production)}")
    print()

    print("Ellipsoidal robust resource audit")
    for audit in audit_ellipsoidal_solution(instance, comparison.ellipsoidal.production):
        print(
            f"resource {audit.resource}: "
            f"nominal={audit.nominal_usage:.6f} "
            f"robust={audit.robust_usage:.6f} "
            f"capacity={audit.capacity:.6f} "
            f"slack={audit.slack:.6f}"
        )

    print()
    print("Box robust resource audit")
    for audit in audit_box_solution(instance, comparison.box.production):
        print(
            f"resource {audit.resource}: "
            f"nominal={audit.nominal_usage:.6f} "
            f"robust={audit.robust_usage:.6f} "
            f"capacity={audit.capacity:.6f} "
            f"slack={audit.slack:.6f}"
        )

    if args.sweep:
        print()
        print("Radius sensitivity")
        records = run_radius_sensitivity(
            instance,
            scales=[0.0, 0.5, 1.0, 1.5, 2.0],
        )
        print(format_radius_table(records))


if __name__ == "__main__":
    main()
