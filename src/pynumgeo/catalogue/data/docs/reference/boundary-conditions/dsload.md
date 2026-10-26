# Distributed surface loads

```numgeo 
*Dsload, <option>
<surface name>, <load label>, <Load magnitude>
```

This option defines a distributed surface load acting on the surface with the name `<surface name>` with a defined load magnitude.

Heat flux and film exchange on u-T solids are defined using [`HFi` under `*Dload`](dload.md#heat-flux) and [`FILMi` under `*Dload`](dload.md#film-condition); these heat-load labels are not available for `*Dsload`.

!!! note "Shell elements"

    Surfaces can contain the faces `F1` and `F2` of shell elements. The labels `P`, `X`, `Y` and `Z` are available for them, see [Shell elements](#shell-elements).

- `<option>`: Specify how the load should be applied. The load can either be applied:

    - instantaneously (without any temporal delay) using `<option> = instant`

    - linearly increasing with step time (0% of the prescribed magnitude are applied at the beginning of the step and 100% at the end of the step time) using `<option> = ramp`

    - using a user defined amplitude defined prior to the step definition using `<option> = Amplitude = <amplitude name>`

    - user-defined load using `<option> = user`. The user has to supply the `user_load.o` file (see [user loads](../user/load.md)). The definition of a `<Load magnitude>` is not required in this case. 

    - `side=1` or `side=2` may be added to the option (`*Dsload, instant, side=2`): in a model with an [embedded shell](../embedded-regions/interaction-surface-plate.md) (`host=split`) the load then acts on the host elements cut by the shell only if they belong to that side of the shell (1: side of face 1, the + side; 2: the opposite side, face 2). Elements which are not cut receive the load in any case. See [Faces of elements cut by an embedded shell](#faces-of-elements-cut-by-an-embedded-shell).
        
!!! note "Loads in a sequence of steps"

    The load acts only in the step in which it is defined; `ramp` starts from zero at the beginning of every step. A load which is to remain active has to be defined again in the following steps (usually with `instant`), see [Loads in a sequence of steps](./index.md#loads-in-a-sequence-of-steps).

- `<surface name>`: Surface name to which the load should be applied.

- `<Load label>`: Load label defining the type of load and the direction of action of the external distributed load. Currently available are:

     |**Load type**                         |
     |-----------------------------------|
     |[Uniform pressure](#uniform-pressure) |
     |[Tangential traction](#tangential-traction) |
     |[Traction in global direction](#traction-in-global-direction) |
     |[Water weight](#water-weight) |
     |[Springs](#springs) |
     |[Compliant base boundary condition](#compliant-base-boundary-condition) |
     |[Drainage condition (seepage)](#drainage-seepage-condition)|
     |[Inflow/Outflow](#inflowoutflow)|
     |[Shell elements: faces F1 and F2](#shell-elements)|
     |[Faces of elements cut by an embedded shell](#faces-of-elements-cut-by-an-embedded-shell)|

------

## Uniform pressure

Distributed load acting perpendicular to the surface face.

```numgeo 
*Dsload, <option>
<surface name>, P, <Magnitude>
```

Positive values for `Pi` act along the outward face normal (mechanical sign convention, tension is positive).

------

## Tangential traction

Distributed load acting tangential to the surface face.

```numgeo 
*Dsload, <option>
<surface name>, T, <Magnitude>
```

!!! Note 

    This is only valid for 2D simulations, since the tangential direction is only unique in 2D.

------

## Traction in global direction

Distributed load acting in global coordinate direction `<Global direction {X,Y,Z}>` on the surface face.

```numgeo 
*Dsload, <option>
<surface name>, <Global direction {X,Y,Z}>, <Magnitude>
```

------

## Water weight

Distributed load acting perpendicular to the surface face compensating(positive) pore-water pressure by its deadweight (e.g. to simulate the flooding of slopes):

```numgeo 
*Dsload, <option>
<surface name>, SWP
```

The magnitude of the load is calculated such that the (only positive) more water pressure acting on the surface is compensated.

------

## Springs

Distributed surface load which corresponds to a support of the surface `<surface name>` (or, for beam elements, the edge set running along the beam) by a plurality of spring elements acting between the model and a fixed, immovable ground ("Winkler-type" elastic foundation).

Four families of ground springs are available, chosen via `<spring type>`:

| `<spring type>` | Direction of action | Compatible elements |
|---|---|---|
| [`spring-ground-n`](#normal-and-tangential-springs) | normal to the element edge | 2D solid elements only (triangular/rectangular, incl. axisymmetric) |
| [`spring-ground-t`](#normal-and-tangential-springs) | tangential to the element edge | 2D solid elements only (triangular/rectangular, incl. axisymmetric) |
| [`spring-ground-(x,y,z)`](#global-direction-springs) | fixed global coordinate direction | beam elements and 3D solid elements only (tetrahedral/hexahedral) |
| [`spring-ground-(x,y,z)-tabular`](#nonlinear-tabular-springs) | fixed global coordinate direction, nonlinear $F$-$u$ law | beam elements and 3D solid elements only (tetrahedral/hexahedral) |

!!! warning "No N/T equivalent for beams/3D, no X/Y/Z equivalent for 2D solids"

    There is no `spring-ground-n`/`-T` for beam or 3D solid elements, and no `spring-ground-x`/`-Y`/`-Z` for 2D solid elements. Assigning a spring to a surface of an incompatible element type aborts with an error at assembly. More springs will be available in the future.

All four families additionally support the [relative displacement (installation) formulation](#relative-displacement-installation-formulation) described below, and — like every `Dsload` — the `<option>` mechanism described at the top of this page (`instant`, `ramp`, `Amplitude=...`, `user`; the last requires the `user_load.o` file, see [user loads](../user/load.md)), except where noted for tabular springs.

------

### Linear springs

```numgeo 
*Dsload, <option>
<surface name>, spring-ground-n, <k> [, <formulation>]
<surface name>, spring-ground-t, <k> [, <formulation>]
<surface name>, spring-ground-x, <k> [, <formulation>]
<surface name>, spring-ground-y, <k> [, <formulation>]
<surface name>, spring-ground-z, <k> [, <formulation>]
```

The nodal spring force is obtained by numerical integration of $f = k(\boldsymbol{u}-\boldsymbol{u}_{ref})$ over the element edge/face/beam-length, projected onto the spring's direction of action (see below). `<k>` is the constant spring stiffness; `<formulation>` is the optional 'relative'/`total` keyword described [below](#relative-displacement-installation-formulation) (default `total`, omit for the previous, backwards-compatible behaviour).

!!! danger "Units of `<k>` depend on the element type"

    `<k>` is **not** a discrete spring stiffness — it is a stiffness *density* that gets integrated over the element, so its unit depends on what is being integrated over:

    | Springs on... | integrated over | unit of `<k>` |
    |---|---|---|
    | 2D solid edges (`N`, `T`) | an edge length (unit out-of-plane thickness) | force/length³, e.g. kN/m³ |
    | 3D solid faces (`X`, `Y`, `Z`) | a face area | force/length³, e.g. kN/m³ |
    | beam elements (`X`, `Y`, `Z`) | the beam length | force/length², e.g. kN/m² |

    The 2D and 3D cases match the classical subgrade-reaction modulus $k_s$; beam springs are one length dimension "shorter" since they are only integrated along a line, not over an area. Getting this wrong by a factor of the tributary length/area is the most common spring-modelling error - verify a single-element patch test against $f = k\cdot A \cdot u$ (solid faces) or $f=k\cdot L \cdot u$ (beams) before trusting the value in a full model. See the [Benchmark section](../../benchmark/springs/spring-ground-n.md) for worked examples.

------

### Normal and tangential springs

`spring-ground-n` acts perpendicular (in normal direction) to the surface; `spring-ground-t` acts tangential to the surface. Both are only available on 2D solid element edges (triangular/rectangular, including axisymmetric elements, where the usual $2\pi r$ integration factor is applied automatically).

!!! info "Where do springs attach"

    Springs that are defined as distributed surface loads (`DSloads`) attach at the integration points of the element edges/faces forming the surface to which they are assigned to. The resulting nodal forces are obtained by means of numerical integration. 

    <p align="center" markdown>
        <img src="./assets/dsload-spring.png" width=100%/><br>
        <em> Figure 1: Examples of springs assigned to surfaces using the `DSload` keyword. </em>
    </p>

!!! note "Reference configuration only"

    The direction of action of `N`/`T` springs is evaluated once from the reference (undeformed) configuration and does not rotate with the deformation, even in an `NLGEOM` step — there is currently no follower-direction (large-rotation) formulation for 2D ground springs.

------

### Global direction springs

`spring-ground-x`, `spring-ground-y` and `spring-ground-z` act along the corresponding **fixed global coordinate axis**, regardless of the orientation of the beam or 3D element face the spring is assigned to — e.g. an inclined raker beam supported by `spring-ground-y` is always resisted vertically, not perpendicular to its own axis. Only available on beam elements and 3D (tetrahedral/hexahedral) solid element faces.

!!! note "Follower area (NLGEOM), 3D solid faces only"

    For springs on 3D solid faces, an `NLGEOM` step activates a geometric (follower-area) stiffness contribution accounting for the change of the tributary face area with deformation — the direction of action itself remains fixed in space, since it is a global-direction spring by definition; only the *area* it is integrated over follows the deformation. Beam elements do not currently support a follower-length update under `NLGEOM` (the beam's reference-configuration length is used regardless of the `NLGEOM` step setting).

------

### Nonlinear (tabular) springs

Appending `-tabular` to a global-direction spring label replaces the constant stiffness `<k>` by a nonlinear force-displacement law read from a plain-text data file:

```numgeo 
*Dsload, <option>
<surface name>, spring-ground-x-tabular, <filename> [, <formulation>]
<surface name>, spring-ground-y-tabular, <filename> [, <formulation>]
<surface name>, spring-ground-z-tabular, <filename> [, <formulation>]
```

`<filename>` points to a two-column text file of $(u,F)$ pairs, sorted by ascending $u$, defining a piecewise-linear force-displacement curve — see [Figure 2](#fig-tabular) below.

At every Newton iteration, the current (relative) displacement is looked up in the table; both the interpolated force and the local secant slope of the active table segment are used directly as the spring force and its consistent tangent stiffness, respectively. No additional linearisation step is required, and full quadratic Newton convergence is retained even through table segments of very different local stiffness (e.g. a near-flat, fully mobilised plateau).

<p align="center" markdown id="fig-tabular">
    <img src="./assets/dsload-spring-beam.png" width=100%/><br>
    <em> Figure 2: Tabular (nonlinear) spring assigned to a beam by means of a `SPRING-GROUND-*-tabular` load, reading a force-displacement curve from a text file. Note: the label shown in this figure, <code>spring-n-Fu</code>, reflects an earlier, pre-release naming convention; the current keyword for the case depicted (a beam supported by a nonlinear tabular spring) is <code>spring-ground-y-tabular</code> (or <code>-X</code>/<code>-Z</code>, depending on the direction of action), as described in this section. </em>
</p>

!!! danger "Units of the table's force column depend on the element type - same rule as `<k>` above"

    The force column of the table is not a discrete force; like `<k>` for linear springs, it is a force *density* that is integrated over the element:

    - beam elements: force **per unit beam length**, e.g. kN/m
    - 3D solid faces: force **per unit face area** (a traction), e.g. kN/m²

    The example table in Figure 2 (`F` in kN) is illustrative; for a beam it should be read as kN/m.

!!! warning "`<option>` (RAMP/INSTANT/AMPLITUDE) has no effect on tabular springs"

    Unlike constant-stiffness springs, the tabular force-displacement law is evaluated directly against the (relative) displacement at every iteration — the loading path is governed entirely by the structure's own displacement history, exactly like a real nonlinear spring, not by an externally imposed amplitude. `<option>` remains mandatory input syntactically but has no bearing on the result for tabular springs.

!!! note "N/T springs have no tabular variant"

    There is currently no `spring-ground-n-tabular`/`spring-ground-t-tabular` — nonlinear springs are only available for the global-direction family, i.e. on beam elements or 3D solid faces.

------

### Relative displacement (installation) formulation

By default, ground springs act on the **total** displacement of the model, $f = k\,\boldsymbol{u}$: the spring is force-free only when $\boldsymbol{u}=\boldsymbol{0}$, i.e. at the very start of the analysis. This is inconvenient for springs that represent a support **installed at some point during the analysis** — a strut installed only after an excavation step has already deflected a wall, for instance — since such a spring would otherwise immediately register a large, unphysical force corresponding to the deflection that had already occurred *before* it was installed.

An optional `<formulation>` keyword, appended as the last entry on the data line, selects between the two available formulations:

```numgeo 
*Dsload, <option>
<surface name>, <spring type>, <k or filename>, relative
<surface name>, <spring type>, <k or filename>, total
```

- `total` (default — omitting `<formulation>` entirely is equivalent and remains backwards compatible): $f = k\,(\boldsymbol{u}-\boldsymbol{u}_{ref})$ with $\boldsymbol{u}_{ref}\equiv\boldsymbol{0}$ for the whole analysis.

- 'relative': the spring is installed **strain-free**. Upon the first assembly of the step in which the load is (re-)declared, numgeo captures the converged displacement field at that instant — i.e. the state at the end of the *previous* step — as the reference field $\boldsymbol{u}_{ref}$; from then on the spring acts on $\boldsymbol{u}-\boldsymbol{u}_{ref}$. Redeclaring the *same* spring (same surface and load label) in the following step **inherits** $\boldsymbol{u}_{ref}$ rather than capturing it anew, so the spring keeps its original installation state across step boundaries instead of being reset force-free at the start of every step it is redeclared in.

!!! example "Strut installed after excavation"

    ```numgeo 
    ** step 2: excavate; strut not yet present
    ** (no *Dsload entry for the strut surface in this step)
    *Step
    ...
    ** step 3: install the strut, force-free at the (already deflected) wall position
    *Dsload
    strut_surface, spring-ground-n, 1.5e5, relative
    ```

!!! warning "Remeshing"

    'relative' springs store a snapshot of the global displacement field at activation. This is currently incompatible with a change of mesh topology (e.g. PFEM remeshing) occurring between the step in which the reference state was captured and any later step in which it is used; numgeo aborts with a descriptive error if the size of the stored reference field no longer matches the current global solution vector, rather than silently producing incorrect results.

See the [Benchmark section](../../benchmark/springs/spring-ground-n.md) for a worked example demonstrating strain-free activation.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../theory/external-loads/ground-springs.md)
</div>

------

## Compliant base boundary condition

The compliant base boundary condition is used to impose a seismic signal at the bottom of the FE model and at the same time damping downwards propagating waves by applying equivalent viscous forces. The distributed force acts in global direction `Dir` to the element faces of surface `<surface name>` to which the force is applied.

```numgeo 
*Dsload, <option>
<surface name>, <compliant type>, <Dir>, <magnitude>
```

The `<Magnitude>` is defined as $\rho \cdot c_{p,s}$ of the underlying material, where $\rho$ is the density and $c_{p,s}$ is the wave speed ($c_s$ for shear waves and $c_p$ for compression waves) The subsequent line then reads:

Two types of springs are implemented, which can be chosen by setting
`<compliant type>` to:

- `compliant`: This corresponds to the "implicit" implementation, where the current velocity $v$ is used to calculate the viscous stress

- `compliant0`: This corresponds to the "explicit" implementation, where the velocity $v_0$ from the previous (converged) time step is used to calculate the viscous stress.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../theory/external-loads/compliant-base-bc.md)
</div>

------

## Drainage (seepage) condition

A special boundary condition is needed if the phreatic surface reaches an open, freely draining surface. In such a case the pore fluid can drain freely down the face of the dam, so at all points on this surface below its intersection with the phreatic surface. Above this point negative pore water pressures occur, with their particular value depending on the solution. This drainage-only flow condition consists of prescribing the flow velocity on the freely draining surface in a way that approximately satisfies the requirement of on the completely saturated portion of this surface.

```numgeo 
*Dsload, <option>
<surface name>, drainage-w, <magnitude>
```

The `<magnitude>` can be approximated as $s_k \dfrac{k^{sat}}{\gamma_w}$

Where $s_k$ is a scaling factor usually in the range of $10^3 \leq s_k \leq 10^4$, $k^{sat}$ is the saturated hydraulic conductivity and $\gamma_w$ is the unit weight of water. numgeo divides the `<magnitude>` by the characteristic element size $c$ of the underlying finite element, which is determined automatically from the area (2D) or the volume (3D) of the element.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../theory/external-loads/drainage-condition.md)
</div>

------

## Inflow/Outflow

This boundary condition allows to define a flow for infiltration boundary problems. The flow velocity $v$ in m/s on the specific surface is directly defined in `<value>`. Negative values correspond to an inflow over the model boundary `<surface name>` into the domain. Positive values prescribe an outflow (exfiltration/evaporation).

```numgeo 
*Dsload, <option>
<surface name>, flow-w, <value>
```

Note that the flow specified via the velocity takes places continuously on the defined surface area, independent of i.e. the pore water pressure. It might, however, vary over time, e.g. by coupling it with an [Amplitude](../amplitude.md) using the `<option>` keyword.

A concentrated volume source [`*Cload, pw`](./cload.md) uses the opposite sign (positive values flow into the model). The water flux conditions `flow-w` and `drainage-w` are not available for u-p-U elements (`u8p4u8-sat`, ...): their pore water flux across the boundary is the relative fluid displacement `w`, which has to be prescribed instead; numgeo terminates with an error message.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../theory/external-loads/flow-condition.md)
</div>

------

## Shell elements

An element-based [surface](../surface.md) can contain faces of [shell elements](../element/elements-shell.md). A shell element has two faces:

| Face | Side of the shell | Outward normal of the face |
|---|---|---|
| `F1` (or `S1`) | top side, into which the normal $\boldsymbol n$ of the element points | $+\boldsymbol n$ |
| `F2` (or `S2`) | bottom side | $-\boldsymbol n$ |

The normal $\boldsymbol n$ follows from the node numbering by the right-hand rule (see [shell elements](../element/elements-shell.md#orientation-and-output-axes)). The following load labels are available for the faces of shell elements; the load acts per unit area of the mid-surface:

| Load label | Load |
|---|---|
| `P` | [uniform pressure](#uniform-pressure) normal to the face; positive values act along the outward normal of the face |
| `X`, `Y`, `Z` | [traction in a global direction](#traction-in-global-direction), independent of the face |

* As for continuum elements, a load which *presses on* a face is a negative pressure. `P` on the face `F1` acts like the label `p` of [`*Dload`](./dload.md#shell-elements), `P` on the face `F2` in the opposite direction. A load of 10 kPa from above on a horizontal slab whose normal points upwards is `P, -10.0` on the face `F1` or, equivalently, `P, 10.0` on the face `F2`.
* A traction does not depend on the face: `F1` and `F2` give the same load. A surface which contains both faces of an element loads it twice (a pressure `P` on both faces cancels).
* The pressure follows the curved surface of the quadratic elements `u6-shell` and `u8-shell`. The loads are integrated with the shape functions of the element like the loads of `*Dload` and refer to the undeformed geometry.
* A surface may contain faces of shell elements and faces of continuum elements.
* The other load labels (`T`, `SWP`, springs, compliant base, drainage, inflow/outflow) and the option `user` are not available for shell elements. Node-based surfaces must not cover shell elements, since the loaded side of a shell cannot be derived from its nodes. numgeo stops with an error message in these cases.

Example: a slab whose normal points upwards, loaded by 10 kPa from above, and the wall of a tank whose normals point outwards, loaded by an internal pressure of 50 kPa:

```numgeo
*Surface, type=element, name=slab-top
slab, F1
*Surface, type=element, name=tank-inside
wall, F2
...
*Dsload, ramp
slab-top, P, -10.0
tank-inside, P, -50.0
```

The loads are verified in the benchmark [Shell elements: loads](../../benchmark/shell/shell-loads.md#surface-loads-on-the-faces-f1-and-f2).

------

## Faces of elements cut by an embedded shell

A surface may contain faces of host elements cut by an [embedded shell](../embedded-regions/interaction-surface-plate.md) with `host=split`. The cut elements are duplicated, one copy for each side of the shell; a surface defined by element sets receives both copies through the element sets of the original, a surface defined by nodes receives them with the face of the original. A load on such a face is shared between the two copies in proportion to the part of the face which lies on their side (face fractions, see [`*Dload`](./dload.md#faces-of-elements-cut-by-an-embedded-shell)). This holds for the labels `P`, `X`, `Y`, `Z`, `FLOW-W`, `DRAINAGE-W` and the ground springs; `T`, `SWP` and the compliant base conditions are not available on cut elements, and a surface with cut elements cannot be used in a [contact pair](../contacts/contact-pair.md). numgeo stops with an error message in these cases. A load which stops at the shell is restricted to the copies of one side with the option `side=`.
