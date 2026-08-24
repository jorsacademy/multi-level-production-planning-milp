from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Set

import pandas as pd

REQUIRED_BOM_COLUMNS = {"parent_id", "component_id", "quantity"}


def validate_bom_acyclic(bom: pd.DataFrame) -> None:
    """Validate required columns, positive quantities, and absence of BOM cycles."""
    missing = REQUIRED_BOM_COLUMNS.difference(bom.columns)
    if missing:
        raise ValueError(f"BOM is missing required columns: {sorted(missing)}")

    if (bom["quantity"] <= 0).any():
        raise ValueError("All BOM quantities must be positive.")

    graph: Dict[str, list[str]] = defaultdict(list)
    for row in bom.itertuples(index=False):
        graph[str(row.parent_id)].append(str(row.component_id))

    visited: Set[str] = set()
    active: Set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            raise ValueError(f"BOM cycle detected at product '{node}'.")
        if node in visited:
            return

        active.add(node)
        for child in graph.get(node, []):
            visit(child)
        active.remove(node)
        visited.add(node)

    for node in set(graph).union({child for children in graph.values() for child in children}):
        visit(node)


def explode_bom(bom: pd.DataFrame, product_id: str, quantity: float = 1.0) -> dict[str, float]:
    """Return flattened component requirements for a parent quantity."""
    validate_bom_acyclic(bom)
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    requirements: dict[str, float] = defaultdict(float)
    by_parent = {
        str(parent): group[["component_id", "quantity"]].copy()
        for parent, group in bom.groupby("parent_id", sort=False)
    }

    def recurse(parent: str, parent_quantity: float) -> None:
        children = by_parent.get(parent)
        if children is None:
            return

        for row in children.itertuples(index=False):
            component = str(row.component_id)
            required = float(row.quantity) * parent_quantity
            requirements[component] += required
            recurse(component, required)

    recurse(str(product_id), float(quantity))
    return dict(requirements)


def immediate_component_usage(bom: pd.DataFrame, products: Iterable[str]) -> dict[tuple[str, str], float]:
    """Map (parent, component) to immediate per-unit component usage."""
    validate_bom_acyclic(bom)
    product_set = {str(product) for product in products}
    usage: dict[tuple[str, str], float] = {}
    for row in bom.itertuples(index=False):
        parent = str(row.parent_id)
        component = str(row.component_id)
        if parent in product_set:
            usage[(parent, component)] = usage.get((parent, component), 0.0) + float(row.quantity)
    return usage
