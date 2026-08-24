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
    assert row["backlog"] == 3.0
