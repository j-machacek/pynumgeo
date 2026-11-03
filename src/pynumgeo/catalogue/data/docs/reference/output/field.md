# Output, field

```numgeo 
*Output, <type>, <format 1>, <format 2>
...
```

!!! note "Release information"

    GiD output was introduced in the [November 2025 release](../../release/release_notes_2025_11.md). Not all output options are supported in the GiD format.

The output can either be given for the external software packages

- Paraview: `<format 1> = vtk`
- GiD: `<format 1> = gid`

With the `<format 2>` keyword you can specify whether the output should be given in ASCII or binary format by using `<format 2> = ascii` or `<format 2> = binary`, respectively. For VTK, `<format 2> = binary-zlib` compresses the binary files with zlib: ParaView reads them directly and all values are unchanged, while writing and reading take longer. GiD ignores the compression and writes `binary` with a warning. Both `<format 1>` and `<format 2>` are not needed in case `print` is used. The output files are complete after every written increment and can be opened while the calculation is running. The following definitions count for both `field` and `print`.

The field output of all steps is written in the format of the first step with field output; `<format 1>` and `<format 2>` of later steps are not used. A step without `*Output, field` continues the field output of the previous step, and steps before the first field output write none (e.g. a geostatic step without field output).

Thermal nodal fields are available in both VTK and GiD. VTK ASCII writes these fields with 16 fractional digits; binary VTK uses double precision. Element-variable ASCII output uses six significant digits and GiD text output nine. Use binary VTK for comparisons of small differences in element temperatures, heat fluxes or stresses.

Use the `*Frequency` keyword to set the output frequency `<output interval>` in increments (integer required). Output is written for converged increments at the selected frequency and at the end of the step. A regular analysis does not automatically write a frame at time zero. Use the following sub-keywords to define output fields of variables stored at the nodes and the integration points of the elements:

## Node output

