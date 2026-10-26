# Beam elements

<p align="center">
  <img src="./assets/beams.png" width=40%/><br>
</p>

Beam elements are structural members capable of resisting axial forces, shear forces and bending moments. They model slender structural elements where one dimension is significantly larger than the other two. The currently implemented beam elements use a Timoshenko beam formulation and therefore account for both bending and shear deformation. Details on the implementation are provided in the [Theory Manual](../../theory/elements/beam.md).

The properties of beam elements are assigned using the `*Material` keyword in combination with the `*Beam properties` sub-keyword. See the [Reference Manual](../material/beam-properties.md) for more information.

If a material density is specified using `*Density`, it is used for the consistent beam mass matrix. If body forces are active, the same density is also used to generate the equivalent distributed beam load. Without `*Density`, no density-based inertia or self-weight contribution is generated.

!!! note "Beam degrees of freedom"

    Beam nodes have translational and rotational degrees of freedom. In 2D, each beam node has `u1`, `u2` and `r3`. In 3D, each beam node has `u1`, `u2`, `u3`, `r1`, `r2` and `r3`. Boundary conditions therefore need to restrain the relevant rotational degrees of freedom as well; otherwise rigid-body mechanisms may remain. Concentrated moments about the global axes are applied with [`*Cload`](../boundary-conditions/cload.md) and the labels `mx`, `my`, `mz` (2D: `mz` only).

## 2D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** |
|---|---|---|---|---|---|
|``u2-beam``           | 2D            | beam       | 2              | linear      | 1  |
|``u3-beam``           | 2D            | beam       | 3              | quadratic   | 3  |

\*  nIP = number of integration points

For 2D beam elements, the active nodal degrees of freedom are `u1`, `u2` and `r3`. The relevant local beam resultants are the normal force $N$, the local shear force $Q_y$ and the bending moment $M_z$.

## 3D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** |
|---|---|---|---|---|---|
|``u2-beam-3D``           | 3D            | beam       | 2              | linear      | 1  |
|``u3-beam-3D``           | 3D            | beam       | 3              | quadratic   | 3  |

\*  nIP = number of integration points

For 3D beam elements, the active nodal degrees of freedom are `u1`, `u2`, `u3`, `r1`, `r2` and `r3`. The local $x$-axis is aligned with the beam axis. The local $y$- and $z$-axes are generated internally from the element orientation. For non-circular or otherwise direction-dependent cross-sections, the orientation of $I_{yy}$, $I_{zz}$, $\kappa_y$ and $\kappa_z$ therefore has to be considered carefully.

## Notes on the 3-node elements

The 3-node elements `u3-beam` and `u3-beam-3D` interpolate the displacements and rotations quadratically; with the middle node off the straight line between the end nodes they follow a curved beam axis (e.g. a tunnel lining). The transverse shear strains and the axial strain are *assumed strains*: they are evaluated at the two points $\xi=\pm1/\sqrt{3}$ of the element and interpolated linearly in between (see the [Theory Manual](../../theory/elements/beam.md#assumed-strains)). This avoids shear locking of slender beams and membrane locking of curved beams. A straight cantilever with a tip load is reproduced exactly with one element, a quarter circle with four elements to 0.01 %, see the benchmarks [Cantilever Beam (slender)](../../benchmark/beam/cantilever-beam-slender.md) and [Curved Cantilever Beam (quarter circle)](../../benchmark/beam/curved-cantilever-beam.md).

## Construction stages, reset and restart

Beam elements are linear elastic and have no strain or stress state of their own: their strains follow from the degrees of freedom relative to a *stress-free reference state* of the element. The reference state is the initial configuration unless it is changed by one of the following options:

* **`*Model change, add`** ([element activation](../model-change/elements.md)): an element that has never been active is activated strain-free and stress-free in the current position of its nodes, e.g. a strut or a lining installed after an excavation stage. It carries only the loads applied after its activation.
* **`*Model change, remove`**: a removed element is not evaluated. The nodal forces it exerted on the remaining model are ramped down over the step. If it is activated again later, it comes back with the deformation (and therefore with the forces and moments) it had at the removal, like the continuum elements keep their stress.
* **`*Reset, Displacement`** ([reset](../reset.md)): the displacements start again from zero, the beam elements keep their deformation, forces and moments.
* **Restart** ([`*Restart write` / `*Restart read`](../restart.md)): the reference state is part of the restart files. Restart files written by earlier versions can be read.

`*Model change, material` assigns new `*Beam properties`; since the elements are elastic, the new stiffness acts on the complete deformation relative to the reference state.

The equilibrium of the moments at the beam nodes is checked in a convergence field of its own, see [`*Controls, r`](../controls.md).

## Notes on density and body forces

The density defined by `*Density` is interpreted as mass density. For beam elements it contributes to:

* the translational inertia through $\rho A$,
* the rotary inertia through $\rho I_{yy}$ and $\rho I_{zz}$,
* the torsional rotary inertia in 3D through $\rho(I_{yy}+I_{zz})$,
* the equivalent density-based body-force vector if body forces are active.

For body-force loading, the distributed line load is formed from the material density, the cross-sectional area and the prescribed body-force direction/magnitude. The resulting external load is assembled consistently with the beam interpolation. In the 2-node formulation, the equivalent nodal force vector includes the corresponding fixed-end moment terms for constant transverse line loads. In the 3-node formulation, the equivalent load vector is integrated over the beam axis using the element shape functions.

## Notes on output

For beam elements, $\sigma_{11}$ is the axial stress and $\sigma_{12}$ and $\sigma_{13}$ correspond to the shear stresses in local $xy$- and $xz$-direction, respectively. All other components are zero.

Similarly, $\varepsilon_{11}$ is the axial strain and $\varepsilon_{12}$ and $\varepsilon_{13}$ correspond to the shear strains in local $xy$- and $xz$-direction, respectively.

In addition to general output in Cartesian coordinates such as displacements, stress and strain, local quantities can be requested:

* `Beam-Force-N`: normal force along the beam axis in F
* `Beam-Force-Qy`: shear force in local $y$-direction in F
* `Beam-Force-Qz`: shear force in local $z$-direction in F
* `Beam-Moment-Mz`: bending moment around the local $z$-axis in F·L
* `Beam-Moment-My`: bending moment around the local $y$-axis in F·L

In 2D, only `Beam-Force-N`, `Beam-Force-Qy` and `Beam-Moment-Mz` are relevant. In 3D, `Beam-Force-Qz` and `Beam-Moment-My` are available in addition.

Beam elements which are embedded with [`*Embedded region, interaction`](../embedded-regions/interaction.md#output) also provide the state of their interface: `interface-shear`, `interface-disp`, `interface-slip` and `interface-cap`.

Forces and moments are calculated at the integration points. The 2-node elements have one integration point in the centre of the element: normal force and shear force are constant along the element, the bending moment is that of the centre. The 3-node elements have three integration points. The element output is the mean of the integration points. For output at the nodes ([`*Output, field`](../output/field.md#node-output)) the values are extrapolated to the nodes of each element and averaged over the line elements (truss and beam elements) which share the node, weighted with their length.

See the [Theory Manual](../../theory/elements/beam.md#7-output-of-forces-and-moments) for information about the calculation of forces and bending moments.
