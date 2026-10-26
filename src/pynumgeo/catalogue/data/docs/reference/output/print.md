# Output, print

This option is used to write variables to the print output files. It must be used as a sub-keyword of the `*Output` keyword. Set `<set name>` equal to the set name for which the output should be defined. In the subsequent line, the output variables are defined.

!!! warning "Restriction"
    The print output is intended to write detailed information for **some selected** nodes, elements or integration points of the model to files. To reduce access times, the print output files are kept open during the simulation. 

    On Ubuntu, the default limit for simultaneously open files is set to 1024. To accommodate this, numgeo restricts the number of open files to 300 per output type (node, element, or integration point). If the number of files per output type exceeds this limit, only the first 300 files will remain open during the simulation, while additional files will be closed after each write operation and reopened when needed. This behavior may negatively affect simulation performance. The same functionality is applied across platforms, including both Windows and Linux.


## Node output

```numgeo 
*Output, print
*Node, nset = <set name>
<variable 1>, ..., <variable n>
```

The available output variables are the same as for `*Output, field` (see [*Output, field](./field.md))  with
the addition of

-   `COORDS`:

    The coordinates of the node in reference configuration.

The reaction forces `RF` and moments `RM` are the forces and moments transmitted to the supports (opposite sign of the reactions acting on the model), see [*Output, field](./field.md#node-output). For temperature, `RFL` is the heat rate supplied to the solid by prescribed-temperature conditions and is positive into the solid.

For the pore fluids, `RPW` and `RPA` are the volume flow rates of pore water and pore air supplied to the model at nodes with prescribed pore water or pore air pressure (length³/time; in 2D per unit out-of-plane thickness, in axisymmetric models for the full circumference). They are positive into the model and negative for an outflow, e.g. at a drained boundary, and include volume sources [`*Cload, pw` or `pa`](../boundary-conditions/cload.md) at the same node. In a steady state the sum of all `RPW` and of all volume sources of the model is zero; in a transient analysis it equals the rate of change of the stored water volume. For u-p-U elements (`u8p4u8-sat`, ...) the flux across the boundary is the relative fluid displacement `w`, and `RPW` is not the outflow of the boundary. Request the outflow at a drained base with:

```numgeo
*Output, print
*Node, nset = base
RPW
```

The nodal temperature variables `TEMP`, `DTEMP`, `TEMP_RATE` and `RFL` use the same definitions as in [field output](field.md#node-output); the print files label them `Temp`, `dTemp`, `Temp_rate` and `RFL`. For example, request a temperature and heat-reaction history at selected nodes with:

```numgeo
*Output, print
*Node, nset = hot_nodes
TEMP, RFL
```

## Element output

This option is used to write element variables (stored at the element centroid) to the print output files. It must be used as a sub-keyword of the `*Output` keyword. Set `<set name>` equal to the element set name
for which the output should be defined. In the subsequent line, the output variables are defined.

```numgeo 
*Output, print
*Element, elset = <set name>
<variable 1>, ..., <variable n>
```

The available output variables are the same as for `*Output, field` (see [*Output, field](./field.md)) with
the addition of

-   `COORDS`/`COORDS_UPD`:

    The coordinate of the centroid in reference or current configuration.

## Integration point output

```numgeo 
*Output, print
*Integration point, elset = <set name>
<variable 1>, ..., <variable n>
```

This option is used to write element variables (stored at integration points) to the print output files. It must be used as a sub-keyword of the `*Output` keyword. Set `<set name>` equal to the element set name for which the output should be defined. In the subsequent line, the output variables are defined.

The following variables are currently available:

-   `COORDS_IGP`/`COORDS_IGP_UPD`:

    The coordinates of the integration points in reference or current configuration.

-   `S`:

    Stress. Single (scalar) components $\sigma_{ij}$ for $i,j = \{x,y,z\}$ \[F/A\]. In case of porous elements $\sigma_{ij}$ is always the "effective stress".

-   `Phantom-viscosity`:

    Viscous part of the stress contributed by the "mechanical viscosity" model. Single (scalar) components $\sigma^{vis}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where `*Mechanical viscosity` was defined.

-   `E`:

    Strain. Single (scalar) components $\varepsilon_{ij}$ for $i,j = \{x,y,z\}$ \[-\]. $\varepsilon_{ij}$ is the total strain, including thermal strain where present in the selected material model.

-   `TEMP_IP`:

    Temperature interpolated to the integration point. Scalar absolute temperature $T$ (K in SI units). Available for [u-T solid elements](../element/elements-ut.md).

-   `HFL1`, `HFL2`, `HFL3`:

    Components of the conductive heat flux $\boldsymbol q=-k\nabla T$ in the global coordinate directions (W/m² in SI units). `HFL3` is zero in 2D. Available for u-T solid elements.

-   `TSTAB`:

    Capacity-scale coefficient $\tau$ of the temperature projection (J/(m³ K) in SI units); see [Thermal stabilisation](../material/thermal-stabilisation.md).

-   `TEMP_MAT`:

    Constitutive temperature represented by the material stress (K in SI units). This state variable belongs to [Thermal elasticity](../material/mechanical/thermal_elasticity.md#state-variables).

-   `VOID`:

    Void ratio. Scalar $e$ \[-\]. This output is only available for porous elements.

-   `Sat_eff`:

    Effective degree of saturation. Scalar $S^e$. This output is only available for coupled porous elements. 

-   `Sat`:

    Degree of saturation. Scalar $S^w$. This output is only available for coupled porous elements with two fluids occupying the pore space. 

-   `Phantom-Elasticity`:

    Part of the stress components (requested by the keyword 'S') contributed by the "phantom elasticity" model. Single (scalar) components $\sigma^{ph}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where "\*Phantom elasticity' was defined.

-   `Sets`:

    Write the defined element sets (name + elements) to the output file. The set name equals the output name. The elements of the associated element set are given the (integer) value 1, all other elements are given the (integer) value 0.

-   `Mat`:

    Write the material names and the associated element set as cell data to the output file. The material name is assigned to the output name. The elements of the associated element set are given the (integer) value 1, all other elements are given the (integer) value 0

Depending on the applied element type and material model, the label `SVARS` can be replaced by the name of the demanded output variable solemnly available for this specific element type/material model. Possible output variables for different material models can be found here [*Material](../material/index.md). If the `<type>` is `user`, the state variable number has to be directly specified, e.g. `SDV1` or `SDV20`.

## Output, user {#sec_user_print}

```numgeo 
*Output, user
*Node, nset = <set name>
<variable 1>, ..., <variable n>
*Element, elset = <set name>
<variable 1>, ..., <variable n>
```

This option is used to write variables to the user files, where the specified variables are written to (initial) user files explained in [*Initial conditions](../initial-conditions/index.md). It must be used as a sub-keyword of the `*Output` keyword. Set `<set name>` equal to the set name for which the output should be defined. In the subsequent line, the output variables are defined.

Depending on the variables, the corresponding user routine will be automatically written. The following variables are currently available:

-   Supported displacement and pore-pressure variables generate the user-defined boundary data described under [User files](../user/index.md), which can be used with `*UBoundary`.

-   `TEMP`, `DTEMP`, `TEMP_RATE` and `RFL` write nodal snapshots for the selected node sets. Their meanings are given under [Node output](field.md#node-output). A temperature snapshot exports data; `*UBoundary` does not support a temperature callback.

-   `S_IGP`

    The stress of the integration points. In this case, the user defined initial stress field file (see [here](../user/index.md)) is generated.

-   `SDV`: The statev with the number [xx]. In this case, the user defined initial state field file (see [here](../user/index.md)) is generated. For instance, `SDV1` is typically the internal void ratio of the constitutive model. For the HCA models (see [here](../material/index.md)), `SDV100` is the strain amplitude. Please contact the developers if you need a specific state variable number for your output.

Nodal snapshots use the internal node index for rows and the requested variable order for columns. `U`, `V` and `A` occupy two columns in 2D or three in 3D; each thermal variable occupies one column. Unselected rows are zero. If overlapping sets specify different layouts, the later set replaces the row. Each write replaces the snapshot with the latest selected increment.

The generated material-state files can be read by the main program using [`*Read State`](../read-state.md).
