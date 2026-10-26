# Concentrated loads

```numgeo 
*Cload, <option>
<node set name>, <Load label>, <Magnitude>
```

This option defines a concentrated force, moment, heat supply or fluid volume source with a defined magnitude, which acts on every node of the
node set `<node set name>`. All sub-keywords are mandatory. `<option>` specifies
how the load should be applied. The load can either be applied:

-   instantaneously (without any temporal delay) using
    `<option> = instant`

-   linearly increasing with step time (0% of the prescribed magnitude
    are applied at the beginning of the step and 100% at the end of the
    step time) using `<option> = ramp`

-   using a user defined amplitude defined prior to the step definition
    using
    `<option> = Amplitude = <amplitude name>`

!!! note "Loads in a sequence of steps"

    The load acts only in the step in which it is defined; `ramp` starts from zero at the beginning of every step. A load which is to remain active has to be defined again in the following steps (usually with `instant`), see [Loads in a sequence of steps](./index.md#loads-in-a-sequence-of-steps).

`<Load label>` defines the type and the direction of the load:

| Load label | Load |
|---|---|
| `x`, `y`, `z` (or `1`, `2`, `3`) | force in the global $x$-, $y$- or $z$-direction |
| `mx`, `my`, `mz` (or `4`, `5`, `6`) | moment about the global $x$-, $y$- or $z$-axis, positive according to the right-hand rule |
| `tt` | heat rate supplied to the node; positive values add heat to the solid |
| `pw`, `pa` | volume flow rate of pore water or pore air supplied to the node; positive values flow into the model |

* The magnitude is applied to *every* node of the node set, it is not distributed over the nodes. A line load along an element edge has to be converted into work-equivalent nodal forces or moments (e.g. $qL/2$ at the two nodes of a linear edge of the length $L$, $qL/6$, $2qL/3$, $qL/6$ at the three nodes of a quadratic edge).
* Moments act on the rotational degrees of freedom `r1`, `r2`, `r3`. They can only be applied to nodes of [beam elements](../element/elements-beam.md) and [shell elements](../element/elements-shell.md); two-dimensional beams have the rotation `r3` only (label `mz`). A moment on a node without the corresponding rotation terminates the analysis with an error message.
* Heat supplies (`tt`) act only on independent temperature nodes of [u-T solids](../element/elements-ut.md). The magnitude is a heat rate (W in a 3D SI model); a negative value removes heat. In 2D, the heat rate is per unit out-of-plane thickness. Nodes without temperature and dependent temperature nodes of mixed elements cannot receive concentrated heat.
* Volume sources (`pw`, `pa`) act on the pore water or pore air pressure of the node (elements with pore pressure degrees of freedom, e.g. `u8p4`, `u4p4-stab`, `u8pp4`, `p4`). With a linear pressure interpolation of mixed elements (e.g. `u8p4`, `u6p3`) only the corner nodes carry a pore pressure; a source at a node without the pore pressure terminates the analysis with an error message. The magnitude is a volume rate (length³/time): in 2D per unit out-of-plane thickness, in axisymmetric models for the full circumference. Positive values supply fluid to the model, negative values extract it.
* Note the opposite sign of [`flow-w` of `*Dsload`](./dsload.md#inflowoutflow), which prescribes the outward normal velocity (positive values are an outflow). A uniform inflow $q$ (length/time) through an edge of the length $L$ corresponds to the work-equivalent nodal sources $qL/2$ at the two nodes of a linear pressure interpolation ($qL/6$, $2qL/3$, $qL/6$ for a quadratic pressure interpolation), or to `flow-w` with $-q$.
* Volume sources are not available for u-p-U elements (`u8p4u8-sat`, ...): their pore water flux is the relative fluid displacement `w`, which has to be prescribed instead. numgeo terminates with an error message.
* The supplied volume can be checked with the reactions [`RPW` and `RPA`](../output/print.md#node-output) of the nodes with prescribed pore pressure: in a steady state the sum of all sources and all reactions is zero.
* Every `*Cload` keyword is followed by exactly one data line. Several `*Cload` definitions acting on the same node add up.

Example: force of 10 kN in the negative $z$-direction and moment of 2 kNm about the $y$-axis at every node of the node set `tip`:

```numgeo
*Cload, ramp
tip, z, -10.0
*Cload, ramp
tip, my, 2.0
```

Example: a heat rate of 25 W supplied to every node of `heater_nodes` in a 3D model:

```numgeo
*Cload, instant
heater_nodes, tt, 25
```

Example: a water inflow of 1.5e-3 m³/s per m into a 0.5 m wide column through its top edge (linear pressure interpolation, nodes `top-ends` at both ends of the edge), the base drained, and the outflow printed at the base:

```numgeo
*Cload, instant
top-ends, pw, 7.5e-4
*Boundary
base, pw, 0
*Output, print
*Node, nset = base
RPW
```

The sum of `RPW` at the base is -1.5e-3 m³/s per m in the steady state. The volume sources and reactions are verified in the benchmark suite (cases `source-balance-p4` and `source-balance-u8p4`).

The moments are verified in the benchmark [Shell elements: loads](../../benchmark/shell/shell-loads.md#moments-cantilever-strip-and-3d-beam).