```numgeo 
*Output, field, <format 1>, <format 2>
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

- `Sets` (only vtk): Write the defined node sets to the output file as the point data `nset` with one component per node set; the component names are the set names (in upper case). The nodes of a set have the value 1 in its component, all other nodes the value 0.

- `S`: Stress $\sigma_{ij}$ for $i,j = \{x,y,z\}$ \[F/A\]. In case of porous elements $\sigma_{ij}$ is always the "effective stress". The vtk output contains the symmetric tensor `Stress` with the six components $\sigma_{xx}$, $\sigma_{yy}$, $\sigma_{zz}$, $\sigma_{xy}$, $\sigma_{yz}$, $\sigma_{xz}$ ($\sigma_{yz} = \sigma_{xz} = 0$ in 2D models). With the option `unweighted` the single (scalar) components `Stress 11`, `Stress 22`, `Stress 33` and `Stress 12` (in 3D also `Stress 13` and `Stress 23`) are written instead.

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\sigma_{11}$ is the axial stress and $\sigma_{12}$ and $\sigma_{13}$ correspond to the shear stresses in local xy and xz-direction, respectively. All other components are zero.

- `Phantom-viscosity` (only vtk): Viscous part of the stress contributed by the "mechanical viscosity" model. Single (scalar) components $\sigma^{vis}_{ij}$ for $i,j = \{1,2,3\}$ \[F/A\]. Only for materials where "\*Mechanical viscosity' was defined.

- `E`: Strain $\varepsilon_{ij}$ for $i,j = \{x,y,z\}$ \[-\]. $\varepsilon_{ij}$ is the total strain; it includes elastic, plastic and thermal contributions where present in the selected material model. The vtk output contains the symmetric tensor `Strain` with the components in the order given for `S`; its shear components are the engineering shear strains $2\varepsilon_{ij}$. With the option `unweighted` the single components `Strain 11`, `Strain 22`, `Strain 33` and `Strain 12 (*2)` (in 3D also `Strain 31 (*2)` and `Strain 23 (*2)`) are written instead.

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

    Contact diagnostic variables. The following variables are written to
    the output file:

    -   `Contact projection failed` (0/1): 0 if the evaluation
        of the convective coordinate was successful, 1 if the projection
        failed, indicating problems in the surface
        definition.

    -   `Convective coordinate` \[-\] (in 3D `Convective coordinate Xi`
        and `Convective coordinate Eta`): local element coordinate
        computed in the minimization of the contact distance.

    -   `Connected node`: number of the node of the opposite surface
        to which the contact node is connected.

    -   `Penalty factor` and `Tangential penalty factor`: normal and
        tangential penalty factor of the contact node.

    -   `Segment 1`, `Segment 2`, `Segment 3` \[-\]: type of the segments associated with a
        node using the `segmentmortar` contact discretisation
        technique, together with the coordinates of the segment nodes.

## Element output

```numgeo 
*Output, field, <format 1>, <format 2>
*Element, elset = <set name>
<variable 1>, ..., <variable n>
```

This sub-keyword defines the element variables, calculated at integration points, to write to the output database. List the variables on the following line. Element field output follows the model-wide VTK/GiD output; [print output](print.md#element-output) permits selection by element set. VTK element values are averages of the integration-point values; nodal output of these variables is extrapolated and averaged as described above. The values of the individual integration points are written with [`*Integration point`](#integration-point-output) (all elements, vtk) or the [integration-point print output](print.md#integration-point-output) (element set).

The following variables are currently available:

- `S`: Stress $\sigma_{ij}$ for $i,j = \{x,y,z\}$ \[F/A\]. In case of porous elements $\sigma_{ij}$ is always the "effective stress". The vtk output contains the symmetric tensor `Stress` (components as for the node output).

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\sigma_{11}$ is the axial stress and $\sigma_{12}$ and $\sigma_{13}$ correspond to the shear stresses in local xy and xz-direction, respectively. All other components are zero.

- `Phantom-viscosity` (only vtk): Viscous part of the stress contributed by the "mechanical viscosity" model, written as the symmetric tensor `Stress-PhVis` (components as for `S`) \[F/A\]. Only for materials where "\*Mechanical viscosity' was defined.

- `E`: Strain $\varepsilon_{ij}$ for $i,j = \{x,y,z\}$ \[-\]. $\varepsilon_{ij}$ is the total strain; it includes elastic, plastic and thermal contributions where present in the selected material model. The vtk output contains the symmetric tensor `Strain` (components as for `S`; shear components as engineering shear strains $2\varepsilon_{ij}$).

    For [Thermal elasticity](../material/mechanical/thermal_elasticity.md), the isotropic thermal strains are $\epsilon^{th}_{11}=\epsilon^{th}_{22}=\epsilon^{th}_{33}=\alpha(T-T_{\rm ref})$, with zero thermal shear strain. Elastic strain is total strain minus thermal strain. In plane strain, total $\epsilon_{33}=0$, although the thermal and elastic contributions are individually nonzero.

    For [Beam](../element/elements-beam.md) and [Truss](../element/elements-u-truss.md) elements, $\varepsilon_{11}$ is the axial strain and $\varepsilon_{12}$ and $\varepsilon_{13}$ correspond to the shear strains in local xy and xz-direction, respectively.

- `TEMP_IP`: Temperature interpolated to the integration point. Scalar absolute temperature $T$ (K in SI units). Available for [u-T solid elements](../element/elements-ut.md).

- `HFL1`, `HFL2`, `HFL3`: Components of the conductive heat flux $\boldsymbol q=-k\nabla T$ in the global coordinate directions (W/m² in SI units). `HFL3` is zero in 2D. Available for u-T solid elements.

- `TSTAB`: Capacity-scale coefficient $\tau$ of the temperature projection (J/(m³ K) in SI units); see [Thermal stabilisation](../material/thermal-stabilisation.md).

- `TEMP_MAT`: Constitutive temperature represented by the material stress (K in SI units). This state variable belongs to [Thermal elasticity](../material/mechanical/thermal_elasticity.md#state-variables).

- `void`: Void ratio. Scalar $e$ \[-\]. This output is only available for porous elements.

- `Sat_eff`: Effective degree of saturation. Scalar $S^e$. This output is only available for coupled porous elements. 

- `Sat`: Degree of saturation. Scalar $S^w$. This output is only available for coupled porous elements with two fluids occupying the pore space.

- `Phantom-Elasticity` (only vtk): Part of the stress components (requested by the keyword 'S') contributed by the "phantom elasticity" model, written as the symmetric tensor `Stress-PhEl` (components as for `S`) \[F/A\]. Only for materials where "*Phantom elasticity" was defined.

- `Sets` (only vtk): Write the defined element sets to the output file as the cell data `elset` with one component per element set; the component names are the set names (in upper case). The elements of a set have the value 1 in its component, all other elements the value 0.

- `shell-n11`, `shell-n22`, `shell-n12`, `shell-m11`, `shell-m22`, `shell-m12`, `shell-q13`, `shell-q23`, `shell-mises-top`, `shell-mises-bot`: Stress resultants (membrane forces, bending moments, transverse shear forces) and von Mises stresses at the top and bottom surface of [shell elements](../element/elements-shell.md#output). Zero for all other elements.

- `shell-axes` (only vtk, only `*Element output`): Output axes of the [shell elements](../element/elements-shell.md#orientation-and-output-axes), to which the stress resultants refer, as the cell vectors `Shell axis 1`, `Shell axis 2` and `Shell normal`.

- `SF` (only vtk, only `*Element output`): Stress resultants along all active [beam](../element/elements-beam.md) and [truss](../element/elements-u-truss.md) elements, embedded elements included, as the dataset `<job>-sections-<step>-<frame>.vtu` (block **Section forces** of the multiblock output). Every element has five equally spaced stations with points of its own, so jumps at the nodes are preserved. Point data: `N` (tension positive), `Qy`, `Qz`, `Mx`, `My`, `Mz`, the local axes `Axis2` and `Axis3` and the number `Station`; cell data: `ElementLabel` and `MaterialID`. Trusses give `N` only; with the option `tension-only` or a tensile strength the values at the stations are limited to the range of the integration point values. The ParaView filter **numgeo Diagram** draws the diagrams. A step with an `*Output, field` of its own writes the block only if its list contains `SF`; it is not taken over from earlier steps.

- `IP` (only vtk, only `*Element output`): Writes all variables of the element output of the step also at the integration points, as if they were listed under [`*Integration point`](#integration-point-output).

- `Mat` (only vtk): Write the material assignment as cell data to the output file: one integer array `Mat:<material name>` per material (material name in upper case). The elements with this material are given the value 1, all other elements the value 0.

Depending on the applied element type and material model, the label `SVARS` can be replaced by the name of the demanded output variable solemnly available for this specific element type/material model.
Possible output variables for different material models can be found under [*Material](../material/index.md). For user-defined materials (`*Mechanical = user`) the state variable number has to be specified directly, e.g. `sdv1` or `sdv20`.

## Integration point output

```numgeo 
*Output, field, vtk, <format 2>
*Integration point
<variable 1>, ..., <variable n>
```

This sub-keyword writes the listed variables at the integration points of all active elements, as the elements hold them: neither averaged nor extrapolated. The values are written as the dataset `<job>-ip-<step>-<frame>.vtu` (block **Integration points** of the multiblock output) with one point per integration point at its coordinates. Point data are `IntegrationPoint` (number of the integration point within the element) and the requested variables; cell data are `ElementLabel` and `MaterialID`. The output is available for vtk only; with GiD, `*Integration point` is not used (warning) since the GiD element output is given at the integration points.

`*Integration point` has no options: like all field output it covers the whole model. Use [`*Integration point, elset=...`](print.md#integration-point-output) of the print output for the values of an element set in a text file.

The following variables are available:

- `S`: Stress, symmetric tensor `Stress` (components and effective stress as for the element output).

- `E`: Strain, symmetric tensor `Strain` (shear components as engineering shear strains $2\varepsilon_{ij}$).

- `void`: Void ratio, scalar `Void ratio`.

- Element variables (e.g. `stress-truss`, `interface-shear`, `shell-n11`, `TEMP_IP`) and state variables of the materials (e.g. `sdv1` of a user material), as listed for the element output. The array names are the variable names in lower case.

`S` and `E` are written for continuum elements only; the stresses of truss, beam and shell elements refer to the axes of the element and are given by their element variables and by `SF`. A point has the value zero if its element does not have a variable. If no active element of the step has a requested variable, numgeo writes a warning in the first frame of the step. The variables `IP`, `SF`, `Mat`, `Sets`, `Embedded`, `shell-axes`, `contact`, `contact_sdv`, `contact_diagnostic`, `delta-t`, `delta-pw`, `F`, `strain-hencky`, `Phantom-elasticity` and `Phantom-viscosity` are not available at the integration points and stop the analysis with an error.

Elements which do not provide the coordinates of their integration points (pressure elements) are not part of the dataset, and the first frame of a restart analysis has no integration point dataset. A step without `*Output, field` continues the field output of the previous step, `*Integration point` included. The dataset contains all integration points in every written frame; on large models request it for selected steps or with a larger `*Frequency`.

```numgeo 
*Output, field, vtk, binary
*Frequency = 1
*Node output
U
*Element output
S, E
*Integration point
S, E, void
```

In ParaView, select the block **Integration points** with **Extract Block** and show it with the representation **Point Gaussian**; **Plot Selection Over Time** follows a selected integration point through the analysis.
