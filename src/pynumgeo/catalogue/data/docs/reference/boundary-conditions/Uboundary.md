# UBoundary

```numgeo 
*UBoundary [, <type>]
<node set name>, <degree of freedom>, <value>
``` 

This command is used to prescribe user-defined boundary conditions on nodes or node sets. If this command is used, `numgeo` expects the user-defined subroutine to be accessible (see [here](../user/boundary.md)). Therefore, the user has to implement the desired relation for the boundary condition using the predefined `user_boundary_conditions` interface, create the corresponding shared object `user_boundary_conditions.so` and place the object in the current working directory. For the compilation of the subroutine, a shell script is provided. It is possible to describe multiple degrees of freedom using one user file, since the name of the degree of freedom is passed into the subroutine; see [here](../user/boundary.md).

Temperature (`tt`) is not supported by `*UBoundary`. Use [`*Boundary`](boundary.md#temperature), optionally with an amplitude, to prescribe temperature.

- `<type>`

    The  optional keyword `<type>` can be used to define time derivatives in the subroutine rather than the actual value of the boundary conditions. For instance, if   `type=velocity` is defined, the integrated value (e.g. displacement) is automatically calculated after the call of the subroutine, such that it is not required to define the integrated value (e.g. displacement) within the subroutine. By default, the type is none. 

    | Type | Description |
    |--------------------|-----------------------|
    | none | prescribe degree of freedom (DOF) |
    | `type=velocity` | first time derivative of the prescribed DOF |
    | `type=acceleration` | second time derivative of the prescribed DOF |


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


- `<value>` = set this parameter equal to the value to be prescribed to the boundary condition. Notice that this value is interpreted as a reference value, which is multiplied with the value defined in the user subroutine. It is recommended to set this value to 1.0 and define the desired value directly in the user subroutine.


<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Good to know__

    ---

    * Boundary conditions can only be applied to degrees of freedom that are actually defined for the chosen element type. For example, in single-phase solid elements of type `u-solid`, you can prescribe a boundary condition for the horizontal displacement `u1`, but attempting to prescribe a boundary condition for `pw` would raise an error, since `pw` is not an active degree of freedom for these elements.

    * Boundary conditions defined using this command **can vary in time** but are active at all nodes of the assigned node set. 

    [:octicons-arrow-right-24: The theory behind the implementations](../../theory/solution-method/boundary-conditions.md)
</div>
