# Mathematical Model

## Sets

- `F`: production facilities
- `M`: demand markets
- `P`: product types

## Parameters

- `d[j,p]`: demand for product `p` at market `j`
- `cap[i,p]`: installed production capacity for product `p` at facility `i`
- `pc[i,p]`: unit production cost
- `tc[i,j,p]`: unit transportation cost
- `r[i,j,p]`: route-availability indicator
- `q[i,p]`: production-availability indicator
- `u[i]`: minimum utilization requirement for facility `i`
- `fc[i,p]`: fixed capacity-expansion cost
- `vc[i,p]`: variable capacity-expansion cost per added unit
- `s[i,p]`: maximum additional capacity
- `CRF`: capital-recovery factor

## Decision Variables

- `x[i,j,p] >= 0`, integer: units of product `p` produced at facility `i` and shipped to market `j`
- `y[i,p] in {0,1}`: whether capacity expansion is activated
- `a[i,p] >= 0`, integer: added production capacity

## Objective

Minimize

`sum((pc[i,p] + tc[i,j,p]) * x[i,j,p])`

plus

`CRF * sum(fc[i,p] * y[i,p] + vc[i,p] * a[i,p])`.

## Constraints

### Demand balance

For every market and product:

`sum_i x[i,j,p] = d[j,p]`

Exact equality is used because all costs are nonnegative and the model does not permit unnecessary overproduction.

### Product-specific capacity

For every facility and product:

`sum_j x[i,j,p] <= cap[i,p] + a[i,p]`

### Capacity-expansion activation

For every facility and product:

`a[i,p] <= s[i,p] * y[i,p]`

### Route and production availability

Variables `x[i,j,p]` receive an upper bound of zero whenever either the route or product-production configuration is unavailable.

### Minimum facility utilization

For every facility:

`sum_j sum_p x[i,j,p] >= u[i] * sum_p cap[i,p]`

The utilization denominator is the installed base capacity. This definition is explicit and intentionally does not increase the minimum utilization requirement when optional capacity is added.

## Capital-Recovery Factor

For interest rate `r` and investment horizon `N`:

`CRF = r(1+r)^N / ((1+r)^N - 1)`

For `r = 0`, the implementation uses `1/N`.

## Solver

The Python implementation uses `scipy.optimize.milp`, backed by HiGHS, and therefore handles integer and binary variables directly.
