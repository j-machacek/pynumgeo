# Distributed loads

```numgeo 
*Dload, <option>
<element set name>, <Load label>, [additional parameter]
```

This option defines a distributed load acting on the faces or in the volume of the element set `<element set name>` with a defined load magnitude. Except of `[additional parameter]` all sub-keywords are mandatory.

- `<option>`: Specify how the load should be applied. The load can either be applied:

    - instantaneously (without any temporal delay) using `<option> = instant`

    - linearly increasing with step time (0 % of the prescribed magnitude are applied at the beginning of the step and 100 % at the end of the step time) using `<option> = ramp`

    - using a user defined amplitude defined prior to the step definition using `<option> = Amplitude = <amplitude name>`

    - user-defined `<option> = user`. The user has to supply the `user_load.o` file (see [user loads](../user/load.md))

    - `side=1` or `side=2` may be added to the option (`*Dload, instant, side=2`): in a model with an [embedded shell](../embedded-regions/interaction-surface-plate.md) (`host=split`) the load then acts on the host elements cut by the shell only if they belong to that side of the shell (1: side of face 1, the + side; 2: the opposite side, face 2). Elements which are not cut receive the load in any case. See [Faces of elements cut by an embedded shell](#faces-of-elements-cut-by-an-embedded-shell).

!!! note "Loads in a sequence of steps"

    The load acts only in the step in which it is defined; `ramp` starts from zero at the beginning of every step. A load which is to remain active has to be defined again in the following steps (usually with `instant`), see [Loads in a sequence of steps](./index.md#loads-in-a-sequence-of-steps).

- `<element set name>`: Element set to which the load should be applied

Each `*Dload` keyword is followed by exactly one data line. Use separate `*Dload` definitions for different element sets, faces or load types; their contributions add up.

- `<Load label>`: Load label defining the type and, where applicable, direction of the distributed load. Currently available are:

     |**Load type**                         |
     |-----------------------------------|
     |[Uniform pressure](#uniform-pressure) |
     |[Traction in global direction](#traction-in-global-direction) |
     |[Volume heat source (`HV`)](#volume-heat-source) |
     |[Heat flux (`HFi`)](#heat-flux) |
     |[Film condition (`FILMi`)](#film-condition) |
     |[Water weight](#water-weight) |
     |[Hydrostatic pressure](#hydrostatic-pressure) |
     |[Compliant base boundary condition](#compliant-base-boundary-condition) |
     |[Shell elements: pressure and traction on the mid-surface](#shell-elements) |
     |[Faces of elements cut by an embedded shell](#faces-of-elements-cut-by-an-embedded-shell) |

------

## Uniform pressure

Distributed loads acting perpendicular to the element face `i` (where i is the face label):

```numgeo 
*Dload, <option>
<element set name>, Pi, <Magnitude>
```

Positive values for `Pi` act along the outward face normal (mechanical sign convention, tension is positive).

------

## Traction in global direction

Distributed loads acting in global direction `Dir`={X,Y,Z} on element face `i` (where i is the face label):

```numgeo 
*Dload, <option>
<element set name>, Di, Dir, <Magnitude>
```

For continuum elements, including u-T solids, a positive magnitude acts in the positive specified direction in 2D and in the negative specified direction in 3D. This is the existing Cartesian traction convention.

------

## Volume heat source

A volume heat source acts throughout each [u-T solid element](../element/elements-ut.md) in the specified element set:

```numgeo
*Dload, <option>
<element set name>, HV, <source density>
```

- `<source density>`: heat supplied per unit volume and time (W/m³ in SI units). Positive values add heat and negative values remove heat.

For example, a uniform source of $10^5$ W/m³ is defined by:

```numgeo
*Dload, instant
heated_elements, HV, 100000
```

The source is integrated over the element volume with the temperature shape functions. The options `instant`, `ramp` and `amplitude=<amplitude name>` scale the source density. The options `user` and `side` are not available for heat loads.

------

## Heat flux

A prescribed heat flux acts on face `i` of each u-T element in the specified element set:

```numgeo
*Dload, <option>
<element set name>, HFi, <heat flux>
```

- `i`: face number, following the continuum-element face numbering. Triangles have three faces, quadrilaterals and tetrahedra four, and bricks six.
- `<heat flux>`: heat supplied per unit area and time (W/m² in SI units). Positive values act **into** the solid; negative values remove heat.

For example, a heat flux of 500 W/m² into face 2 is defined by:

```numgeo
*Dload, instant
heated_elements, HF2, 500
```

The options `instant`, `ramp` and `amplitude=<amplitude name>` scale the flux. The options `user` and `side` are not available. A face without a prescribed temperature, flux or film condition is insulated. In 2D, the integrated heat rate is per unit out-of-plane thickness.

The face geometry follows the displacement interpolation, while the heat load is distributed with the temperature interpolation. In particular, a flux on a mixed element must not be replaced by equal concentrated heat loads at all displacement nodes.

------

## Film condition

A film condition describes heat exchange between a solid face and an environment at temperature $T_\infty$ (a Robin boundary condition):

```numgeo
*Dload, <option>
<element set name>, FILMi, <film coefficient>, <ambient temperature>
```

- `i`: face number, as for [heat flux](#heat-flux).
- `<film coefficient>`: heat-transfer coefficient $h$ (W/(m² K) in SI units), finite and nonnegative.
- `<ambient temperature>`: absolute ambient temperature $T_\infty$ (K in SI units), finite and strictly positive.

The inward heat flux is

$$q_{\mathrm{in}}=h(T_\infty-T).$$

For example, a film coefficient of 15 W/(m² K) and an ambient temperature of 293.15 K are defined by:

```numgeo
*Dload, instant
exposed_elements, FILM2, 15, 293.15
```

The options `instant`, `ramp` and `amplitude=<amplitude name>` scale $h$; the ambient temperature remains constant. The scaled coefficient must remain nonnegative. The options `user` and `side` are not available. The film contribution and its temperature derivative are included in the coupled equations. Requirements for a temperature reference in steady conduction are described under [`*Static`](../step/static.md).

The heat-load labels `HV`, `HFi` and `FILMi` belong to `*Dload`; they are not labels of [`*Dsload`](dsload.md). The benchmark [Heat sources, flux and film exchange](../../benchmark/thermal/thermal-loads.md) gives examples and heat-balance checks.

------

## Water weight

Distributed load acting perpendicular to the element face `i` compensating (positive) pore-water pressure by its deadweight (e.g. to simulate the flooding of slopes). The magnitude of the load is calculated such that the (only positive) pore water pressure acting on the surface is compensated. The subsequent line then reads:

```numgeo 
*Dload, <option>
<element set name>, SWPi
```

------

## Hydrostatic pressure

Hydrostatic pressure (elevation-dependent) acting perpendicular to the element face `i`. The vertical direction $h$ is assumed to be the $y$-direction in 2-D models and the distribution of initial pore water/air pressure is assumed to vary piecewise linearly with this vertical coordinate:

```numgeo 
*Dload, <option>
<element set name>, HPi, <Magnitude 1>, h1, <Magnitude 2>, h2
```

------

## Compliant base boundary condition

The compliant base boundary condition is used to impose a seismic signal at the bottom of the FE model and at the same time damping downwards propagating waves by applying equivalent viscous forces. The distributed force acts in global direction `Dir` to the element face `i` to which the force is applied. The `<Magnitude>` is defined as $\rho \cdot c_{p,s}$ of the underlying material, where $\rho$ is the density and $c_{p,s}$ is the wave speed ($c_s$ for shear waves and $c_p$ for compression waves) The subsequent line then reads:

```numgeo 
*Dload, <option>
<element set name>, <compliant type>, <Dir>, <magnitude>
```

Two types of springs are implemented, which can be chosen by setting `<compliant type>` to:

- `complianti`: This corresponds to the "implicit" implementation, where the current velocity $v$ is used to calculate the viscous stress

- `compliant0i`: This corresponds to the "explicit" implementation, where the velocity $v_0$ from the previous (converged) time step is used to calculate the viscous stress.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../theory/external-loads/compliant-base-bc.md)
</div>

------

## Shell elements

[Shell elements](../element/elements-shell.md) have no faces in the sense of the continuum elements; they are loaded on their mid-surface. The face labels (`Pi`, `Di`, ...) of the continuum elements are not available for shell elements, instead the subsequent line reads:

```numgeo 
*Dload, <option>
<element set name>, <Load label>, <Magnitude>
```

| Load label | Load per unit area of the mid-surface |
|---|---|
| `p` | pressure normal to the mid-surface; positive values act along the normal $\boldsymbol n$ of the element |
| `x`, `y`, `z` (or `1`, `2`, `3`) | traction in the global $x$-, $y$- or $z$-direction, independent of the normal |

* The normal $\boldsymbol n$ of an element follows from its node numbering by the right-hand rule (counter-clockwise numbering seen from the tip of $\boldsymbol n$, see [shell elements](../element/elements-shell.md#orientation-and-output-axes)). A positive pressure pushes the shell from its bottom side towards its top side. A load pressing on the top side, e.g. soil or water above a plate whose normal points upwards, is therefore a *negative* pressure.
* The pressure follows the curved surface of the quadratic elements `u6-shell` and `u8-shell`; for the flat elements it acts normal to the element plane.
* The loads are converted into consistent nodal forces by integration with the shape functions of the element, like the body force. The load refers to the undeformed geometry (the shell elements are geometrically linear).
* The element set has to contain shell elements only. The option `user` is not available for shell elements.
* Several `*Dload` definitions acting on the same elements add up, also with loads of [`*Dsload`](./dsload.md#shell-elements) on the faces `F1` and `F2` of the elements.

Example: a horizontal slab whose normal points upwards, loaded by 10 kPa from above, and the dead load of 2 kPa of a roof as traction in the negative $z$-direction:

```numgeo 
*Dload, ramp
slab, p, -10.0
*Dload, instant
roof, z, -2.0
```

The loads are verified in the benchmark [Shell elements: loads](../../benchmark/shell/shell-loads.md).

------

## Faces of elements cut by an embedded shell

Host elements cut by an [embedded shell](../embedded-regions/interaction-surface-plate.md) with `host=split` are duplicated, one copy for each side of the shell, and both copies keep the element faces of the original. A face load on such an element (the labels `Pi` and `Di`) is shared between the two copies in proportion to the part of the face which lies on their side: the integration weights of the face are scaled with face fractions sampled at the start of the analysis, so that the resultant of a pressure on a cut face is exact for both copies together, and the load of a copy is that of its part of the face (the distribution over the face is first order in the size of the sampling cells, $16\times16$ cells per face). The copies join the element sets of their original, so no change of the element set is needed.

A load which stops at the shell, such as the water on the ground surface of one side of a flood wall, is restricted to the copies of that side with the option `side=`; the side is the one of face 1 (+ side, `side=1`) or of face 2 (`side=2`) of the shell, whose orientation numgeo reports in the log file (normal of face 1 at the first coupling point). The element set of such a load contains the elements of that side up to and including the cut elements:

```numgeo
*Dload, instant, side=2
top-flood, P2, -35.0
```

The labels `PiW`, `SWPi`, `SWPiW`, `COMPLIANTi` and `COMPLIANT0i` are not available on cut elements; numgeo stops with an error message which names the load, the element set and the step. The log file lists the number of distributed loads which act on faces of the duplicated elements. The loads are verified in the element tests of the embedded shell (T10).
