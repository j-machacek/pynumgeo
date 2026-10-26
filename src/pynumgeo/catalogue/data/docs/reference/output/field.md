# Output, field

```numgeo 
*Output, <type>, <format 1>, <format 2> [, flush]
...
```

!!! note "Release information"

    GiD output was introduced in the [November 2025 release](../../release/release_notes_2025_11.md). Not all output options are supported in the GiD format.

The output can either be given for the external software packages

- Paraview: `<format 1> = vtk`
- GiD: `<format 1> = gid`

With the `<format 2>` keyword you can specify whether the output should be given in ASCII or binary format by using `<format 2> = ascii` or `<format 2> = binary`, respectively. Both `<format 1>` and `<format 2>` are not needed in case `print` is used. The following definitions count for both `field` and `print`.

The field output of all steps is written in the format of the first step with field output; `<format 1>` and `<format 2>` of later steps are not used. A step without `*Output, field` continues the field output of the previous step, and steps before the first field output write none (e.g. a geostatic step without field output).

Thermal nodal fields are available in both VTK and GiD. VTK ASCII writes these fields with 16 fractional digits; binary VTK uses double precision. Element-variable ASCII output uses six significant digits and GiD text output nine. Use binary VTK for comparisons of small differences in element temperatures, heat fluxes or stresses.

Use the `*Frequency` keyword to set the output frequency `<output interval>` in increments (integer required). Output is written for converged increments at the selected frequency and at the end of the step. A regular analysis does not automatically write a frame at time zero. Use the following sub-keywords to define output fields of variables stored at the nodes and the integration points of the elements:

## Node output

```numgeo 
*Output, field, <format 1>, <format 2> [, flush]
*Node, nset = <set name>
<variable 1>, ..., <variable n>
```

