import pandas as pd

from production_planning.optimizer import ProductionPlanner


def test_purchased_item_has_no_production_variable_and_plan_is_bounded():
    products = pd.DataFrame([
        {"product_id": "FG-A", "product_type": "manufactured"},
        {"product_id": "COMP-A", "product_type": "purchased"},
    ])
    bom = pd.DataFrame([
        {"parent_id": "FG-A", "component_id": "COMP-A", "quantity": 2.0},
    ])
    routing = pd.DataFrame([
        {"product_id": "FG-A", "resource_id": "RES-01", "runtime_minutes_per_unit": 60.0},
    ])
    inventory = pd.DataFrame([
        {"product_id": "FG-A", "on_hand": 0.0},
        {"product_id": "COMP-A", "on_hand": 20.0},
    ])
    demand = pd.DataFrame([
        {"product_id": "FG-A", "period": 1, "quantity": 5.0},
    ])
    capacity = pd.DataFrame([
        {"resource_id": "RES-01", "period": 1, "capacity_hours": 5.0},
    ])

    planner = ProductionPlanner(products, bom, routing, inventory, demand, capacity)
    plan = planner.solve(1)

    fg = plan.loc[plan["product_id"] == "FG-A"].iloc[0]
    comp = plan.loc[plan["product_id"] == "COMP-A"].iloc[0]

    assert planner.status == "Optimal"
    assert fg["production"] == 5.0
    assert fg["backlog"] == 0.0
    assert comp["production"] == 0.0
    assert comp["ending_inventory"] == 10.0


def test_capacity_limits_production_and_creates_backlog():
    products = pd.DataFrame([
        {"product_id": "FG-A", "product_type": "manufactured"},
    ])
    bom = pd.DataFrame(columns=["parent_id", "component_id", "quantity"])
    routing = pd.DataFrame([
        {"product_id": "FG-A", "resource_id": "RES-01", "runtime_minutes_per_unit": 60.0},
    ])
    inventory = pd.DataFrame([
        {"product_id": "FG-A", "on_hand": 0.0},
    ])
    demand = pd.DataFrame([
        {"product_id": "FG-A", "period": 1, "quantity": 8.0},
    ])
    capacity = pd.DataFrame([
        {"resource_id": "RES-01", "period": 1, "capacity_hours": 5.0},
    ])

    planner = ProductionPlanner(products, bom, routing, inventory, demand, capacity)
    plan = planner.solve(1)
    row = plan.iloc[0]

    assert row["production"] == 5.0
    assert row["fulfilled_demand"] == 5.0
    assert row["backlog"] == 3.0


def test_component_shortage_prevents_infeasible_parent_production():
    products = pd.DataFrame([
        {"product_id": "FG-A", "product_type": "manufactured"},
        {"product_id": "COMP-A", "product_type": "purchased"},
    ])
    bom = pd.DataFrame([
        {"parent_id": "FG-A", "component_id": "COMP-A", "quantity": 2.0},
    ])
    routing = pd.DataFrame([
        {"product_id": "FG-A", "resource_id": "RES-01", "runtime_minutes_per_unit": 30.0},
    ])
    inventory = pd.DataFrame([
        {"product_id": "FG-A", "on_hand": 0.0},
        {"product_id": "COMP-A", "on_hand": 4.0},
    ])
    demand = pd.DataFrame([
        {"product_id": "FG-A", "period": 1, "quantity": 5.0},
    ])
    capacity = pd.DataFrame([
        {"resource_id": "RES-01", "period": 1, "capacity_hours": 8.0},
    ])

    plan = ProductionPlanner(products, bom, routing, inventory, demand, capacity).solve(1)
    fg = plan.loc[plan["product_id"] == "FG-A"].iloc[0]

    assert fg["production"] == 2.0
    assert fg["backlog"] == 3.0


