# Shell elements

<p align="center" markdown>
  <img src="./assets/shells.png" width="95%"/><br>
  <em>Node numbering (filled: corner nodes, open: mid-side nodes), integration points (crosses) and normal n of the shell elements.</em>
</p>

Shell elements model thin-walled structures whose thickness is small compared with their other dimensions: pile walls (monopiles, open-ended steel piles), sheet pile walls, caissons, slabs and tanks. They carry membrane forces, bending moments and transverse shear forces. The implemented elements are Reissner-Mindlin shells (shear-deformable, thick and thin shells) with mixed interpolation of the strain components (MITC), which makes them free of shear locking and, for the quadratic elements, of membrane locking. Details on the formulation are given in the [Theory Manual](../../theory/elements/shell.md), the verification in the [Benchmark Manual](../../benchmark/shell/shell-plates.md). Three tutorials show the application: a [cylindrical tank under internal pressure](../../tutorial/shells/tank-internal-pressure.md), a [raft foundation on an elastic subsoil](../../tutorial/shells/raft-foundation.md) and the [construction stages and load cases of a raft foundation](../../tutorial/shells/raft-construction-stages.md).


!!! note "Shell degrees of freedom"

    Every shell node has three translations `u1`, `u2`, `u3` and three rotations `r1`, `r2`, `r3` about the global axes. Boundary conditions have to restrain the relevant rotations as well (clamped edge: all six degrees of freedom, symmetry plane: the displacement normal to the plane and the two rotations about the axes lying in the plane). The rotation about the shell normal (*drilling rotation*) has a small stiffness of its own, so flat shells need no additional restraints.

    A node may be shared by shell elements and continuum elements with displacement degrees of freedom only (e.g. `u8-solid-3D`, `u20-solid`). The node then has the six degrees of freedom of the shell; the continuum elements act on its translations only, so such a connection transfers forces but no moments (hinge). Nodes shared with elements whose degrees of freedom do not match (e.g. the pore-water pressure of `u8p8-sat-3D`) are refused with an error message.

## 3D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** | **nIP\*** | **Formulation** |
|---|---|---|---|---|---|---|
|``u3-shell`` | 3D | triangular  | 3 | linear    | 3 | flat facet, MITC3 |
|``u4-shell`` | 3D | rectangular | 4 | linear    | 4 | flat facet, MITC4 |
|``u6-shell`` | 3D | triangular  | 6 | quadratic | 3 | curved, MITC6 |
|``u8-shell`` | 3D | rectangular | 8 | quadratic | 9 | curved, MITC9 with condensed centre node |

\*  nIP = number of integration points for output and for the coupling of [embedded shells](../embedded-regions/interaction-surface-plate.md)

The shell elements are available in three-dimensional models only. The linear elements are flat: a curved surface is approximated by facets (warped `u4-shell` elements are projected on their mean plane). The quadratic elements follow a curved surface with their mid-side nodes; the node numbering is that of the faces of the quadratic solid elements, so that a `u8-shell` fits to a face of a `u20-solid` and a `u6-shell` to a face of a `u10-solid-3D`.

Which element to use:

* `u8-shell` is the most accurate element and the recommended choice, in particular for curved shells and whenever bending moments and stresses are evaluated.
* `u4-shell` is robust and inexpensive; curved shells require finer meshes (16 to 32 elements around the circumference of a pile).
* `u6-shell` is a good triangular element for irregular meshes.
* `u3-shell` should only be used to fill in meshes of `u4-shell` elements. It is stiff on coarse meshes of curved shells and of very thin plates, and its membrane forces converge slowly.

## Orientation and output axes

The normal $\boldsymbol n$ of an element follows from its node numbering by the right-hand rule (counter-clockwise numbering seen from the tip of the normal, see the figure above). The side into which the normal points is the *top* side of the shell, the other one the *bottom* side. The thickness is distributed symmetrically about the surface defined by the nodes (mid-surface).

