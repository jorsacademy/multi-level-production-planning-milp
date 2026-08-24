import pandas as pd

from production_planning.atp import available_to_promise
from production_planning.pegging import peg_orders


def test_atp_is_deterministic():
    inventory = pd.DataFrame([
        {"product_id": "FG-A", "on_hand": 4.0},
    ])
    plan = pd.DataFrame([
        {"product_id": "FG-A", "period": 1, "production": 3.0, "external_supply": 0.0},
        {"product_id": "FG-A", "period": 2, "production": 5.0, "external_supply": 0.0},
    ])
    orders = pd.DataFrame([
        {"order_id": "ORDER-001", "product_id": "FG-A", "quantity": 6.0, "due_period": 1},
    ])

    result = available_to_promise("FG-A", 4.0, 1, inventory, plan, orders)

    assert result["confirmed"] is True
    assert result["promise_period"] == 2
    assert result["promise_quantity"] == 4.0


def test_pegging_does_not_reuse_supply():
    orders = pd.DataFrame([
        {"order_id": "ORDER-001", "product_id": "FG-A", "quantity": 4.0, "due_period": 1},
        {"order_id": "ORDER-002", "product_id": "FG-A", "quantity": 4.0, "due_period": 1},
    ])
    inventory = pd.DataFrame([
        {"product_id": "FG-A", "on_hand": 3.0},
    ])
    plan = pd.DataFrame([
        {"product_id": "FG-A", "period": 1, "production": 3.0},
    ])

    result = peg_orders(orders, inventory, plan)
    supplied = result.loc[result["source_type"] != "unfulfilled", "quantity"].sum()
    unfulfilled = result.loc[result["source_type"] == "unfulfilled", "quantity"].sum()

    assert supplied == 6.0
    assert unfulfilled == 2.0
