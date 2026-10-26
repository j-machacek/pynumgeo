# Boundary-Flexible

```numgeo 
*Boundary-Flexible, [amplitude=<amplitude name>, <type>]
<node set name>, <dof>, <...>
``` 

!!! note "Release information"

    Flexible boundary conditions were introduced in the [November 2025 release](../../release/release_notes_2025_11.md).

This command is used to prescribe boundary conditions on nodes or node sets. It is possible to define more than one `*Boundary` command per step. However, the defined boundary conditions are only active in the step for which they are defined. 

!!! note " "

    `*Boundary-Flexible` conditions differ from general `*Boundary` conditions in that they **can vary both in time and space**. In particular, they may be active or inactive at individual nodes within the specified node set. Further details can be found in the [Theory Manual](../../theory/solution-method/boundary-conditions.md).

Temperature (`tt`) is not supported by `*Boundary-Flexible`. Use [`*Boundary`](boundary.md#temperature) to prescribe temperature at independent temperature nodes.

The `*Boundary-Flexible` command has the following keywords:

-   `amplitude=<amplitude name>`

    The optional `amplitude` parameter allows for the specification of an amplitude by which the boundary values are scaled (mainly used for non-linear static and dynamic calculations). This only makes sense for non-zero boundary values. Thus, in that case, the values entered on the sub-lines of the \*Boundary command are interpreted as reference values to be multiplied with the (time dependent) amplitude value to obtain the actual value.

    Example: `*Boundary, amplitude = loading-ramp`

-   `<type>`

    The second optional keyword `<type>` can be used to prescribe more "advanced" boundary conditions. 

    | Type | Description                        |  Section
    |--------------------|-----------------------|-----------------|
    | none | prescribe degree of freedom (dof)| [Section 1](#1-default)|
    |`type=moving-hydrostatic` | hydrostatic distribution with a "moving" zero-level | [Section 2](#2-moving-hydrostatic)|

- `<node set name>` = name of the node set to which the boundary condition is applied

- `<degree of freedom>` = the degree of freedom to be constrained. The following degrees of freedom can be modified:

    |Degrees of freedom  | Description                        | 
    |--------------------|------------------------------------| 
    | `u1`               |Displacement in x1-direction        | 
    | `u2`               |Displacement in x2-direction        | 
    | `u3`               |Displacement in x3-direction        | 
    | `r1`               |Rotation in x1-direction (only beam elements)       | 
    | `r2`               |Rotation in x2-direction (only beam elements)       | 
    | `r3`               |Rotation in x3-direction (only beam elements)       |
    | `pw`               |Pore-water pressure                 | 
    | `pa`               |Pore-air pressure                   | 
    | `w1`               |Water displacement in x1-direction  | 
    | `w2`               |Water displacement in x2-direction  | 
    | `w3`               |Water displacement in x3-direction  | 


<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Good to know__

    ---

    * Boundary conditions can only be applied to degrees of freedom that are actually defined for the chosen element type. For example, in single-phase solid elements of type `u-solid`, you can prescribe a boundary condition for the horizontal displacement `u1`, but attempting to prescribe a boundary condition for `pw` would raise an error, since `pw` is not an active degree of freedom for these elements.

    * Boundary conditions defined using this command **can vary in time and space** but are active at all nodes of the assigned node set. 

    [:octicons-arrow-right-24: The theory behind the implementations](../../theory/solution-method/boundary-conditions.md)
</div>

---------------

## 1. Default

For the default case (no `type` prescribed), the command takes the flowing form:  

```
*Boundary-Flexible
<node set name>, <dof>, <value>
```

They can be repeated as often as needed.

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the amplitude value (in case an amplitude is assigned to the boundary condition).

---------------

## 2. Moving Hydrostatic

If `type=moving-hydrostatic` is used to define a more general form of the `type=hydrostatic` boundary condition, the command takes the form: 

```
*Boundary-Flexible, type=moving-hydrostatic
<node set name>, <dof>, <dir>, <slope>, <zero-level 0>, <t0>, <zero-level 1>, <t1> 
```

- `<node set name>` = name of the node set to which the boundary condition is applied
- `<dof>` = the degree of freedom to be constrained.
- `<dir>` = Direction of action in global coordinates (x=1, y=2, z=3)
- `<slope>` = slope of hydrostatic distribution, e.g. unit weight of water in case of a hydrostatic distribution pore water pressure.
- `<zero-level 0>` = coordinate of the initial zero-level for the hydrostatic distribution at time `t0`
- `<t0>` = initial time `t0`
- `<zero-level 1>` = coordinate of the final zero-level for the hydrostatic distribution at time `t1`

<figure id="fig_flexbc_moving_hydrostatic">
  <div class="center">
    <img src="./assets/moving-hydrostatic-flexible.svg" alt="Flexible hydrostatic boundary condition that activates or releases nodes as the reference level changes."/>
    <em>Figure 2: Example for boundary conditions of type `moving-hydrostatic`</em>
  </div>
</figure>

!!! note " "

    * For times smaller than `t0` the zero-level for the hydrostatic distribution is `<zero-level 0>` and for times larger than `t1` the zero-level corresponds to `<zero-level 1>`

    * Unlike the `*Boundary, type = moving-hydrostatic` command (see [*Boundary](./boundary.md#6-moving-hydrostatic)), the `*Boundary-Flexible` command releases the `dofs` above the zero level instead of enforcing negative values.