The stress resultants refer to the *output axes* 1, 2 and 3 of the element:

* axis 3 is the normal $\boldsymbol n$,
* axis 1 is the projection of the global $z$-axis on the shell surface. If the normal is parallel to the global $z$-axis within 2.5° (horizontal plates), the global $x$-axis is projected instead,
* axis 2 $=\boldsymbol n\times$ axis 1.

For a vertical pile or wall, axis 1 is therefore the vertical (axial) direction and axis 2 the horizontal (circumferential) direction, independent of the node numbering of the individual elements. For a horizontal slab, axis 1 is the global $x$-direction. The axes are evaluated at every integration point of the curved elements and once per flat element; they can be written to the field output with the variable `shell-axes`.

## Loads

* **Concentrated forces and moments** at the shell nodes: [`*Cload`](../boundary-conditions/cload.md) with the labels `x`, `y`, `z` (forces) and `mx`, `my`, `mz` (moments about the global axes).
* **Distributed loads** per unit area of the mid-surface: [`*Dload`](../boundary-conditions/dload.md#shell-elements) with the label `p` (pressure normal to the mid-surface, positive along the normal $\boldsymbol n$) or `x`, `y`, `z` (traction in a global direction). A load pressing on the top side of the shell is a negative pressure.
* **Surface loads** on the faces `F1` (side of the normal $\boldsymbol n$) and `F2` (opposite side) of an element-based surface: [`*Dsload`](../boundary-conditions/dsload.md#shell-elements) with the labels `P` (pressure, positive along the outward normal of the face) and `X`, `Y`, `Z`. A load pressing on a face is a negative pressure.
* **Body forces**: [`*Body force`](../boundary-conditions/body-force.md) together with the density (see below).

Contact pairs cannot be defined on surfaces of shell elements. The loads are verified in the benchmark [Shell elements: loads](../../benchmark/shell/shell-loads.md).

Like all loads, the loads of shell elements act only in the step in which they are defined, see [Loads in a sequence of steps](../boundary-conditions/index.md#loads-in-a-sequence-of-steps).

## Construction stages, reset and restart

Shell elements are linear elastic and have no strain or stress state of their own: their strains follow from the degrees of freedom relative to a *stress-free reference state* of the element. The reference state is the initial configuration unless it is changed by one of the following options:

* **`*Model change, add`** ([element activation](../model-change/elements.md)): an element that has never been active is activated strain-free and stress-free in the current position of its nodes, e.g. a raft cast on a soil which has already settled or a wall installed after an excavation stage. It carries only the loads applied after its activation.
* **`*Model change, remove`**: a removed element is not evaluated; its loads (`*Dload`, `*Dsload`, body force) are ignored. The nodal forces it exerted on the remaining model are ramped down over the step. If it is activated again later, it comes back with the deformation (and therefore with the stress resultants) it had at the removal, like the continuum elements keep their stress.
* **`*Reset, Displacement`** ([reset](../reset.md)): the displacements start again from zero, the shell elements keep their deformation and stress resultants.
* **Restart** ([`*Restart write` / `*Restart read`](../restart.md)): the reference state is part of the restart files.

The verification is given in the benchmark [Shell elements: loads in a sequence of steps and construction stages](../../benchmark/shell/shell-stages.md). [Beam](elements-beam.md#construction-stages-reset-and-restart) and [truss elements](elements-u-truss.md#construction-stages-reset-and-restart) behave in the same way. The equilibrium of the moments at the shell nodes is checked in a convergence field of its own, see [`*Controls, r`](../controls.md).

!!! note "Changing the section properties"

    `*Model change, material` assigns a new `*Shell properties` definition to shell elements. Since the elements are elastic, the new stiffness acts on the complete deformation relative to the reference state (secant stiffness, as in the effective modulus method of creep analyses), not only on the deformation of the following steps.

## Notes on density and body forces

If a material density is specified with `*Density`, it is used for the consistent mass matrix (translational inertia $\rho t$, rotary inertia $\rho t^3/12$) and, if body forces are active, for the body force per unit area $\rho\,t\,g$ acting in the direction of the body force. A uniform load per unit area $q$ in a fixed direction can also be applied in this way by choosing density and body force magnitude such that $\rho\,t\,g=q$; `*Dload` gives the same load without changing the mass of a dynamic analysis.

## Output

The following variables are available for shell elements in the [field output](../output/field.md) (`*Node output`: nodal values extrapolated from the integration points, `*Element output`: element mean values) and in the [print output](../output/print.md) (`*Element` and `*Integration point`):

| Variable | Description | Unit |
|---|---|---|
| `shell-n11`, `shell-n22`, `shell-n12` | membrane forces $N_{11}$, $N_{22}$, $N_{12}$ in the output axes, positive in tension | F/L |
| `shell-m11`, `shell-m22`, `shell-m12` | bending and twisting moments $M_{11}$, $M_{22}$, $M_{12}$. $M_{11}$ is the moment of the stresses $\sigma_{11}$: a positive $M_{11}$ causes tension in direction 1 on the top side | F·L/L |
| `shell-q13`, `shell-q23` | transverse shear forces $Q_{13}$, $Q_{23}$ | F/L |
| `shell-mises-top`, `shell-mises-bot` | von Mises stress at the top and at the bottom surface of a homogeneous wall, from $\sigma_{\alpha\beta}=N_{\alpha\beta}/t\pm6M_{\alpha\beta}/t^2$ | F/L² |
| `shell-axes` | output axes as cell vectors `Shell axis 1`, `Shell axis 2` and `Shell normal` (field output, `*Element output` only) | -- |
| `S` | membrane stress tensor $N_{\alpha\beta}/t$ and mean transverse shear stress $Q_{\alpha3}/t$ in global components | F/L² |
| `E` | membrane strain tensor and transverse shear strain of the mid-surface in global components | -- |

Node variables of the shell nodes ([field output](../output/field.md#node-output) and print output):

| Variable | Description |
|---|---|
| `U` | displacements |
| `UR` | rotations about the global axes (VTK name `Rotation`; print output columns `UR1`, `UR2`, `UR3`) |
| `RF`, `RM` | reaction forces and reaction moments at nodes with boundary conditions (VTK name `Reaction moment`; print output columns `RM1`, `RM2`, `RM3`) |

Example of an output request for a pile wall:

```numgeo
*Output, field, vtk, binary
*Node output
u, ur, rf, rm
*Element output
shell-n11, shell-n22, shell-n12, shell-m11, shell-m22, shell-mises-top, shell-mises-bot, shell-axes
*Output, print
*Integration point, elset=pile
coords_igp, shell-n11, shell-m22
```

!!! note "Accuracy of the stress resultants"

    Membrane forces and bending moments of the `u8-shell` converge with the square of the element size, those of the other elements linearly (see the [benchmarks](../../benchmark/shell/shell-plates.md#clamped-circular-plate)). The transverse shear forces `shell-q13` and `shell-q23` are evaluated from the assumed transverse shear strains. In thin shells these strains are very small compared with the bending strains, and the shear forces of the `u3-shell`, `u6-shell` and `u8-shell` become inaccurate if the elements are much larger than the wall thickness. Displacements, membrane forces and bending moments are not affected.

!!! warning "Limitations"

    - The shell elements are geometrically linear (small displacements and rotations) and linear elastic with a homogeneous wall.
    - Three-dimensional models only. Contact pairs cannot be defined on surfaces of shell elements.
    - No explicit time integration: steps with [`*Explicit dynamic`](../step/explicit-dynamic.md) are refused for shell elements (they can be part of an instance with implicit time integration). Use [`*Dynamic`](../step/dynamic.md).
    - The offset of the wall thickness is not considered where shells are connected to or embedded in continuum elements: the interaction acts on the mid-surface.
