
# Contact pair

```numgeo
*Contact pair, Interaction=<interaction name>, Discretisation=... [,Adjust] [,Perturbation] [,General], [Sliding=...], [Gap=...]
<Slave Surface>, <Master Surface>
```

This option defines a contact pair. The sub-keywords `Interaction` and `Discretisation` are mandatory. 

* The interaction ([*Interaction](./interaction.md)) as well as the surfaces ([*Surface](../surface.md)) have to be defined beforehand. 
* The sub-keyword `Adjust` can be added to resolve initial over-closures. Any normal stresses due to initial penetrations are not considered.
* `Perturbation ` can be used to calculate the stiffness contribution of the contact by means of numerical differentiation. 
* `Sliding=...`
* `Gap=...` (see below)

---

## Discretisation

The following discretisation methods are available:

  |Type               |             Description             | Analysis type
  |------------------ |-------------------------------------| ---------------
  |`element mortar`   | element-based mortar discretisation | 2D/3D/axisym.
  |`segment mortar`   | segment-based mortar discretisation | 2D/axisym.
  |`NTN`              |     node-to-node discretisation     | 2D/3D/axisym.
  |`IPS`              | integration-point-to-surface discretisation (`nigp=<n>`: integration points per face) | 2D/3D/axisym.


Generally, the slave and the master surface should have a comparable
number of nodes. If the modelling requires to mesh one of them finer
than the other, choose the finer surface as slave. This is in particular important if the `segment mortar` method is used.

In case `General` is used, all surfaces defined in the model are merged and paired with itself. No subsequent line is allowed in this case. Note that this method also allows for self-contact. The surfaces in the model have to be defined prior. An automatic detection of material surfaces is not yet implemented.

Note that contact in 3D models is currently limited to the
`element mortar` and `NTN` surface discretisation methods. In addition, fluid contact and fluid interaction as described in [*Interaction](./interaction.md) are only available for the
`element mortar` technique.

---

## Sliding

!!! info ""
    Only for `discretisation=element mortar`, 3D, without `perturbation`.

Control the kinematics of the contact pair:

* `finite` (**default**): the paired nodes are searched, the integration points are projected and the normals, tangents and integration areas are evaluated in the current configuration.
* `small`: all of these are evaluated once in the reference configuration and kept; the gap vector is the distance of the paired points in the reference configuration plus their relative displacement, and the normal gap and the slip are its components in the reference normal and tangents. The normal at an integration point is interpolated from nodal normals (at each node the mean of the reference normals of the faces that share it), so that a faceted surface acts as the smooth surface it approximates.

Use `sliding=small` with geometrically linear continua (all analyses without `nlgeom`) when the surfaces may slide past each other by more than a small fraction of an element face: the paired points then stay paired, as in the small-displacement theory, and the faces do not overlap in the current configuration. 

With `sliding=finite` and geometrically linear continua, curved or faceted surfaces that slide past each other overlap in the current configuration, and the continua take the overlap by compression.

The interpolated normal matters for faceted surfaces with large slip: a slip along the smooth surface has a component normal to a facet wherever the facet deviates from the smooth surface, towards the facet on one side of each corner and away from it on the other. With the normal of the facet, this component would close the gap at one end of every facet and open it at the other; with the unilateral normal law the closed ends carry pressure that grows with the slip
(for a pile modelled with a faceted solid wall, spurious pressures at the flanks and behind the pile).

Example:

```
*Contact pair, interaction=wall-soil, discretisation=element mortar, sliding=small
wall-outer, soil-outer
wall-inner, soil-plug
wall-toe, soil-toe
```

---

## Gap

!!! info ""
    Only for `discretisation=IPS` and `discretisation=element mortar`, in combination with [*Model change, add](../model-change/elements.md).

Reference of the normal gap of the faces that are activated during the analysis:

* `mesh` (**default**): the gap is measured between the faces in their current positions. A fill that is activated next to a facing which has already moved away from its mesh position starts with an open gap of the size of the facing displacement; the fill is unsupported until it has closed this gap.
* `activation`: the normal gap at the first evaluation after the activation is taken as the reference zero gap (whatever its sign): for `IPS` the gap of an integration point whose face, or the face it is paired with, has been activated; for `element mortar` the gap of a node which has been activated, or whose connected (closest) node on the other surface has been activated. The activated body is placed against the current position of its neighbour, as with the shared nodes of interface elements, and transmits contact stresses from the start. The reference is kept for the rest of the analysis. Only the normal gap is referred to the activation; the friction acts on the relative displacements after the activation in both cases.

Faces which exist from the start of the analysis are not affected. If the neighbour of an activated body has not moved (e.g. a facing which is propped during the construction), both options give the same result.

Example (staged construction of a reinforced wall with a segmental facing whose panels are placed on the displaced panels below, see the [benchmark](../../benchmark/geosynthetics/geogrid-wall-rowe-ho-feligha.md); the tutorial [Geogrid-reinforced wall with a propped facing panel](../../tutorial/geosynthetics/propped-panel-wall.md#contact-between-facing-and-fill) explains the contact definition of such a wall):

```
*Contact pair, interaction=soil-facing, discretisation=IPS, nigp=3, gap=activation
soil-face, facing-face
```