This sub-keyword defines the nodal variables to write to the output database. List the requested variables on the following line. VTK and GiD field variables are written over the model; node-set selection is retained for [print](print.md#node-output) and [user output](print.md#sec_user_print).

The following variables are currently available:

- `U`: Solid displacements. Vector field $\boldsymbol{u}$, magnitude $|\boldsymbol{u}|$ and components $u_i$ for $i=\{x,y,z\}$.

- `V`: Solid velocities. Vector field $\boldsymbol{v}$, magnitude $|\boldsymbol{v}|$ and components $v_i$ for $i=\{x,y,z\}$. This output is only available in analyses of type "Dynamic" or "Transient".

- `A`: Solid accelerations. Vector field $\boldsymbol{a}$, magnitude $|\boldsymbol{a}|$ and components $a_i$ for $i=\{x,y,z\}$. This output is only available in analyses of type "Dynamic".

- `Pw`: Pore-water pressure. Scalar field $p^w$. This output is only available for finite elements based on the $\boldsymbol{u}$-$p$ formulation discretising the solid displacement $\boldsymbol{u}$ and the pore water pressure $p^w$ as primary unknowns.

- `Uw`: Water displacements. Vector field $\boldsymbol{U}$, magnitude $|\boldsymbol{U}|$ and components $U_i$ for $i=\{x,y,z\}$. This output is only available for finite elements based on the $\boldsymbol{u}$-$\boldsymbol{U}$ formulation discretising the solid displacement $\boldsymbol{u}$ and the pore water displacement $\boldsymbol{U}$ as primary unknowns.

- `Pa`: Pore-air pressure. Scalar field $p^a$. This output is only available for finite elements based on the $\boldsymbol{u}$-$p$-$p$ formulation discretising the solid displacement $\boldsymbol{u}$, the pore water pressure $p^w$ and the pore air pressure $p^a$ as primary unknowns.

- `TEMP`: Absolute temperature. Scalar field `Temperature` $T$ (K in SI units), available at nodes of [u-T solids](../element/elements-ut.md). Mixed elements include temperatures interpolated at their dependent nodes.

- `DTEMP`: Temperature increment. Scalar field `Temperature increment` $\Delta T$ of the current converged increment (K in SI units).

- `TEMP_RATE`: Temperature rate. Scalar field `Temperature rate` $\Delta T/\Delta t$ of a [transient](../step/transient.md) step (K/s in SI units); zero in a static step.

    Thermal nodal variables are zero at nodes without temperature degree of freedom. In models which also contain other elements, such a zero does not represent a physical temperature of zero kelvin; restrict the display to the u-T solid elements, e.g. with the ParaView filter *Threshold* applied to `Temperature`.

- `UR`: Rotations of the nodes of [beam](../element/elements-beam.md) and [shell](../element/elements-shell.md) elements about the global axes. Vector field `Rotation` with the components $\varphi_i$ for $i=\{x,y,z\}$; zero at nodes without rotational degrees of freedom.

- `RF` (only vtk): Reaction forces. Vector field $\boldsymbol{RF}$, magnitude $|\boldsymbol{RF}|$ and components $RF_i$ for $i=\{x,y,z\}$.

- `RM`: Reaction moments at nodes with prescribed rotations. Vector field `Reaction moment` with the components $RM_i$ for $i=\{x,y,z\}$.

- `RFL`: Reaction heat flow. Scalar field `Reaction heat flow`, the heat rate supplied by a prescribed-temperature boundary condition. Positive values add heat to the solid (W in a 3D SI model; per unit out-of-plane thickness in 2D). In the VTK output it is zero at nodes without a prescribed temperature; print, user and GiD output give the remaining heat-flow residual there (zero within the convergence tolerance), as for `RF`. Prescribed sources, fluxes and film exchange are separate contributions to a global heat balance; they are not included in `RFL`.

    The physical heat balance includes reversible thermoelastic storage as well as $\rho c_\epsilon\dot T$; see the [coupled heat equation](../../theory/elements/thermoelastic-solids.md#balance-equations-and-thermodynamics).

!!! note "Sign of the reaction forces"

    `RF` and `RM` are the forces and moments which the model transmits **to the supports**, i.e. the internal nodal forces at the constrained degrees of freedom. They have the opposite sign of the reactions acting on the model. For a model loaded by its self weight (acting in the $-z$-direction) and supported at its base, the sum of `RF3` at the base is therefore negative and equal to the weight, and the sum of `RM` of a cantilever is the moment of the applied loads about the support.

- `Sets` (only vtk): Write the defined node sets (name + nodes) to the output file. The set name equals the output name. The nodes of the associated node set are given the (integer) value 1, all other nodes are given the (integer) value 0.

- `S`: Stress. Single (scalar) components $\sigma_{ij}$ for $i,j = \{x,y,z\}$ \[F/A\]. In case of porous elements $\sigma_{ij}$ is always the "effective stress".

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\sigma_{11}$ is the axial stress and $\sigma_{12}$ and $\sigma_{13}$ correspond to the shear stresses in local xy and xz-direction, respectively. All other components are zero.

- `Phantom-viscosity` (only vtk): Viscous part of the stress contributed by the "mechanical viscosity" model. Single (scalar) components $\sigma^{vis}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where "\*Mechanical viscosity' was defined.

- `E`: Strain. Single (scalar) components $\varepsilon_{ij}$ for $i,j = \{x,y,z\}$ \[-\]. $\varepsilon_{ij}$ is the total strain; it includes elastic, plastic and thermal contributions where present in the selected material model.

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\varepsilon_{11}$ is the axial strain and $\varepsilon_{12}$ and $\varepsilon_{13}$ correspond to the shear strains in local xy and xz-direction, respectively.

- `TEMP_IP`: Temperature interpolated to the integration point. Scalar absolute temperature $T$ (K in SI units). Available for [u-T solid elements](../element/elements-ut.md).

- `HFL1`, `HFL2`, `HFL3`: Components of the conductive heat flux $\boldsymbol q=-k\nabla T$ in the global coordinate directions (W/m² in SI units). `HFL3` is zero in 2D. Available for u-T solid elements.

- `TSTAB`: Capacity-scale coefficient $\tau$ of the temperature projection (J/(m³ K) in SI units); see [Thermal stabilisation](../material/thermal-stabilisation.md).

- `TEMP_MAT`: Constitutive temperature represented by the material stress (K in SI units). This state variable belongs to [Thermal elasticity](../material/mechanical/thermal_elasticity.md#state-variables).

- `void`: Void ratio. Scalar $e$ \[-\]. This output is only available for porous elements.

- `Sat_eff`: Effective degree of saturation. Scalar $S^e$. This output is only available for coupled porous elements. 

- `Sat`: Degree of saturation. Scalar $S^w$. This output is only available for coupled porous elements with two fluids occupying the pore space. 

- `Phantom-Elasticity` (only vtk): Part of the stress components (requested by the keyword 'S') contributed by the "phantom elasticity" model. Single (scalar) components $\sigma^{ph}_{ij}$ for $i,j = \{1,2,3\}$ [F/A]. Only for materials where "\*Phantom elasticity' was defined.

!!! note "Nodal values of integration point variables (vtk)"

    The VTK output holds one dataset per dimension of the elements: line elements (truss and beam elements, `<job>-1d-...`), surface elements (`<job>-2d-...`) and volume elements (`<job>-3d-...`). Stress, strain and element variables are extrapolated from the integration points to the nodes of each element and averaged over the elements **of the same dataset** which share the node. At a node shared by a truss or beam element and continuum elements, the nodal values of the soil therefore do not contain the truss or beam, and the nodal values of the truss or beam (e.g. `stress-truss`, `beam-moment-mz`, `interface-shear`) do not contain the soil. Element variables are averaged over the elements which provide the variable.

    The average is weighted with the size of the elements (area or volume; truss and beam elements: length). `*Node output, nset=<set name>, unweighted` selects the simple mean.

Additional nodal output variables:

- `Con_f` (only vtk): Connector force of a connector element. Scalar force acting in the direction of the longitudinal axis of the element. This output is only available for so-called "connector-elements".


    For embedded shells ([`section=plate`](../embedded-regions/interaction-surface-plate.md#output)) one additional dataset per region is written, which contains both faces of the wall and the toe with the contact status, the tractions, the capacities and the relative displacements as cell data.

Node output variables associated with contact definitions between two (or more) parts (only available in analyses including contacts):

- `Contact`:

    Mechanical contact variables.

    - Scalar Normal/Tangential stress $t_N$, $t_T$ \[Pressure\]

    - Scalar Normal/Tangential distance $g_N$, $g_T$ \[Length\]

    - Nodal contact force $F_x$, $F_y$, $F_z$ \[Force\]: the contribution of the contact to the nodal forces (vtk output in ASCII and binary format, print output)

-   `Contact_sdv` (only vtk):

    Contact state variables. Output depends on the chosen constitutive
    contact model. It is currently only available if the hypoplastic
    contact model is used.

-   `Contact_diagnostic` (only vtk):

    Contact diagnostic variables. The following variables are print to
    the output file:

    -   Scalar contact iteration (0/1/-1) It is 0 prior to the
        initialization of contacts. 1 if the contact is closed and -1 if
        the contact is open.

    -   Scalar convective coordinate failed (0/1) 0 if the evaluation
        of the convective coordinate was successful. 1 if the projection
        failed, indicating problems in the surface
        definition.

    -   Scalar convective coordinate \[-\] Local element coordinate
        computed in the minimization of the contact
        distance

    -   Scalar Segment type \[-\] Type of segment associated with a
        node using the `segmentmortar` contact discretisation
        technique.

## Element output

```numgeo 
*Output, field, <format 1>, <format 2> [, flush]
*Element, elset = <set name>
<variable 1>, ..., <variable n>
*Integration point, elset = <set name>
<variable 1>, ..., <variable n>
```

This sub-keyword defines the element variables, calculated at integration points, to write to the output database. List the variables on the following line. Element field output follows the model-wide VTK/GiD output; [print output](print.md#element-output) permits selection by element set. VTK element values are averages of the integration-point values; nodal output of these variables is extrapolated and averaged as described above. Use [integration-point print output](print.md#integration-point-output) to inspect individual integration points.

The following variables are currently available:

- `S`: Stress. Single (scalar) components $\sigma_{ij}$ for $i,j = \{x,y,z\}$ \[F/A\]. In case of porous elements $\sigma_{ij}$ is always the "effective stress".

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\sigma_{11}$ is the axial stress and $\sigma_{12}$ and $\sigma_{13}$ correspond to the shear stresses in local xy and xz-direction, respectively. All other components are zero.

- `Phantom-viscosity` (only vtk): Viscous part of the stress contributed by the "mechanical viscosity" model. Single (scalar) components $\sigma^{vis}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where "\*Mechanical viscosity' was defined.

- `E`: Strain. Single (scalar) components $\varepsilon_{ij}$ for $i,j = \{x,y,z\}$ \[-\]. $\varepsilon_{ij}$ is the total strain; it includes elastic, plastic and thermal contributions where present in the selected material model.

    For [Thermal elasticity](../material/mechanical/thermal_elasticity.md), the isotropic thermal strains are $\epsilon^{th}_{11}=\epsilon^{th}_{22}=\epsilon^{th}_{33}=\alpha(T-T_{\rm ref})$, with zero thermal shear strain. Elastic strain is total strain minus thermal strain. In plane strain, total $\epsilon_{33}=0$, although the thermal and elastic contributions are individually nonzero.

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\varepsilon_{11}$ is the axial strain and $\varepsilon_{12}$ and $\varepsilon_{13}$ correspond to the shear strains in local xy and xz-direction, respectively.

- `TEMP_IP`: Temperature interpolated to the integration point. Scalar absolute temperature $T$ (K in SI units). Available for [u-T solid elements](../element/elements-ut.md).

- `HFL1`, `HFL2`, `HFL3`: Components of the conductive heat flux $\boldsymbol q=-k\nabla T$ in the global coordinate directions (W/m² in SI units). `HFL3` is zero in 2D. Available for u-T solid elements.

- `TSTAB`: Capacity-scale coefficient $\tau$ of the temperature projection (J/(m³ K) in SI units); see [Thermal stabilisation](../material/thermal-stabilisation.md).

- `TEMP_MAT`: Constitutive temperature represented by the material stress (K in SI units). This state variable belongs to [Thermal elasticity](../material/mechanical/thermal_elasticity.md#state-variables).

- `void`: Void ratio. Scalar $e$ \[-\]. This output is only available for porous elements.

- `Sat_eff`: Effective degree of saturation. Scalar $S^e$. This output is only available for coupled porous elements. 

- `Sat`: Degree of saturation. Scalar $S^w$. This output is only available for coupled porous elements with two fluids occupying the pore space.

- `Phantom-Elasticity` (only vtk): Part of the stress components (requested by the keyword 'S') contributed by the "phantom elasticity" model. Single (scalar) components $\sigma^{ph}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where "*Phantom elasticity" was defined.

- `Sets` (only vtk): Write the defined element sets (name + elements) to the output file. The set name equals the output name. The elements of the associated element set are given the (integer) value 1, all other elements are given the (integer) value 0.

- `shell-n11`, `shell-n22`, `shell-n12`, `shell-m11`, `shell-m22`, `shell-m12`, `shell-q13`, `shell-q23`, `shell-mises-top`, `shell-mises-bot`: Stress resultants (membrane forces, bending moments, transverse shear forces) and von Mises stresses at the top and bottom surface of [shell elements](../element/elements-shell.md#output). Zero for all other elements.

- `shell-axes` (only vtk, only `*Element output`): Output axes of the [shell elements](../element/elements-shell.md#orientation-and-output-axes), to which the stress resultants refer, as the cell vectors `Shell axis 1`, `Shell axis 2` and `Shell normal`.

- `Mat` (only vtk): Write the material names and the associated element set as cell data to the output file. The material name is assigned to the output name. The elements of the associated element set are given the (integer) value 1, all other elements are given the (integer) value 0

Depending on the applied element type and material model, the label `SVARS` can be replaced by the name of the demanded output variable solemnly available for this specific element type/material model.
Possible output variables for different material models can be found under [*Material](../material/index.md). If the `<type>` is `user`, the state variable number has to be specified directly, e.g. `SDV1` or `SDV20`.
