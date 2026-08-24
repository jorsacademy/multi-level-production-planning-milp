from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .validation import require_columns


def peg_orders(orders: pd.DataFrame, inventory: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    """Peg orders to available inventory first, then planned production by due period."""
    require_columns(orders, {"order_id", "product_id", "quantity", "due_period"}, "orders")
    require_columns(inventory, {"product_id", "on_hand"}, "inventory")
    require_columns(plan, {"product_id", "period", "production"}, "plan")

    inventory_remaining = defaultdict(float)
    for row in inventory.itertuples(index=False):
        inventory_remaining[str(row.product_id)] += float(row.on_hand)

    production_remaining: dict[tuple[str, int], float] = defaultdict(float)
    for row in plan.itertuples(index=False):
        production_remaining[(str(row.product_id), int(row.period))] += float(row.production)

    rows: list[dict[str, object]] = []
    sorted_orders = orders.sort_values(["due_period", "order_id"], kind="stable")

    for order in sorted_orders.itertuples(index=False):
        product = str(order.product_id)
        remaining = float(order.quantity)
        due_period = int(order.due_period)

        from_inventory = min(remaining, inventory_remaining[product])
        if from_inventory > 0:
            rows.append(
                {
                    "order_id": str(order.order_id),
                    "product_id": product,
                    "source_type": "inventory",
                    "source_id": f"INV-{product}",
                    "source_period": 0,
                    "quantity": from_inventory,
                }
            )
            inventory_remaining[product] -= from_inventory
            remaining -= from_inventory

        if remaining > 0:
            candidate_periods = sorted(
                period
                for (candidate_product, period), quantity in production_remaining.items()
                if candidate_product == product and period <= due_period and quantity > 0
            )
            for period in candidate_periods:
                available = production_remaining[(product, period)]
                pegged = min(remaining, available)
                if pegged <= 0:
                    continue
                rows.append(
                    {
                        "order_id": str(order.order_id),
                        "product_id": product,
                        "source_type": "production",
                        "source_id": f"PROD-{product}-P{period}",
                        "source_period": period,
                        "quantity": pegged,
                    }
                )
                production_remaining[(product, period)] -= pegged
                remaining -= pegged
                if remaining <= 0:
                    break

        if remaining > 0:
            rows.append(
                {
                    "order_id": str(order.order_id),
                    "product_id": product,
                    "source_type": "unfulfilled",
                    "source_id": None,
                    "source_period": None,
                    "quantity": remaining,
                }
            )

    return pd.DataFrame(rows)
