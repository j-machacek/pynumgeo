# Body Force

```numgeo
*Body Force, <option>
<element set name>, grav, <mag>, <dir1, dir2, dir3>
```

This command defines a body force acting on the volumes of 3D elements (or areas in 2D) within the specified `<element set name>`. All sub-arguments are mandatory.

### Arguments

- `<option>`

    Specifies how the load is applied over time. The following options are available:

    - `instant`: The full load is applied instantaneously at the beginning of the step.
    
    - `ramp`: The load increases linearly with time from 0 % at the start to 100 % at the end of the step.
    
    - `Amplitude = <amplitude name>`: Applies the load according to a predefined amplitude function.

- `<element set name>`

    The name of the element set to which the body force should be applied.

- `grav`

    A fixed keyword indicating that a gravity-type body force is to be applied, defined as the vector  
    $\boldsymbol{g} = (g_1, g_2, g_3)^T$.

- `<mag>`

    The magnitude of the gravitational acceleration $g = \|\boldsymbol{g}\|$, specified in units of L/T² (e.g. m/s²).

- `<dir1, dir2, dir3>`

    A direction vector defining the direction of the gravity load: $\hat{\boldsymbol{g}} = \boldsymbol{g} / \|\boldsymbol{g}\|$.

!!! note "Loads in a sequence of steps"

    The load acts only in the step in which it is defined; `ramp` starts from zero at the beginning of every step. A load which is to remain active has to be defined again in the following steps (usually with `instant`), see [Loads in a sequence of steps](./index.md#loads-in-a-sequence-of-steps).

------

### Example

To define a gravitational force of 9.81 m/s² acting in the negative z-direction on all elements in a 3D Cartesian coordinate system (with the z-axis pointing upwards), use:

$$
\boldsymbol{g} = \begin{bmatrix} 0 \\ 0 \\ -9.81 \end{bmatrix} = 9.81 \cdot \begin{bmatrix} 0 \\ 0 \\ -1 \end{bmatrix}
$$

The corresponding numgeo command is:

```numgeo
*Body Force, instant
all, grav, 9.81, 0, 0, -1
```
