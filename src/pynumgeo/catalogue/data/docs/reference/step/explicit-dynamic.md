```numgeo 
*Explicit Dynamic
<Delta t_0>, <t_step>, [<Delta t_min>], [<Delta t_max>]
[*Mass Scaling=<>]
[*Time integration,instance=<>]
```
This procedure is used to calculate the response of a structure subject
to dynamic loading using an explicit integration procedure of the
equations of motion. In a dynamic step, loads are by default applied by
their full magnitude at the start of the step. Other loading patterns
can be prescribed by using previously defined amplitudes.

-   The first line specifies the time incrementation. The specification
    of an initial time increment $\Delta t_0$ is always required. $t_{step}$ is the overall step
    time, which has to be specified in any case as well.$\Delta t_{min}$ is the minimum
    used time increment, which may be omitted, and $\Delta t_{max}$ is the maximum
    allowed time increment, which may be omitted as well. If only $\Delta t_0$ and $t_{step}$
    are specified, the minimum stable time increment $\Delta t_{crit}$
    is used for all increments after the first increment. If $\Delta t_{min}$ is given
    (and not equivalent to zero) $\Delta t=$$\Delta t_{min}$ holds if $\Delta t_{crit}<$$\Delta t_{min}$
    . If $\Delta t_{max}$ is given ($\Delta t_{min}$ has to be defined in this case, potentially set to
    zero) $\Delta t =$$\Delta t_{max}$ holds if $\Delta t_{crit}>$$\Delta t_{max}$ . The value of $\Delta t_{crit}$ can be scaled using the optional `scale factor =< >` as explained in the [step definition](./index.md).

-   
```numgeo 
[*Mass Scaling=<>]
```
Use this keyword to globally scale the mass by the specified factor,
    thereby increasing the minimum stable time increment
    $\Delta t_{crit}$.
-   
```numgeo 
[*Time integration,instance=<>]
```
Use this keyword to use implicit time integration for the specified instance, while all other instances of the model are using explicit time integration. The specified instance has to be the first instance defined in the model. By default, Backward Euler is used for the implicit time integration. Details on this so-called mixed IMplicit-EXplicit (IMEX) scheme can be found in [@Staubach2024_IMEX].

The following elements are supported in explicit analyses:

| **Element label**|Dim | **Shape** | **Nodes** | **Interpolation Order** | **nIP** | **Remarks**
|------------------|----|-----------|-----------|-------------------------|---------|-------------
|`u4-solid-red`    | 2D | rectangle | 4         | linear                  | 1       | (2)
|`u8-solid-3D-red` | 3D | brick     | 8         | linear                  | 1       | (2)
|`u4u4-red`        | 2D | rectangle | 4         | linear                  | 1       | (2)
|`u8u8-3d-red`     | 3D | brick     | 8         | linear                  | 1       | (2)

  \*      **nIP** = number of integration points

  (2)   Reduced integration: This element does not suffer from the same locking issues as fully integrated elements, however, due to the rank deficiency of the element stiffness matrix, an Hourglass stiffness has to be applied to prevent spurious zero-energy modes. For more information see the `*Material` Section and the Theory Manual
