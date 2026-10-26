# Initial conditions, Type=temperature

```numgeo
*Initial conditions, Type=temperature [, default]
<node set name>, <initial temperature>
...
```

This keyword defines the initial absolute temperature at the nodes of [u-T solid elements](../element/elements-ut.md). It is required before the first step. Only the `default` option is available; it may be omitted. Specify the keyword once and list all node sets below it.

- `<node set name>`: name of a previously defined node set.
- `<initial temperature>`: finite, strictly positive absolute temperature (K in SI units), assigned to every node of the set.

Every independent temperature node must have an initial value. Use separate node sets for different temperatures; a set containing one node can be used to define a general nodal temperature field. If node sets overlap, the value of the last set applies.

For example:

```numgeo
*Initial conditions, Type=temperature
cold_nodes, 293.15
hot_nodes, 313.15
```

In mixed elements, the temperatures of displacement-only edge, face and interior nodes are interpolated from the corner values. These nodes may be omitted from the initial condition; values supplied for them are replaced by the interpolation. Nodes without a temperature degree of freedom cannot be assigned an initial temperature.

The initial nodal temperature initializes the heat equation. The reference temperature $T_{\rm ref}$ of [Thermal elasticity](../material/mechanical/thermal_elasticity.md) defines its stress-free thermal reference and does not replace the initial condition. Initial stress and its thermal history are described under [Initial stress and material state](../material/mechanical/thermal_elasticity.md#initial-stress-and-material-state). Mechanical equilibration in the first transient step contributes reversible thermoelastic heat.

Temperature prescribed during a step is defined with [`*Boundary`](../boundary-conditions/boundary.md#temperature). The tutorial [Uniform heating and restrained expansion](../../tutorial/thermal/uniform-heating.md) illustrates both definitions.
