# Ellipsoidal Robust Production Planning with SOCP

A verification-first Operations Research benchmark for production planning under **uncertain resource-consumption coefficients**.

The repository compares three uncertainty geometries on the same production-planning instance:

```text
deterministic LP
      |
      +---- factor-box robust LP
      |
      +---- ellipsoidal robust SOCP
```

The central methodological point is that uncertainty-set geometry changes the robust counterpart.

## Production-planning model

Products are indexed by `j` and resources by `r`.

Decision:

```text
x_j >= 0    production quantity of product j
```

Nominal objective:

```text
maximize sum_j contribution_margin_j * x_j
```

with market bounds

```text
0 <= x_j <= demand_cap_j.
```

For resource `r`, the nominal consumption coefficients are `abar_r`.

## Factor representation of coefficient uncertainty

The uncertain resource-consumption row is

```text
a_r = abar_r + P_r u_r,
```

where `P_r` maps a lower-dimensional uncertainty-factor vector into coefficient perturbations.

This representation supports non-axis-aligned uncertainty through shared factor exposure across products.

## Ellipsoidal uncertainty

For

```text
||u_r||_2 <= rho_r,
```

robust feasibility requires

```text
(abar_r + P_r u_r)^T x <= capacity_r
for every ||u_r||_2 <= rho_r.
```

The support function of the Euclidean ball gives the exact counterpart

```text
abar_r^T x
+ rho_r ||P_r^T x||_2
<= capacity_r.
```

The norm term is second-order conic, so the production-planning problem is an **SOCP**. The repository solves it with CVXPY and CLARABEL.

## Factor-box uncertainty

For the larger factor box

```text
||u_r||_inf <= rho_r,
```

the support function is

```text
rho_r ||P_r^T x||_1.
```

Therefore the exact box counterpart is

```text
abar_r^T x
+ rho_r ||P_r^T x||_1
<= capacity_r.
```

Absolute-value auxiliaries convert this formulation to an LP, solved with SciPy/HiGHS.

Because the Euclidean ball of radius `rho` is contained in the infinity-norm box of the same radius,

```text
ellipsoidal feasible set contains box-robust feasible set.
```

Hence, for this common uncertainty map and a maximization objective,

```text
deterministic profit
>= ellipsoidal robust profit
>= box robust profit.
```

The regression suite checks this ordering rather than assuming it.

## Exact adversarial audit

For fixed production `x`, define

```text
g_r = P_r^T x.
```

The worst ellipsoidal factor is

```text
u_r* = rho_r g_r / ||g_r||_2
```

when `g_r != 0`.

It attains

```text
max ||u_r||_2 <= rho_r  u_r^T g_r
= rho_r ||g_r||_2.
```

For the factor box, the exact adversary is

```text
u_r* = rho_r sign(g_r),
```

which attains

```text
rho_r ||g_r||_1.
```

Every returned robust solution is independently audited using these closed-form adversarial factors.

## Validated benchmark

GitHub Actions validated the implementation on Python 3.10 and 3.12 using CVXPY with CLARABEL for the SOCP and SciPy/HiGHS for the LP baselines.

Default benchmark result:

| Method | Profit | Production vector |
|---|---:|---|
| Deterministic LP | 6218.368932 | [52.000, 48.000, 19.728, 0.000, 43.456] |
| Ellipsoidal robust SOCP | 5585.933689 | [52.000, 48.000, 22.900, 0.000, 24.719] |
| Factor-box robust LP | 5285.278601 | [52.000, 48.000, 31.019, 8.577, 0.000] |

For this fixture:

```text
ellipsoidal price of robustness = 632.435243
box conservatism gap            = 300.655088
```

The first two ellipsoidal resource rows are active at the optimum:

```text
resource 0: nominal 268.680780 -> robust 300.000000 / capacity 300
resource 1: nominal 219.950919 -> robust 245.000000 / capacity 245
resource 2: nominal 149.653526 -> robust 167.032642 / capacity 190
```

The exact adversarial-factor audit reproduces these robust usages.

### Radius sensitivity

Every base radius is multiplied by the same scale.

| Radius scale | Deterministic profit | Ellipsoidal profit | Box profit | Ellipsoidal output | Box output |
|---:|---:|---:|---:|---:|---:|
| 0.00 | 6218.369 | 6218.369 | 6218.369 | 163.184 | 163.184 |
| 0.50 | 6218.369 | 5885.248 | 5708.447 | 154.984 | 150.553 |
| 1.00 | 6218.369 | 5585.934 | 5285.279 | 147.619 | 139.596 |
| 1.50 | 6218.369 | 5315.007 | 4926.723 | 140.952 | 130.332 |
| 2.00 | 6218.369 | 5068.143 | 4618.968 | 134.876 | 122.397 |

On this benchmark the robust objectives are monotone in the uncertainty scale, and the box model remains more conservative than the ellipsoidal model. These are fixture-specific measurements, not universal performance claims.

For the full derivation of the robust counterparts, see `docs/model.md`.

## Repository structure

```text
src/ellipsoidal_ro/
  data.py          validated synthetic production instance
  uncertainty.py   support functions and exact worst-case factors
  model.py         deterministic LP, box robust LP, ellipsoidal SOCP
  experiments.py   method comparison and radius sensitivity
  __main__.py      CLI benchmark

docs/
  model.md         support-function and dual-norm derivation

tests/
  test_uncertainty.py
  test_models.py
  test_experiments.py
```

## Installation

```bash
python -m pip install -e ".[dev]"
```

Python 3.10+ is supported.

## Run

Default comparison:

```bash
python -m ellipsoidal_ro
```

Uncertainty-radius sensitivity:

```bash
python -m ellipsoidal_ro --sweep
```

## Verification contract

The test suite checks:

- exact ellipsoidal support-function equality;
- exact factor-box support-function equality;
- sampled ellipsoid-boundary realizations never exceed the analytical robust usage;
- SOCP robust feasibility under the exact adversarial factors;
- factor-box LP robust feasibility;
- equality of deterministic, ellipsoidal and box objectives at zero radius;
- deterministic >= ellipsoidal >= box objective ordering;
- nonincreasing robust objective as uncertainty radii increase.

## Methodological boundary

Implemented:

- uncertain linear resource-consumption coefficients;
- lower-dimensional factor uncertainty;
- ellipsoidal uncertainty sets;
- exact SOCP robust counterpart;
- factor-box uncertainty;
- exact LP robust counterpart;
- exact support-function adversarial audits;
- uncertainty-radius sensitivity analysis.

Not claimed:

- adjustable or multistage robust optimization;
- distributionally robust optimization;
- chance constraints;
- data-driven estimation of ellipsoid geometry;
- mixed-integer conic production planning;
- industrial-scale conic decomposition.

Those are separate research directions rather than labels applied to functionality that is not implemented.
