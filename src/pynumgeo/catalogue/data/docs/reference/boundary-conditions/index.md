# Boundary conditions and loads

Boundary conditions specify the behavior of a problem’s solution on the boundaries of the computational domain. They are essential for correctly formulating and solving partial differential equations using the finite element method. In broad terms, boundary conditions are usually classified into:

* [Essential (Dirichlet) Boundary Conditions:](#essential-dirichlet-boundary-conditions)

    These conditions prescribe the value of the solution itself on the boundary. For instance, in a structural problem, a Dirichlet boundary condition might fix displacements of a beam’s endpoints to zero. In a thermal problem, it could fix the temperature at the boundary to a known value.

* [Natural (Neumann) Boundary Conditions:](#natural-neumann-boundary-conditions)

    These conditions specify the value of the derivative of the solution normal to the boundary or, in many physical problems, the flux (such as heat flux, fluid flux, or stress). In a structural context, this may correspond to prescribing surface tractions rather than displacements. In a thermal problem, it can represent a specified heat flow across the boundary.

* [Mixed (Robin) Boundary Conditions:](#mixed-robin-boundary-conditions)

    These conditions relate a field value to its boundary flux. A film condition relates heat flux to the difference between the solid and ambient temperatures.

* [Others:](#others)

    Other options to apply loading or constraints include the definition of body forces, mass points or spring-damper elements.

## Essential (Dirichlet) Boundary Conditions


<div class="grid cards" markdown>
- :material-package-variant-closed-remove:{ .lg .middle } __*Boundary__

    ---

    [:octicons-arrow-right-24: Dirichlet boundary conditions, can vary in time](./boundary.md)

- :material-package-variant-closed-remove:{ .lg .middle } __*Flexible-Boundary__

    ---

    [:octicons-arrow-right-24: Dirchlet boundary conditions, can vary in time and space](./flexible-boundary.md)

- :material-package-variant-closed-remove:{ .lg .middle } __*UBoundary__

    ---

    [:octicons-arrow-right-24: User-defined Dirichlet boundary conditions, can vary in time](./Uboundary.md)

</div>


## Natural (Neumann) Boundary Conditions

<div class="grid cards" markdown>

- :material-arrow-collapse-down:{ .lg .middle } __Distributed loads__

    ---

    [:octicons-arrow-right-24: Pressure, traction and heat flux acting on element faces](./dload.md)

- :material-arrow-collapse-down:{ .lg .middle } __Distributed surface loads__

    ---

    [:octicons-arrow-right-24: Distributed loads acting on surfaces](./dsload.md)

- :material-arrow-collapse-down:{ .lg .middle } __Concentrated loads__

    ---

    [:octicons-arrow-right-24: Concentrated forces, moments and heat supplies acting on nodes or node sets](./cload.md)

- :material-arrow-collapse-down:{ .lg .middle } __Reaction forces__

    ---

    [:octicons-arrow-right-24: Save and apply reaction forces acting from constrained nodes](./reaction_force.md)

</div>

## Mixed (Robin) Boundary Conditions

<div class="grid cards" markdown>

- :material-thermometer:{ .lg .middle } __Film condition__

    ---

    [:octicons-arrow-right-24: Heat exchange with an ambient temperature using `FILMi` under `*Dload`](./dload.md#film-condition)

</div>

## Loads in a sequence of steps

Boundary conditions and loads (`*Boundary`, `*Cload`, `*Dload`, `*Dsload`, `*Body force`, ...) are part of the step in which they are defined. They are **not** carried over into the next step: at the beginning of a step exactly the loads listed in this step act on the model. This has three consequences, which are illustrated in the tutorial [Construction stages and load cases of a raft foundation](../../tutorial/shells/raft-construction-stages.md):

* **A load that remains** (the self weight of the soil and of the structures, the loads of a building in a later load case) has to be defined again in every following step, normally with the option `instant`, since it acts with its full magnitude from the beginning of the step.
* **A load that is not defined again disappears** at the beginning of the next step, i.e. with the first increment. To remove a load gradually, define it once more in the next step with an amplitude that falls from 1 to 0 (e.g. `*Amplitude, type=tabular` with the points `0.0, 1.0` and `1.0, 0.0`).
* **`ramp` always starts from zero**: it increases the load linearly from 0 at the beginning of the step to its full magnitude at the end of the step. A load which was applied with `ramp` in one step and is repeated with `ramp` in the next step drops to zero at the beginning of that step. To increase a load from $F_1$ to $F_2$ within a step, define $F_1$ with `instant` and the increase $F_2-F_1$ with `ramp` (several definitions acting on the same nodes, elements or faces add up).

Amplitudes are evaluated with the step time (the time counted from the beginning of the step). An amplitude can therefore be used again in several steps, e.g. an amplitude which applies and removes a load within one step. The same rules hold for boundary conditions: prescribed values refer to the total value of the selected degree of freedom (displacement, pressure or absolute temperature) and have to be defined in every step.

A typical geotechnical analysis consists of the following phases:

| step | procedure | loads defined in the step |
|---|---|---|
| initial state | [`*Geostatic`](../step/geostatic.md) | self weight of the soil (`*Body force, instant`) in equilibrium with the initial stress field (`*Initial conditions, type=stress`); structures which are built later are removed with [`*Model change, remove`](../model-change/elements.md) |
| construction | [`*Static`](../step/static.md) | self weight of the soil (`instant`), activated structures ([`*Model change, add`](../model-change/elements.md)) and their self weight (`ramp`), excavation by removal of elements |
| service loads | `*Static` | all loads of the previous steps (`instant`), new loads (`ramp` or amplitude) |
| variable or cyclic loads | `*Static` or [`*Dynamic`](../step/dynamic.md) | all permanent loads (`instant`), variable loads with an amplitude |

## Others

<div class="grid cards" markdown>
- :material-human-child:{ .lg .middle } __*Body forces__

    ---

    [:octicons-arrow-right-24: Body/volume forces](./body-force.md)

- :material-thermometer:{ .lg .middle } __Volume heat sources__

    ---

    [:octicons-arrow-right-24: Heat supplied within u-T elements using `HV` under `*Dload`](./dload.md#volume-heat-source)

- :material-weight:{ .lg .middle } __Mass points__

    ---

    [:octicons-arrow-right-24: Mass points assigned to nodes or node sets](./mass_point.md)

- :material-transit-connection-horizontal:{ .lg .middle } __Connector elements__

    ---

    [:octicons-arrow-right-24: Spring-damper element between two nodes or node sets](./connector_element.md)

</div>
