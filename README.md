# Multi-Level Production Planning MILP

A compact reference implementation of a capacity-constrained, multi-level production planning model built with Python and PuLP.

The project models finished-goods demand, bill-of-material relationships, inventory, routing-based resource consumption, finite capacity, backlog, and deterministic available-to-promise calculations. The sample data is generic and does not represent any real company.

## Main features

- Multi-level bill-of-material explosion
- Inventory balance by product and period
- Routing-based capacity consumption
- Finite resource capacity by period
- Demand fulfillment and backlog tracking
- Deterministic available-to-promise calculation
- Order pegging against inventory and planned production
- Solver-status validation
- Cycle detection in the bill of materials
- Reproducible sample scenario and unit tests

## Model outline

For each product `p` and period `t`, the core material balance is:

```text
ending_inventory[p,t]
=
beginning_inventory[p,t]
+ production[p,t]
+ external_supply[p,t]
- independent_demand[p,t]
- dependent_component_demand[p,t]
```

Resource capacity is enforced through routing times:

```text
sum(production[p,t] * runtime_minutes[p,r] / 60 for p)
<= available_capacity_hours[r,t]
```

The objective minimizes a weighted combination of backlog, inventory holding, production, and external-supply costs.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the sample

```bash
python examples/basic_multilevel_plan.py
```

## Run tests

```bash
pytest -q
```

## Repository structure

```text
src/production_planning/
    optimizer.py
    bom.py
    atp.py
    pegging.py
    validation.py
examples/
tests/
```

## Scope

This repository is intended as an educational and research reference. It is not an ERP, MRP II, APS, or MES product. Real production environments usually require additional rules such as lead-time offsets, setup-state sequencing, calendars, yields, scrap, alternate components, purchase-order constraints, multi-site transfers, and execution feedback.

## License

Commercial use is prohibited. See `LICENSE` for the full terms.
