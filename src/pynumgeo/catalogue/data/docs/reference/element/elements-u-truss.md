# Truss elements

!!! note "Release information"

    Truss elements were introduced in the [November 2025 release](../../release/release_notes_2025_11.md).

<p align="center">
  <img src="./assets/element-truss.png" width=40%/><br>
</p>

Truss (or cable) elements are structural members capable of transmitting stresses only in the direction normal to the cross section. It is assumed that this normal stress is constant over the cross-sectional area. Details on the implementation are provided in the [Theory Manual](../../theory/elements/truss.md).

The properties of truss elements are assigned using the `*Material` keyword in combination with the `*Truss properties` sub-keyword. See the [Reference Manual](../material/truss-properties.md) for more information. By default the elements are linear elastic in tension and compression. With the option `tension-only` they carry no compressive force, and with a tensile strength their normal force is limited; both are meant for cables, tie rods and geosynthetics.

Truss elements can be embedded into a mesh of continuum elements with [`*Embedded region, interaction`](../embedded-regions/interaction.md): grouted anchors and nails (default) or, in two-dimensional models, geotextiles and geogrids (`section=sheet`).

---

## 2D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** |
|---|---|---|---|---|---|
|``u2-truss``           | 2D            | truss       | 2              | linear      | 1  |
|``u3-truss``           | 2D            | truss      | 3             |   quadratic   | 3  |   

\*  nIP = number of integration points

!!! warning "3-node elements"

    Since truss elements have no bending stiffness, mechanisms may occur, when using 3-node truss elements as ‘stand alone’ elements, if the central node is not constrained in some way.

---

## 3D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** |
|---|---|---|---|---|---|
|``u2-truss-3D``           | 3D            | truss       | 2              | linear      | 1  |
|``u3-truss-3D``           | 3D            | truss      | 3             |   quadratic   | 3  |   

\*  nIP = number of integration points

---

## Construction stages, reset and restart

The strain of a truss element is not integrated incrementally: the elongation follows from the displacements relative to a *stress-free reference state* of the element. The only state variable is the plastic strain of elements with a tensile strength. The reference state is the initial configuration unless it is changed by one of the following options:

* **`*Model change, add`** ([element activation](../model-change/elements.md)): an element that has never been active is activated strain-free and without force in the current position of its nodes, e.g. a strut installed after an excavation stage. It carries only the loads applied after its activation.
* **`*Model change, remove`**: a removed element is not evaluated. The nodal forces it exerted on the remaining model are ramped down over the step. If it is activated again later, it comes back with the elongation (and therefore with the normal force) it had at the removal.
* **`*Reset, Displacement`** ([reset](../reset.md)): the displacements start again from zero, the truss elements keep their elongation and normal force.
* **Restart** ([`*Restart write` / `*Restart read`](../restart.md)): the reference state and the plastic strain are part of the restart files. Restart files written by earlier versions can be read.

`*Model change, material` assigns new `*Truss properties`; since the elements are elastic, the new stiffness acts on the complete elongation relative to the reference state (see the anchor of the tutorial [Excavation pit with a retaining wall](../../tutorial/staged-construction/excavation.md#installation-and-prestressing)).

---

## Additional output

For truss elements additional output variables are available. In addition to general output in cartesian coordinates such as displacements, stress and strain, local quantities in direction of the truss axis can be requested:

* `stress-truss`: normal force $N = A\,\sigma$ of the truss in F, tension positive. With $A = 1$ it is the axial stress in F/L² or, for a geosynthetic layer in a plane strain model, the tensile force per unit width.
* `strain-truss`: strain in direction of the truss axis, relative to the stress-free reference state
* `pstrain-truss`: plastic strain in direction of the truss axis (elements with a tensile strength)
* `state-truss`: state of the axial law: -1 slack (`tension-only`), 0 elastic, 1 at the tensile strength

Truss elements which are embedded with [`*Embedded region, interaction`](../embedded-regions/interaction.md#output) also provide the state of their interface: `interface-shear`, `interface-disp`, `interface-slip` and `interface-cap`.

The variables are calculated at the integration points; the element output is their mean. For output at the nodes ([`*Output, field`](../output/field.md#node-output)) the values are extrapolated to the nodes of each element and averaged over the line elements (truss and beam elements) which share the node, weighted with their length.
