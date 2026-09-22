# Mathematical formulation

## Nominal production planning

Let:

- (x_j) be production of product (j);
- (c_j > 0) be contribution margin;
- (ar a_{rj}) be nominal consumption of resource (r) per unit of product (j);
- (b_r) be resource capacity;
- (d_j) be the market upper bound.

The nominal LP is

[
max_x quad c^	op x
]

subject to

[
ar a_r^	op x le b_r qquad orall r,
]

[
0 le x_j le d_j qquad orall j.
]

## Factor uncertainty

For each resource row, uncertain coefficients are represented by

[
a_r(u_r)=ar a_r+P_r u_r,
]

where (P_rinmathbb R^{n	imes k}) maps a (k)-dimensional uncertainty factor into the (n) product coefficients.

For a fixed production vector (x),

[
a_r(u_r)^	op x
=
ar a_r^	op x+u_r^	op P_r^	op x.
]

Define the factor exposure

[
g_r(x)=P_r^	op x.
]

The robust counterpart is determined by the support function of the uncertainty set applied to (g_r(x)).

## Ellipsoidal uncertainty

Let

[
mathcal U_r^{(2)}
=
{u:|u|_2le ho_r}.
]

Then

[
sup_{uinmathcal U_r^{(2)}}u^	op g_r
=
ho_r|g_r|_2.
]

Therefore

[
ar a_r^	op x
+
ho_r|P_r^	op x|_2
le b_r.
]

This is a second-order-cone constraint.

The exact worst-case factor is, for (g_r
e0),

[
u_r^*
=
ho_rrac{g_r}{|g_r|_2}.
]

Substitution gives

[
(u_r^*)^	op g_r
=
ho_r|g_r|_2.
]

The implementation uses this factor as an independent post-solve feasibility oracle.

## Factor-box uncertainty

Let

[
mathcal U_r^{(infty)}
=
{u:|u|_inftyle ho_r}.
]

By dual norms,

[
sup_{uinmathcal U_r^{(infty)}}u^	op g_r
=
ho_r|g_r|_1.
]

Hence

[
ar a_r^	op x
+
ho_r|P_r^	op x|_1
le b_r.
]

Introduce nonnegative auxiliaries (t_{rk}) satisfying

[
t_{rk}ge (P_r^	op x)_k,
]

[
t_{rk}ge -(P_r^	op x)_k.
]

Then the resource row becomes

[
ar a_r^	op x
+
ho_rsum_k t_{rk}
le b_r,
]

which is linear.

The exact factor-box adversary is

[
u_r^*
=
ho_r,operatorname{sign}(g_r).
]

## Geometry and conservatism

For the same radius,

[
{u:|u|_2leho}
subseteq
{u:|u|_inftyleho}.
]

The factor box therefore contains every ellipsoidal realization and additional corner realizations.

For a profit-maximization problem this gives the feasible-set relation

[
X_{	ext{box}}
subseteq
X_{	ext{ellipsoid}}
subseteq
X_{	ext{deterministic}},
]

and consequently

[
z_{	ext{deterministic}}
ge
z_{	ext{ellipsoid}}
ge
z_{	ext{box}}.
]

The regression suite verifies this relationship on the declared benchmark.

## Radius sensitivity

The experiment scales every radius by a common multiplier (lambdage0):

[
ho_r(lambda)=lambdaho_r.
]

At (lambda=0), both robust models collapse to the nominal LP.

As (lambda) increases, each robust feasible set can only shrink. Therefore the optimal profit of each robust model is nonincreasing in (lambda). This monotonicity is tested computationally.

## Scope

The formulation treats uncertainty independently by resource row: each row has its own factor vector (u_r) and radius (ho_r). It does not impose one shared uncertainty realization across all resource constraints.

That modeling choice keeps the robust counterpart separable and transparent. A joint cross-resource ellipsoid would be a distinct model and should not be inferred from this implementation.
