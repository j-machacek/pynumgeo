# Equation

```numgeo
*Equation [, <type>]
[*Penalty = <penalty multiplier>]
<equation data>
```

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: Multi-point constraints and penalty formulation](../theory/solution-method/multi-point-constraints.md)
</div>

The `*Equation` command defines homogeneous linear constraints between active degrees of freedom (DOFs). It is a step-level command. Depending on the selected type, the constrained DOFs may belong to paired nodes from two node sets or to the same node. All equation types are imposed by the penalty method.

Temperature (`tt`) constraints are not supported by `*Equation`. Prescribe temperature with [`*Boundary`](boundary-conditions/boundary.md#temperature).

A non-homogeneous constant term is not supported; all terms must be written on the left-hand side of the equation.

## Penalty multiplier

The optional line

```numgeo
*Penalty = <penalty multiplier>
```

must immediately follow the `*Equation` command. The prescribed value is the multiplier $\alpha_0$ used to scale the equation penalty with the local tangent stiffness. The default value is $\alpha_0=10^3$. The resulting penalty formulation and its stiffness scaling are described in the [Theory Manual](../theory/solution-method/multi-point-constraints.md#penalty-scaling-in-numgeo).

## General two-set equation

If no type is specified, the command constrains one DOF of a node set to equal one, possibly different, DOF of another node set:

```numgeo
*Equation
[*Penalty = <penalty multiplier>]
<node set 1>, <DOF 1>, <node set 2>, <DOF 2>
```

For every generated node pair, numgeo imposes

$$
d_1-d_2=0.
$$

Both node sets must contain at least one node. If their sizes differ, every node of the larger set is paired with the closest node of the smaller set; a node of the smaller set may therefore participate in more than one equation. If both sets have the same size, the second set is matched to the first set according to the shortest nodal distance.

## EqualDOF

The `EqualDOF` type constrains the same DOF in two node sets:

```numgeo
*Equation, EqualDOF
[*Penalty = <penalty multiplier>]
<node set 1>, <node set 2>, <DOF>
```

The two node sets must contain the same number of nodes. The nodes of the second set are reordered according to their shortest distance from the nodes of the first set, and numgeo imposes

$$
d^{(1)}-d^{(2)}=0
$$

for every generated pair.

## Linear equations with user-defined coefficients

The `linear` type applies the same homogeneous linear equation independently to every node in one node set:

```numgeo
*Equation, linear
[*Penalty = <penalty multiplier>]
<node set>, <DOF 1>, <factor 1>, <DOF 2>, <factor 2> [, ..., <DOF n>, <factor n>]
```

At least two DOF/factor pairs must be specified. For every node $m$ in the named set, numgeo generates

$$
\sum_{k=1}^{n} a_k d_k^{(m)}=0,
$$

where $a_k$ is `<factor k>` and $d_k^{(m)}$ is `<DOF k>` at node $m$. The definition does not pair different nodes with each other. All listed DOFs must be active at every node in the set.

The syntax uses coefficient pairs while retaining numgeo's set-based input: all terms refer to the same node, and the equation is replicated over the complete node set. All DOF/factor pairs must be given on the same input record.

For example,

```numgeo
*Equation, linear
*Penalty = 1.0e+04
Soil.left-free, u1, -3.8268343236508978e-01, u2, 9.2387953251128674e-01
```

imposes, at every node in `Soil.left-free`,

$$
-0.38268343236508978\,u_1
+0.92387953251128674\,u_2=0.
$$

This can be used, for example, to suppress displacement in a prescribed direction on an inclined boundary.

!!! note "Coefficient scaling"

    The factors are used exactly as entered and are not normalised internally. Multiplying every factor by a common value leaves the exact homogeneous equation unchanged, but changes the numerical penalty contribution by the square of that value. Coefficients of comparable magnitude, preferably of order unity, should therefore be used. An equation for which all factors are zero is rejected.

!!! note "Prescribed DOFs"

    A generated equation is inactive if all of its DOFs are already prescribed by boundary conditions. If no active equation remains for an `*Equation` definition, numgeo terminates the analysis with an input error.

## Available degrees of freedom

Degrees of freedom that can be constrained using the `*Equation` keyword are listed below. A DOF can only be used at nodes for which it is active.

| Degree of freedom | `numgeo` key |
|---|---|
| Solid displacement in the $x_1$, $x_2$ and $x_3$ directions | `u1`, `u2`, `u3` |
| Water displacement in the $x_1$, $x_2$ and $x_3$ directions | `w1`, `w2`, `w3` |
| Pore-water pressure | `pw` |
| Pore-air pressure | `pa` |
