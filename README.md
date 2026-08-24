# Multi-Level Production Planning MILP

A compact reference implementation of a capacity-constrained, multi-level production planning model built with Python and PuLP.

The project models finished-goods demand, bill-of-material relationships, inventory, routing-based resource consumption, finite capacity, backlog, production lead times, setup decisions, lot-size limits, and deterministic available-to-promise calculations. The sample data is generic and does not represent any real company.

## Main features

- Multi-level bill-of-material explosion
- Inventory balance by product and period
- Routing-based capacity consumption
- Finite resource capacity by period
- Production lead-time offsets
- Binary setup decisions
- Setup-time capacity consumption
- Product-level setup costs
- Minimum and maximum lot sizes
- Demand fulfillment and backlog tracking
- Material-feasibility enforcement for BOM components
- Deterministic available-to-promise calculation
- Order pegging against inventory and planned production
- Solver-status validation
- Cycle detection in the bill of materials
- Reproducible sample scenario and unit tests

## Model outline

The model separates customer-demand fulfillment from material consumption. Backlog is therefore associated with independent demand rather than being used as a substitute for missing BOM components.

For each product `p` and period `t`, independent demand follows:

```text
previous_backlog[p,t]
+ independent_demand[p,t]
=
fulfilled_demand[p,t]
+ backlog[p,t]
```

Material balance is enforced as:

```text
beginning_inventory[p,t]
+ production_completion[p,t]
+ external_supply[p,t]
=
ending_inventory[p,t]
+ fulfilled_demand[p,t]
+ dependent_component_demand[p,t]
```

This means a parent item cannot be produced by simply creating component backlog. Required components must be available when the parent production order is released.

## Lead-time offsets

For a manufactured product with lead time `L`, a quantity completed in period `t` is released in:

```text
release_period = t - L
```

Routing capacity and component consumption are assigned to the release period. If the release period would fall before period 1, that completion is not allowed inside the planning horizon.

Example:

```text
lead_time_periods = 1
completion_period = 3
release_period = 2
```

## Setup decisions

Each manufactured product-period pair has a binary setup variable:

```text
setup[p,t] in {0,1}
```

Production is linked to the setup decision:

```text
production[p,t] <= upper_bound[p,t] * setup[p,t]
```

If a minimum lot size is specified:

```text
production[p,t] >= min_lot_size[p] * setup[p,t]
```

A setup can also consume resource capacity through the optional routing field:

```text
setup_minutes
```

Resource capacity therefore includes both run time and setup time:

```text
sum(
    production[p,t] * runtime_minutes_per_unit[p,r] / 60
    + setup[p,t] * setup_minutes[p,r] / 60
    for p
)
<= available_capacity_hours[r,t]
```

## Lot-size limits

Manufactured products may define:

```text
min_lot_size
max_lot_size
```

The maximum lot size limits a single production completion quantity in a period. The minimum lot size forces an active setup to produce at least that quantity.

When demand is smaller than the minimum lot size, the model may intentionally create ending inventory if producing the minimum lot is less costly than leaving customer demand backlogged.

## Product input fields

Required product fields:

```text
product_id
product_type
```

Optional manufactured-product fields:

```text
lead_time_periods
min_lot_size
max_lot_size
setup_cost
```

`lead_time_periods` must be a nonnegative integer. Lot sizes and setup costs must be nonnegative. If both lot-size limits are supplied, `max_lot_size` cannot be smaller than `min_lot_size`.

## Routing input fields

Required routing fields:

```text
product_id
resource_id
runtime_minutes_per_unit
```

Optional routing field:

```text
setup_minutes
```

All routing times are expressed in minutes and are converted to hours inside the resource-capacity constraints.

## Objective

The objective minimizes a weighted combination of:

```text
backlog
ending inventory
production quantity
external supply
setup cost
```

The default backlog penalty is intentionally much larger than ordinary production and inventory weights so that feasible customer demand is normally served before low-cost inventory reductions are considered.

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

This repository is intended as an educational and research reference. It is not an ERP, MRP II, APS, or MES product. Real production environments can require additional rules such as sequence-dependent changeovers, overlapping operations, safety-stock policies, yields, scrap, alternate components, purchase-order lead times, supplier calendars, multi-site transfers, and execution feedback.

## License

Commercial use is prohibited. See `LICENSE` for the full terms.
