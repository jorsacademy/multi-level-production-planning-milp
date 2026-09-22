from ellipsoidal_ro.data import demo_instance
from ellipsoidal_ro.experiments import run_radius_sensitivity


def test_radius_sensitivity_is_monotone_in_robust_objective() -> None:
    records = run_radius_sensitivity(
        demo_instance(),
        scales=[0.0, 0.5, 1.0, 1.5],
    )

    ellipsoidal = [record.ellipsoidal_objective for record in records]
    box = [record.box_objective for record in records]

    assert all(
        ellipsoidal[i + 1] <= ellipsoidal[i] + 1e-5
        for i in range(len(ellipsoidal) - 1)
    )
    assert all(
        box[i + 1] <= box[i] + 1e-7
        for i in range(len(box) - 1)
    )
    assert all(
        record.ellipsoidal_objective >= record.box_objective - 1e-5
        for record in records
    )
