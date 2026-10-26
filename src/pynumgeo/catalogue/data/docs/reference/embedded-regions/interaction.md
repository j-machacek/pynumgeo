# Interaction

```numgeo
*Embedded region, interaction [, type=constant | type=Mohr-Coulomb] [, section=bar | section=sheet]
<guest element set>, <host element set>, <interface parameters>
```

This keyword embeds line (guest) elements - [truss](../element/elements-u-truss.md) or [beam](../element/elements-beam.md) elements - into a region of continuum (host) elements using the *embedded beam* approach: in contrast to the [absorbed](absorbed.md) method, the guest elements retain their independent degrees of freedom and interact with the host region through distributed interface springs which are numerically integrated over the embedded length. The guest elements are either **bars** (`section=bar`, default: grouted anchors, soil nails, micro piles) or, in two-dimensional models, **sheets** (`section=sheet`: geotextiles and geogrids), see [Sections](#sections).

For the underlying formulation refer to the [Theory Manual](../../theory/embedded-regions/interaction.md). Verification examples are provided as benchmarks, in [2D](../../benchmark/embedded/embedded-anchor-pull-out-2d.md) and in [3D](../../benchmark/embedded/embedded-anchor-pull-out-3d.md), for the Mohr-Coulomb capacity in a [geostatic stress field](../../benchmark/embedded/embedded-anchor-pull-out-mc.md) and for [geosynthetic layers](../../benchmark/geosynthetics/geosynthetics.md).

---

## Keyword options

Both options are optional.

| Option | Values | Default | Effect |
|---|---|---:|---|
| `type` | `constant`, `Mohr-Coulomb` | `constant` | Axial capacity of the interface: none or a constant skin traction `t_ult` (`constant`), or a capacity which follows from the stress of the host, $t_{cap} = A_s \cdot \max(c - \sigma_n\tan\varphi,\ 0)$ (`Mohr-Coulomb`). The type determines the entries of the data lines. |
| `section` | `bar`, `sheet` | `bar` | What the guest elements represent, see [Sections](#sections). `bar`: a bar surrounded by soil. `sheet`: a layer with soil on its two faces, in two-dimensional models; requires `type=Mohr-Coulomb`. |

---

## Data lines

The keyword can be followed by an arbitrary number of data lines, each defining one interaction between a guest element set and a host element set. With `type=constant` (default) a data line reads

```numgeo
*Embedded region, interaction
<guest element set>, <host element set>, k_t, k_n [, t_ult]
```

and with `type=Mohr-Coulomb`

```numgeo
*Embedded region, interaction, type=Mohr-Coulomb [, section=bar | section=sheet]
<guest element set>, <host element set>, k_t, k_n, c, phi, A_s
```

- `guest element set`: Name of the element set containing the line elements to be embedded. Only elements of shape *beam* (trusses, beams) are permitted.
- `host element set`: Name of the element set defining the host region. Only continuum elements (triangular, rectangular, tetrahedral, hexahedral) are considered as potential host elements; other element types contained in the set (e.g. the guest elements themselves in case of an all-inclusive set) are ignored.
- `k_t`: Axial (tangential) interface stiffness per unit length in F/L², e.g. kN/m/m. Required, `k_t` > 0.
- `k_n`: Lateral (normal) interface stiffness per unit length in F/L², e.g. kN/m/m. Required, `k_n` ≥ 0.
- `t_ult`: Ultimate axial skin traction per unit length in F/L, e.g. kN/m (optional). If provided and positive, the axial interface traction is limited to $|t_s| \le t_{ult}$ (elastic - perfectly plastic slider); the plastic slip is stored at the integration points of the guest elements and updated upon convergence of each increment. If omitted (or ≤ 0), the axial interface behaviour is linear elastic.
- `c`: Interface cohesion (adhesion) in F/L², e.g. kPa. Required, `c` ≥ 0 (`c` and `phi` must not both be zero).
- `phi`: Interface friction angle in degrees. Required, 0 ≤ `phi` < 90.
- `A_s`: Shear surface per unit length of the guest elements in L, converting the interface stress to a force per unit length. Required, `A_s` > 0. Its meaning depends on the [section](#sections).

For `type=Mohr-Coulomb` the capacity per unit length is $t_{cap}(x) = A_s \cdot \max(c - \sigma_n(x)\tan\varphi,\ 0)$ with the (effective) normal stress $\sigma_n$ of the host material at the guest elements (tension-positive; compression increases the capacity, the max-term is the tension cutoff). Which normal stress is used is selected with `section`.

---

## Sections

The option `section` states what the line elements represent. It selects the normal stress $\sigma_n$ of the Mohr-Coulomb capacity and the way guest nodes on the edges of host elements are treated:

| | `section=bar` (default) | `section=sheet` |
|---|---|---|
| The guest elements are | a bar which is surrounded by soil: grouted anchor, soil nail, micro pile (in 2D: a row of them) | a layer seen in cross-section, with soil on its two faces: geotextile, geogrid |
| Models | 2D and 3D | 2D (plane strain) |
| Guest elements | truss or beam elements | truss elements (usually `tension-only`) or beam elements |
| `type` | `constant` or `Mohr-Coulomb` | `Mohr-Coulomb` |
| Normal stress $\sigma_n$ | mean lateral stress $\tfrac{1}{2}(\operatorname{tr}\boldsymbol{\sigma} - \boldsymbol{a}\cdot\boldsymbol{\sigma}\cdot\boldsymbol{a})$ with the axis $\boldsymbol{a}$ of the bar; in 2D it includes the out-of-plane stress | stress normal to the layer, $\boldsymbol{n}\cdot\boldsymbol{\sigma}\cdot\boldsymbol{n}$ with the in-plane normal $\boldsymbol{n}$ of the layer |
| `A_s` | perimeter of the shaft: $\pi D$ in 3D, $\pi D / s$ for a row with the out-of-plane spacing $s$ in 2D | contact width of both faces: 2.0 for a continuous layer in a slice of unit thickness |
| `k_t` | stiffness of the shaft per unit length of the bar | stiffness of both faces together |
| Guest node on an edge between host elements | coupled to the host element found first; $\sigma_n$ from this element | host elements of both sides are kept: $\sigma_n$ is the mean of the two sides, the node is coupled to an active element, and a layer with soil on one side only has half the capacity |

An interface without capacity or with a constant capacity `t_ult` (`type=constant`) does not depend on the stress of the host; it is defined with the default section. `section=sheet` without `type=Mohr-Coulomb` is an error.

---

## Bars (section=bar)

A grouted anchor, a soil nail or a micro pile is a row of truss or beam elements, placed independently of the soil mesh. `section=bar` is the default and need not be written:

```numgeo
*Embedded region, interaction, type=Mohr-Coulomb, section=bar
Grout-Body, Soil, 1.0e5, 1.0e6, 10.0, 30.0, 0.5
```

- `k_t`, `k_n`: Stiffness of the shaft per unit length of the bar in the axial and in the lateral direction.
- `c`, `phi`: Adhesion and friction angle of the contact between the grout body and the soil.
- `A_s`: In 3D, $A_s = \pi D$ with the effective diameter $D$ of the grout body; in 2D plane strain, the elements represent a row of bars with the out-of-plane spacing $s$, hence $A_s = \pi D / s$ (the truss or beam properties are those of one bar divided by $s$ as well).

The normal stress of the capacity is the mean lateral stress $\sigma_n = \tfrac{1}{2}(\operatorname{tr}\boldsymbol{\sigma} - \boldsymbol{a}\cdot\boldsymbol{\sigma}\cdot\boldsymbol{a})$ of the host material, mapped from the converged host element stresses onto the bar: the mean of the normal stresses which act perpendicular to the axis, a scalar substitute for the radial stress around the shaft. In a two-dimensional model it includes the out-of-plane stress. The free length of an anchor is not embedded: leave its elements out of the guest element set, or let them extend beyond the host region (see the note on the host element search below). The tutorial [Pull-out of a grouted anchor](../../tutorial/embedded-beams/anchor-interaction.md) shows a complete example.

---

## Geosynthetic layers (section=sheet)

In a two-dimensional (plane strain) model a geotextile or a geogrid is a line: a row of [truss elements](../element/elements-u-truss.md) with the material option [`*Truss properties, tension-only`](../material/truss-properties.md#geosynthetics). The truss elements are placed where the layer lies, independently of the soil mesh, and are embedded with `section=sheet`:

```numgeo
*Embedded region, interaction, type=Mohr-Coulomb, section=sheet
Geogrid, Soil, 4.0e4, 1.0e6, 0.0, 28.0, 2.0
```

The data line has the same entries as for anchors; for a layer they mean:

- `k_t`: Shear stiffness of the interface per unit length of the layer in F/L², **both faces together**: $k_t = 2\,k_s\,b$ with the shear stiffness $k_s$ of one face (stress per relative displacement, e.g. kPa/m) and the width $b$ of the layer (1 m for a plane strain slice of unit thickness). The shear stress of a face is fully mobilised at the relative displacement $\tau_{max}/k_s$.
- `k_n`: Stiffness normal to the layer in F/L². The layer has to follow the soil normal to its plane: choose a large value (e.g. 10 to 100 times `k_t`).
- `c`, `phi`: Adhesion and friction angle $\delta$ of the contact between soil and geosynthetic. They are often given through an interaction coefficient $f$ from pull-out or direct shear tests, $\tan\delta = f\,\tan\varphi'$.
- `A_s`: Contact width of **both faces** per unit length of the layer in L: 2.0 for a continuous layer in a plane strain slice of unit thickness (1.0 if only one face is in contact with soil of the host set).

The capacity per unit length of the layer is $t_{cap} = A_s \cdot \max(c - \sigma_n\tan\delta,\ 0)$ with the (effective) stress normal to the layer, $\sigma_n = \boldsymbol{n}\cdot\boldsymbol{\sigma}\cdot\boldsymbol{n}$, where $\boldsymbol{n}$ is the normal of the guest element in the plane of the model. In contrast to a bar (`section=bar`), the out-of-plane stress does not act on a layer. For a horizontal layer $\sigma_n$ is the vertical stress.

Beam elements can be embedded as sheets as well, e.g. a thin wall or a stiff reinforcement seen in cross-section whose two faces are in frictional contact with the soil.

!!! note "Layers on element edges"

    The nodes of the layer may lie inside the host elements or on their edges, e.g. on the boundary between the subsoil and a fill. A node on an element edge has host elements on both sides of the layer. The normal stress at the node is then the mean of the two sides, and the node is coupled to one of the elements which are active. If the elements of one side are inactive (a layer placed on the ground before the fill is built, or soil removed above it), only one face is in contact and the capacity is halved.

!!! note "Different soils above and below the layer"

    Use two definitions for the same guest element set, one per face: each with the element set of the soil on this side as host set, the parameters of this contact, the stiffness $k_t = k_s\,b$ of one face and `A_s` = 1.0.

!!! note "Connection of a layer to a facing"

    A geogrid which is connected to a wall or to a facing is embedded a second time, with the facing elements as host set and without capacity (`type=constant`, `section=bar`, the defaults): `Geogrid, Facing, k_t, k_n`. The geogrid elements inside the facing are coupled to it, the other elements are skipped (they lie outside the host set). `k_t` transmits the tensile force of the geogrid to the facing. `k_n` couples the end of the geogrid to the facing normal to the layer, i.e. vertically for a horizontal layer. Since the soil is tied to the layer normal to its plane by the sheet interface (`k_n` of the sheet, without limit), a large `k_n` of the connection lets the soil next to the facing hang on the facing through the end of the geogrid; with a small `k_n` (e.g. 1 kN/m²) the connection transmits the tensile force of the geogrid only. The choice changes the distribution of the forces over the layers and the vertical load on the facing considerably. See the tutorial [Geogrid-reinforced wall with a propped facing panel](../../tutorial/geosynthetics/propped-panel-wall.md#connection-to-the-facing) and the [benchmark](../../benchmark/geosynthetics/geogrid-wall-rowe-ho-feligha.md).

!!! note "What the layer does not do"

    The host mesh is continuous across the layer. The layer can slide relative to the soil, and the capacity of its interface limits the force it can take up, but the soil above cannot slide along the layer relative to the soil below other than by shearing of the host elements. The layer is geometrically linear (no membrane effect).

---

## Construction stages, reset and restart

Guest elements and host elements may be removed and activated with [`*Model change, remove/add`](../model-change/elements.md). The interface of a guest element acts as long as the guest element and the host elements to which its nodes are coupled are active:

- **Removal** of the guest element or of its host elements: the interface forces are ramped down to zero over the step, like the nodal forces of the removed elements.
- **First activation**: the interface starts free of traction in the current position of guest and host. A layer installed during construction takes up only the relative displacements which occur after its installation. Together with the strain-free activation of the [truss elements](../element/elements-u-truss.md#construction-stages-reset-and-restart) this gives a layer which is free of force when it is placed. The tutorial [Geogrid-reinforced wall with a propped facing panel](../../tutorial/geosynthetics/propped-panel-wall.md) builds a wall with a layer and its fill in every lift.
- **Activation of an interface which was active before**: it returns with the tractions and the slip it had when it was lost, as the elements return with their stresses and the truss elements with their force.
- An active guest element without an active host element is not coupled to the host region (warning in the log file); its nodes must be held otherwise.
- [`*Reset, Displacement`](../reset.md) keeps the tractions and the slip of the interface.
- **Restart**: status, slip and reference of the interface are part of the [restart files](../restart.md).

---

## Output

The state of the interface is available as element output of the guest elements, for [truss](../element/elements-u-truss.md#additional-output) and for [beam](../element/elements-beam.md#notes-on-output) elements, for bars and for sheets, in the print output ([`*Output, print`](../output/print.md): elements and integration points) and in the field output ([`*Output, field`](../output/field.md): elements and nodes, ASCII and binary):

- `interface-shear`: axial interface traction in F/L (force per unit length of the guest element, all faces together). Divide by `A_s` to obtain the shear stress of the contact.
- `interface-disp`: relative axial displacement between guest element and host in L.
- `interface-slip`: plastic slip of the interface in L.
- `interface-cap`: capacity $t_{cap}$ (or `t_ult`) in F/L; zero if no capacity is defined.

A 2-node element (one integration point) reports the mean over its length, a 3-node element the values at its three integration points. The ratio `interface-shear` / `interface-cap` is the mobilisation of the interface. If a guest element belongs to several definitions, the tractions and capacities are summed and the relative displacement and the slip are averaged. The variables are zero for elements which are not embedded or whose interface is not active. The axial force of the guest elements is the element output [`stress-truss`](../element/elements-u-truss.md#additional-output) of the truss elements and [`beam-force-n`](../element/elements-beam.md#notes-on-output) of the beam elements.

!!! note "Host element search"

    A guest element is embedded only if **all** of its nodes are located inside (or on the boundary of) a host element. Guest elements with at least one node outside the host region are skipped (no interaction forces are generated for them) and reported to the log file. This allows e.g. the free length of an anchor to extend beyond the host region without further measures. If none of the guest elements can be embedded, an error is issued.

!!! note "Wished-in-place installation"

    The interface transmits only *relative* displacements between the guest elements and the surrounding host material. Guest elements activated "wished-in-place" therefore follow the deformation of the host region free of interface forces until relative movement occurs. A typical modelling sequence for a grouted anchor is: assign a very soft (dummy) material to the anchor elements during the initial (geostatic) steps and switch to the real material using [`*Model change, material`](../model-change/material.md) in the installation step. No additional measures (reference configurations, stress resets) are required.

!!! note "Large relative slip does not disengage the interface"

    The host element and coupling weights are determined once, from the reference configuration, and never re-searched: there is no concept of the guest "leaving" the host in a geometric sense. Large relative displacement (e.g. pulling an anchor most of the way out) is handled entirely by the interface law: the axial traction saturates at `t_ult` and stays engaged, rather than the coupling being lost. See [Behaviour under large relative slip](../../theory/embedded-regions/interaction.md#behaviour-under-large-relative-slip-does-the-guest-leave-the-host) for details.

!!! note "Mohr-Coulomb capacity update"

    The capacity is evaluated from the **converged** host stresses of the previous increment: it is constant within each increment, which preserves the consistent linearisation of the slider (robust Newton convergence), and lags the host stress state by one increment. In the first increment of the step in which the interface is activated ([`*Model change, add`](../model-change/elements.md) of the guest elements), the converged host stress is that of the state before the activation, e.g. zero for a fill which is placed together with the layer; in this increment the capacity is therefore computed from the current host stress of each iteration (not linearised). Since the host element stresses are effective stresses, coupled (u-p) analyses automatically yield an effective-stress friction criterion. The host stress assigned to a guest node is the mean over the integration points of its host element; guest elements should not be larger than the host elements.

    Because of the element mean, the capacity in a linear stress field is exact for guest elements at the centroid level of a row of host elements and for sheets on its edges (mean of the two rows). Elsewhere the stress differs from that at the guest element by at most its variation over half an element, e.g. $\gamma h / 2$ for a horizontal layer in elements of height $h$ (see the [benchmark](../../benchmark/geosynthetics/geosynthetics.md#g5-host-and-guest-element-types)).

!!! warning "Limitations"

    - The interface geometry (embedded length, axial direction) and the coupling to the host elements are evaluated in the **reference configuration**. For analyses with large deformations of the host region (`nlgeom`) the interface does not follow the deformed configuration.

    - The lateral stiffness `k_n` has no capacity limit (no analogue of `t_ult`): arbitrarily large lateral relative displacement produces an unbounded elastic lateral force. This also holds for `type=Mohr-Coulomb`, whose capacity applies to the axial direction only.

    - `*Embedded region, interaction` is not available in explicit dynamic steps.

    - Do not combine `*Embedded region, absorbed` and `*Embedded region, interaction` for the same guest elements.

    - `section=sheet` is available in two-dimensional models only (error message in 3D, where a layer is a surface).

    - If the host elements on one side of a layer are removed, the capacity drops to that of one face at the beginning of the step; this change is not ramped over the step.

    - In [`*Reduction`](../step/reduction.md) steps the strength parameters of the interface are not reduced.
