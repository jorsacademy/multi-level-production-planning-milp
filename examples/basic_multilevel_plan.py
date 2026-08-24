import pandas as pd

from production_planning import ProductionPlanner, available_to_promise, peg_orders


def build_sample_data():
    products = pd.DataFrame(
        [
            {"product_id": "FG-A", "product_type": "manufactured"},
            {"product_id": "SUB-A", "product_type": "manufactured"},
            {"product_id": "COMP-A", "product_type": "purchased"},
        ]
    )

    bom = pd.DataFrame(
        [
            {"parent_id": "FG-A", "component_id": "SUB-A", "quantity": 2.0},
            {"parent_id": "FG-A", "component_id": "COMP-A", "quantity": 1.0},
            {"parent_id": "SUB-A", "component_id": "COMP-A", "quantity": 3.0},
        ]
    )

    routing = pd.DataFrame(
        [
            {"product_id": "FG-A", "resource_id": "RES-01", "runtime_minutes_per_unit": 20.0},
            {"product_id": "SUB-A", "resource_id": "RES-02", "runtime_minutes_per_unit": 10.0},
        ]
    )

    inventory = pd.DataFrame(
        [
            {"product_id": "FG-A", "on_hand": 5.0},
            {"product_id": "SUB-A", "on_hand": 10.0},
            {"product_id": "COMP-A", "on_hand": 100.0},
        ]
    )

    demand = pd.DataFrame(
        [
            {"product_id": "FG-A", "period": 1, "quantity": 20.0},
            {"product_id": "FG-A", "period": 2, "quantity": 15.0},
            {"product_id": "FG-A", "period": 3, "quantity": 10.0},
        ]
    )

    capacity = pd.DataFrame(
        [
            {"resource_id": "RES-01", "period": 1, "capacity_hours": 8.0},
            {"resource_id": "RES-01", "period": 2, "capacity_hours": 8.0},
            {"resource_id": "RES-01", "period": 3, "capacity_hours": 8.0},
            {"resource_id": "RES-02", "period": 1, "capacity_hours": 8.0},
            {"resource_id": "RES-02", "period": 2, "capacity_hours": 8.0},
            {"resource_id": "RES-02", "period": 3, "capacity_hours": 8.0},
        ]
    )

    external_supply = pd.DataFrame(
        [
            {"product_id": "COMP-A", "period": 1, "max_quantity": 100.0},
            {"product_id": "COMP-A", "period": 2, "max_quantity": 100.0},
            {"product_id": "COMP-A", "period": 3, "max_quantity": 100.0},
        ]
    )

    orders = pd.DataFrame(
        [
            {"order_id": "ORDER-001", "product_id": "FG-A", "quantity": 12.0, "due_period": 1},
            {"order_id": "ORDER-002", "product_id": "FG-A", "quantity": 10.0, "due_period": 2},
        ]
    )

    return products, bom, routing, inventory, demand, capacity, external_supply, orders


def main():
    products, bom, routing, inventory, demand, capacity, external_supply, orders = build_sample_data()

    planner = ProductionPlanner(
        products=products,
        bom=bom,
        routing=routing,
        inventory=inventory,
        demand=demand,
        capacity=capacity,
        external_supply=external_supply,
    )

    plan = planner.solve(horizon_periods=3)
    print("Solver status:", planner.status)
    print("\nProduction plan")
    print(plan.to_string(index=False))

    atp = available_to_promise(
        product_id="FG-A",
        requested_quantity=8.0,
        requested_period=2,
        inventory=inventory,
        plan=plan,
        existing_orders=orders,
    )
    print("\nATP result")
    print(atp)

    pegging = peg_orders(orders=orders, inventory=inventory, plan=plan)
    print("\nPegging result")
    print(pegging.to_string(index=False))


if __name__ == "__main__":
    main()