def test_lead_time_offsets_release_and_delays_completion():
    products = pd.DataFrame([
        {
            "product_id": "FG-A",
            "product_type": "manufactured",
            "lead_time_periods": 1,
            "min_lot_size": 0.0,
            "max_lot_size": 10.0,
            "setup_cost": 0.0,
        },
    ])
    bom = pd.DataFrame(columns=["parent_id", "component_id", "quantity"])
    routing = pd.DataFrame([
        {
            "product_id": "FG-A",
            "resource_id": "RES-01",
            "runtime_minutes_per_unit": 60.0,
            "setup_minutes": 0.0,
        },
    ])
    inventory = pd.DataFrame([{"product_id": "FG-A", "on_hand": 0.0}])
    demand = pd.DataFrame([{"product_id": "FG-A", "period": 1, "quantity": 4.0}])
    capacity = pd.DataFrame([
        {"resource_id": "RES-01", "period": 1, "capacity_hours": 4.0},
        {"resource_id": "RES-01", "period": 2, "capacity_hours": 0.0},
    ])

    plan = ProductionPlanner(products, bom, routing, inventory, demand, capacity).solve(2)
    p1 = plan[(plan["product_id"] == "FG-A") & (plan["period"] == 1)].iloc[0]
    p2 = plan[(plan["product_id"] == "FG-A") & (plan["period"] == 2)].iloc[0]

    assert p1["production"] == 0.0
    assert p1["backlog"] == 4.0
    assert p2["release_period"] == 1
    assert p2["production"] == 4.0
    assert p2["fulfilled_demand"] == 4.0
    assert p2["backlog"] == 0.0


def test_minimum_lot_size_and_setup_time_are_enforced():
    products = pd.DataFrame([
        {
            "product_id": "FG-A",
            "product_type": "manufactured",
            "lead_time_periods": 0,
            "min_lot_size": 5.0,
            "max_lot_size": 10.0,
            "setup_cost": 10.0,
        },
    ])
    bom = pd.DataFrame(columns=["parent_id", "component_id", "quantity"])
    routing = pd.DataFrame([
        {
            "product_id": "FG-A",
            "resource_id": "RES-01",
            "runtime_minutes_per_unit": 60.0,
            "setup_minutes": 60.0,
        },
    ])
    inventory = pd.DataFrame([{"product_id": "FG-A", "on_hand": 0.0}])
    demand = pd.DataFrame([{"product_id": "FG-A", "period": 1, "quantity": 4.0}])
    capacity = pd.DataFrame([{"resource_id": "RES-01", "period": 1, "capacity_hours": 6.0}])

    plan = ProductionPlanner(products, bom, routing, inventory, demand, capacity).solve(1)
    row = plan.iloc[0]

    assert row["setup"] == 1
    assert row["production"] == 5.0
    assert row["fulfilled_demand"] == 4.0
    assert row["ending_inventory"] == 1.0


def test_maximum_lot_size_limits_single_period_production():
    products = pd.DataFrame([
        {
            "product_id": "FG-A",
            "product_type": "manufactured",
            "lead_time_periods": 0,
            "min_lot_size": 1.0,
            "max_lot_size": 3.0,
            "setup_cost": 0.0,
        },
    ])
    bom = pd.DataFrame(columns=["parent_id", "component_id", "quantity"])
    routing = pd.DataFrame([
        {"product_id": "FG-A", "resource_id": "RES-01", "runtime_minutes_per_unit": 10.0},
    ])
    inventory = pd.DataFrame([{"product_id": "FG-A", "on_hand": 0.0}])
    demand = pd.DataFrame([{"product_id": "FG-A", "period": 1, "quantity": 5.0}])
    capacity = pd.DataFrame([{"resource_id": "RES-01", "period": 1, "capacity_hours": 8.0}])

    plan = ProductionPlanner(products, bom, routing, inventory, demand, capacity).solve(1)
    row = plan.iloc[0]

    assert row["production"] == 3.0
    assert row["backlog"] == 2.0
