# Multi-Product Demand Allocation MILP

A synthetic mixed-integer linear programming project for allocating multiple product demands across production facilities while minimizing production, transportation, and capacity-expansion costs.

The project is intentionally generic. It does not use proprietary data, company names, or real operational datasets.

## Problem Overview

The model decides:

- how many units of each product should be produced at each facility,
- how those units should be allocated to demand markets,
- whether additional production capacity should be activated,
- how much additional capacity should be added.

The objective is to minimize total annualized cost while satisfying demand, capacity, routing, production-availability, and minimum-utilization requirements.

## Optimization Model

The implementation uses `scipy.optimize.milp` with the HiGHS mixed-integer solver.

Decision variables:

- `x[i,j,p]`: integer units of product `p` produced at facility `i` and shipped to market `j`
- `y[i,p]`: binary capacity-expansion activation variable
- `a[i,p]`: integer added capacity for product `p` at facility `i`

The objective includes:

- unit production cost,
- unit transportation cost,
- fixed capacity-expansion cost,
- variable capacity-expansion cost,
- capital-recovery annualization of capacity-expansion expenditures.

Main constraints:

1. Exact demand satisfaction for every market-product pair.
2. Product-specific production-capacity limits.
3. Route and production-availability restrictions.
4. Facility-level minimum utilization requirements.
5. Capacity-expansion activation and upper-bound constraints.
6. Integrality and binary restrictions.

The detailed formulation is provided in `docs/mathematical_model.md`.

## Reliability Features

The repository includes several safeguards beyond the optimization model itself:

- deterministic synthetic data generation with a fixed random seed,
- structural and numerical input validation before optimization,
- checks for unreachable positive demand,
- unit and regression tests for the MILP formulation,
- an end-to-end solve in continuous integration,
- automated tests on Python 3.11 and Python 3.12,
- utilization-cost sensitivity analysis.

These checks are intended to catch malformed datasets, broken route definitions, invalid capacities, and regressions in the optimization logic before results are used.

## Repository Structure

```text
.
├── README.md
├── LICENSE.md
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
├── docs/
│   └── mathematical_model.md
├── outputs/
├── src/
│   ├── generate_data.py
│   ├── model.py
│   ├── reporting.py
│   ├── scenario_analysis.py
│   ├── solve.py
│   └── validation.py
└── tests/
    └── test_model.py
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

## Generate Synthetic Data

```bash
python src/generate_data.py
```

The generator creates a reproducible synthetic instance under `data/`.

## Solve the Optimization Model

```bash
python src/solve.py
```

Before solving, the input dataset is validated. The solver writes allocation, capacity-expansion, and facility-utilization reports to `outputs/` and prints a compact summary to the terminal.

## Run Tests

```bash
pytest -q
```

The regression suite includes a small analytically verifiable MILP instance that requires capacity expansion, a capital-recovery-factor test, and a validation test for unreachable demand.

## Run Utilization Sensitivity Analysis

```bash
python src/scenario_analysis.py
```

This solves the same planning instance under several facility-level minimum-utilization requirements and writes `outputs/utilization_scenarios.csv`. The result can be used to study the trade-off between operating-balance requirements and total allocation cost.

## Reproducibility

Synthetic data are generated using a fixed seed. Re-running `python src/generate_data.py` recreates the same instance unless the generator parameters are intentionally changed.

## Scope

This repository is designed for educational, academic, research, and portfolio use. It is not a representation of any specific company, commercial system, proprietary planning process, or operational dataset.

The numerical results produced by this repository are synthetic examples and should not be interpreted as business recommendations.

## License

This project is released under a custom non-commercial license. Commercial use is not permitted without prior written permission. See `LICENSE.md` for the full terms.
