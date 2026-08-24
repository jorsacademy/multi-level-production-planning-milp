from __future__ import annotations

import pandas as pd

from .validation import require_columns


def available_to_promise(
    product_id: str,
    requested_quantity: float,
    requested_period: int,
    inventory: pd.DataFrame,
    plan: pd.DataFrame,
    existing_orders: pd.DataFrame | None = None,
) -> dict[str, float | int | bool | None]:
    """Calculate deterministic cumulative ATP through and after a requested period."""
    if requested_quantity < 0:
        raise ValueError("Requested quantity cannot be negative.")
    if requested_period < 1:
        raise ValueError("Requested period must be at least 1.")

    require_columns(inventory, {"product_id", "on_hand"}, "inventory")
    require_columns(plan, {"product_id", "period", "production", "external_supply"}, "plan")

    on_hand_series = inventory.loc[inventory["product_id"].astype(str) == str(product_id), "on_hand"]
    on_hand = float(on_hand_series.sum()) if not on_hand_series.empty else 0.0

    receipts = (
        plan.loc[plan["product_id"].astype(str) == str(product_id)]
        .assign(receipt=lambda frame: frame["production"] + frame["external_supply"])
        .groupby("period")["receipt"]
        .sum()
        .to_dict()
    )

    committed: dict[int, float] = {}
    if existing_orders is not None and not existing_orders.empty:
        require_columns(existing_orders, {"product_id", "due_period", "quantity"}, "existing_orders")
        committed = (
            existing_orders.loc[existing_orders["product_id"].astype(str) == str(product_id)]
            .groupby("due_period")["quantity"]
            .sum()
            .to_dict()
        )

    max_period = max([requested_period, *receipts.keys(), *committed.keys()])
    cumulative_available = on_hand

    for period in range(1, max_period + 1):
        cumulative_available += float(receipts.get(period, 0.0))
        cumulative_available -= float(committed.get(period, 0.0))
        if period >= requested_period and cumulative_available >= requested_quantity:
            return {
                "confirmed": True,
                "promise_period": period,
                "promise_quantity": float(requested_quantity),
                "available_after_commitment": cumulative_available - requested_quantity,
            }

    return {
        "confirmed": False,
        "promise_period": None,
        "promise_quantity": max(0.0, cumulative_available),
        "available_after_commitment": max(0.0, cumulative_available),
    }
