# Boundary

```numgeo 
*Boundary, [amplitude=<amplitude name>, <type>]
<node set name>, <dof>, <...>
``` 

This command is used to prescribe boundary conditions on nodes or node sets. It is possible to define more than one `*Boundary` command per step. However, the defined boundary conditions are only active in the step for which they are defined. The `*Boundary` command has the following keywords:

-   `amplitude=<amplitude name>`

    The optional `amplitude` parameter allows for the specification of an amplitude by which the boundary values are scaled (mainly used for non-linear static and dynamic calculations). This only makes sense for non-zero boundary values. Thus, in that case, the values entered on the sub-lines of the \*Boundary command are interpreted as reference values to be multiplied with the (time dependent) amplitude value to obtain the actual value.

    Example: `*Boundary, amplitude = loading-ramp`

-   `<type>`

    The second optional keyword `<type>` can be used to prescribe more "advanced" boundary conditions. 

    | Type | Description                        |  Section
    |--------------------|-----------------------|-----------------|
    | none | prescribe degree of freedom (dof)| [Section 1](#1-default)|
    |`type=velocity` | first time derivative of the prescribed dof| [Section 2](#2-velocity)|
    |`type=acceleration` | second time derivative of the prescribed dof| [Section 3](#3-acceleration)|
    |`type=increment` | increment (i.e. the change) of a dof | [Section 4](#4-increment)|
    |`type=hydrostatic` | hydrostatic (linear increase with depth) distribution | [Section 5](#5-hydrostatic)|
    |`type=moving-hydrostatic` | hydrostatic distribution with a "moving" zero-level | [Section 6](#6-moving-hydrostatic)|

- `<node set name>` = name of the node set to which the boundary condition is applied

- `<degree of freedom>` = the degree of freedom to be constrained. The following degrees of freedom can be modified:

    |Degrees of freedom  | Description                        | 
    |--------------------|------------------------------------| 
    | `u1`               |Displacement in x1-direction        | 
    | `u2`               |Displacement in x2-direction        | 
    | `u3`               |Displacement in x3-direction        | 
    | `r1`               |Rotation about the x1-axis (beam and shell elements)       | 
    | `r2`               |Rotation about the x2-axis (beam and shell elements)       | 
    | `r3`               |Rotation about the x3-axis (beam and shell elements)       |
    | `pw`               |Pore-water pressure                 | 
    | `pa`               |Pore-air pressure                   |
    | `tt`               |Absolute [temperature](#temperature) of u-T solids |
    | `w1`               |Water displacement in x1-direction  | 
    | `w2`               |Water displacement in x2-direction  | 
    | `w3`               |Water displacement in x3-direction  | 


<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Good to know__

    ---

    * Boundary conditions can only be applied to degrees of freedom that are actually defined for the chosen element type. For example, in single-phase solid elements of type `u-solid`, you can prescribe a boundary condition for the horizontal displacement `u1`, but attempting to prescribe a boundary condition for `pw` would raise an error, since `pw` is not an active degree of freedom for these elements.

    * Boundary conditions defined using this command **can vary in time** but are active at all nodes of the assigned node set. 

    [:octicons-arrow-right-24: The theory behind the implementations](../../theory/solution-method/boundary-conditions.md)
</div>

---------------

## 1. Default

For the default case (no `type` prescribed), the command takes the flowing form:  

```
*Boundary
<node set name>, <dof>, <value>
```

They can be repeated as often as needed.

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the amplitude value (in case an amplitude is assigned to the boundary condition).

### Temperature

Use `tt` to prescribe the absolute temperature $T$ at the independent temperature nodes of [u-T solids](../element/elements-ut.md). These are all nodes of equal-order elements and the corner nodes of mixed elements; a node set containing other nodes of mixed elements is rejected. The prescribed temperature must be finite and strictly positive; in SI units it is given in kelvin.

```numgeo
*Boundary
hot_nodes, tt, 303.15
```

The default boundary type prescribes the total temperature. The options `type=velocity`, `type=acceleration`, `type=increment`, `type=hydrostatic` and `type=moving-hydrostatic` are not available for `tt`. Temperature constraints through `*UBoundary`, `*Flexible-Boundary` or `*Equation` are not supported.

An assigned [amplitude](../amplitude.md) multiplies the **absolute** reference temperature. For example, a prescribed change from 300 K to 310 K can be defined with a reference value of 310 K and a tabular amplitude increasing from $300/310$ to 1. A zero amplitude would prescribe zero kelvin and is invalid. The temperature before the first increment is defined separately with [`*Initial conditions, Type=temperature`](../initial-conditions/temperature.md).

For prescribed heat input, use [`*Cload`](cload.md) or [`*Dload`](dload.md#heat-flux).

---------------

## 2. Velocity

For `type=velocity` the first derivative of the selected `dof` w.r.t. time is prescribed. The command takes the flowing form:  

```
*Boundary
<node set name>, <dof>, <value>
```

They can be repeated as often as needed.

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the amplitude value (in case an amplitude is assigned to the boundary condition).

---------------

## 3. Acceleration

For `type=acceleration` the second derivative of the selected `dof` w.r.t. time is prescribed. The command takes the flowing form:  

```
*Boundary
<node set name>, <dof>, <value>
```

They can be repeated as often as needed.

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the amplitude value (in case an amplitude is assigned to the boundary condition).

---------------

## 4. Increment

For `type=increment`, the increment (i.e. the change) of the selected `dof` relative to its original value at the start of the step. The command takes the flowing form:  

```
*Boundary
<node set name>, <dof>, <value>
```

They can be repeated as often as needed.

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the amplitude value (in case an amplitude is assigned to the boundary condition).

---------------

## 5. Hydrostatic

If `type=hydrostatic` is used to define the boundary condition, the command differs from the ones above and takes the form:  

```
*Boundary
<node set name>, <dof>, <slope>, <zero level>
```

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<slope>` = slope of hydrostatic distribution, e.g. unit weight of water in case of a hydrostatic distribution pore water pressure.
- `<zero level>` = coordinate (y-coordinate in 2-D and z-coordinate in 3-D) where the distribution is zero, e.g. location of the water table in case of a hydrostatic distribution of pore water pressure

An example for the `hydrostatic` boundary condition is depicted in [Figure1](#fig_bc_hydrostatic) for two different geometrical settings (scenario 1 and scenario 2).

<figure id="fig_bc_hydrostatic">
  <div class="center">
    <img src="./assets/hydrostatic.svg" alt="Hydrostatic boundary condition with pressure increasing linearly below a fixed reference level."/>
    <em>Figure 1: Example for boundary conditions of type `hydrostatic`</em>
  </div>
</figure>

!!! note " "

    Although the term 'hydrostatic' implies that this boundary condition is intended for the pore water pressure degree of freedom (DOF), it can also be applied to other degrees of freedom. For instance, it can be used to describe the horizontal movement of a hinged sheet pile wall.

---------------

## 6. Moving Hydrostatic

If `type=moving-hydrostatic` is used to define a more general form of the `type=hydrostatic` boundary condition, the command takes the form: 

```
*Boundary
<node set name>, <dof>, <dir>, <slope>, <zero-level 0>, <t0>, <zero-level 1>, <t1> 
```

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<dir>` = Direction of action in global coordinates (x=1, y=2, z=3)
- `<slope>` = slope of hydrostatic distribution, e.g. unit weight of water in case of a hydrostatic distribution pore water pressure.
- `<zero-level 0>` = coordinate of the initial zero-level for the hydrostatic distribution at time `t0`
- `<t0>` = initial time `t0`
- `<zero-level 1>` = coordinate of the final zero-level for the hydrostatic distribution at time `t1`

<figure id="fig_bc_moving_hydrostatic">
  <div class="center">
    <img src="./assets/moving-hydrostatic.svg" alt="Hydrostatic boundary condition with a reference level that changes during the step."/>
    <em>Figure 2: Example for boundary conditions of type `moving-hydrostatic`</em>
  </div>
</figure>

!!! note " "

    For times smaller than `t0` the zero-level for the hydrostatic distribution is `<zero-level 0>` and for times larger than `t1` the zero-level corresponds to `<zero-level 1>`
