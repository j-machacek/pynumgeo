# Change a contact pair to small sliding
```numgeo
*Model change, contact pair, sliding=small
<slave surface>, <master surface>
```

!!! note "Release information"

    `*Model change, contact pair` is part of the [upcoming release](../../release/release_notes_upcoming.md).

Use this option to change contact pairs with [`discretisation=IPS`](../contacts/contact-pair.md#integration-point-to-surface-ips) from finite sliding to [small sliding](../contacts/contact-pair.md#small-sliding-with-ips) at the beginning of a step. The configuration at the beginning of the step becomes the reference configuration of the pair: from then on the paired points, the contact normals and tangents and the integration areas are those of this configuration, while the gap, the slip and the contact stresses follow the displacements.

Typical use: a model is built in construction stages with finite sliding, and the contact geometry is fixed before a step in which the displacements become large while the continua are geometrically linear, e.g. a [strength reduction](../step/reduction.md) that is followed to large displacements.

---

## Data lines

Each data line selects one surface pair, i.e. one data line of a [`*Contact pair`](../contacts/contact-pair.md) definition, by its slave and its master surface in the order of that definition. Any number of data lines may follow the keyword.

* The surfaces and the contact pair have to be defined before the first step; the pair may have been defined without `sliding` (finite sliding, the default).
* Other surface pairs are not changed, also if they use the same interaction or belong to the same `*Contact pair` definition.
* The option `sliding=small` is mandatory. A pair with small sliding cannot be changed back to finite sliding.

The following selections stop the analysis with an error message:

| Selection | Message |
|---|---|
| a surface that is not defined | `Unknown surface ...` |
| surfaces that are not paired by a `*Contact pair` | `no *Contact pair has the slave surface ... and the master surface ...` |
| the surfaces of a pair in the wrong order | `... the pair is defined with ... as slave and ... as master surface` |
| a surface pair that is defined in more than one `*Contact pair` | `... the selection is ambiguous` |
| a pair with another discretisation than `IPS`, or with `doublepass` | `... does not use discretisation=IPS` / `... uses the option doublepass` |
| the same pair twice in one step | `... is selected more than once` |
| a face of the slave surface also belongs to the slave surface of a pair that keeps finite sliding (contact pairs [merged](../contacts/contact-pair.md#several-contact-pairs-on-one-slave-surface) because their slave surfaces share faces) | `... belongs to the slave surface of the surface pair ... with small sliding and to that of the surface pair ... with finite sliding ... the selection is ambiguous` |

---

## Behaviour

* **Reference.** The reference of every integration point of the slave surface is captured once at the beginning of the step: after the restart files have been read, after the contact topology has been rebuilt for elements removed or activated in the same step, and before the first increment. It is the converged configuration of the end of the previous step and is kept through equilibrium iterations, rejected increments, the following steps and a restart.
* **Continuity.** The change starts from the converged contact state: normal gap (including clearance, `Adjust` and [`gap=activation`](../contacts/contact-pair.md#gap) offsets), contact stresses, status (open or closed) and state variables of the friction model are kept. With unchanged displacements the contact tractions and forces are those of the end of the previous step. The log file reports the largest difference between the converged normal gap of the points and the normal gap of their reference projection (round-off for a converged previous step).
* **After the change** the normal gap of a point changes by the relative displacement of the point and its partner along the reference normal, the slip by their relative displacement along the reference tangents; opening, closure, stick, slip and the (reduced) friction strength are evaluated as before. See [small sliding with IPS](../contacts/contact-pair.md#small-sliding-with-ips) for the formulation, the normals at facets and corners and the treatment of points without partner.
* **Faces activated later.** Integration points of slave faces activated by [`*Model change, add`](elements.md) in a later step, and points that find their partner on a master face activated later, take the configuration at the beginning of the activation step as their reference (after the activated nodes have been placed with `position=design` or `deformed`); with `gap=activation` their normal gap at that instant is the reference zero gap. A pair can be selected while its faces are still inactive.
* **Repeated selection.** Selecting a pair that already uses small sliding (by `sliding=small` of `*Contact pair` or by an earlier step) leaves its reference unchanged; a warning is written to the log file.
* **Merged contact pairs.** If the selected pair was [merged](../contacts/contact-pair.md#several-contact-pairs-on-one-slave-surface) with other contact pairs (slave surfaces with common nodes), the selection still addresses the faces of its slave surface only. Their integration points are paired with the merged master surface, as in finite sliding.
* **Step types.** The option is available in all step types in which IPS contact is available, including [`*Reduction`](../step/reduction.md) (also with `arc-length`). It cannot be combined with `*PFEM remeshing`.
* The log file reports every change (`Model change: small sliding of surface pair ...`) and, per contact pair, the number of integration points whose reference was captured, with and without partner.

---

## Restart

In a [restart analysis](../restart.md) the changes of the skipped steps are applied from the input deck (log message `Model change of the skipped step ... replayed (restart)`), and the reference of the integration points is read from the restart files (`_ips_contact_step_<n>.dat`). The contact pairs and the `*Model change, contact pair` definitions of the skipped steps must be those of the original analysis, and the mesh must be the same; otherwise the analysis stops. A pair can be changed in the first step of the restart analysis; its reference is then the configuration of the restart files.

---

## Example

Staged construction followed by a change of both contact pairs: block A is pressed into a support (step 1), the support settles by 0.5 mm (step 2), block B is activated above the settled support and pressed down (step 3, `gap=activation`), and both blocks are slid over the support with small sliding (step 4). All nodes are displacement-controlled, so that the resultants follow from the penalty and Coulomb laws.

```numgeo
*Interaction, name=friction
*Normal, mechanical=penalty
1e6
*Friction, model=Coulomb
1e5, 0.3, 0
** two contact pairs with the same interaction, finite sliding (default)
*Contact pair, interaction=friction, discretisation=IPS, gap=activation
block_a_surface, support_a
*Contact pair, interaction=friction, discretisation=IPS, gap=activation
block_b_surface, support_b
...
*Step, name=initial, inc=1000, maxiter=35
*Static
0.1, 1, 1e-6, 0.1
*Model change, remove
block_b
...
*End step
...
*Step, name=place, inc=1000, maxiter=35
*Static
0.1, 1, 1e-6, 0.1
*Model change, add
block_b
...
*End step
*Step, name=slide, inc=1000, maxiter=35
*Static
0.1, 1, 1e-6, 0.1
*Model change, contact pair, sliding=small
block_a_surface, support_a
block_b_surface, support_b
...
*End step
```

Complete input file: [small-sliding-staged.inp](assets/small-sliding-staged.inp) (run with `numgeo inp=small-sliding-staged out=run ncpus=1`). The sums of the forces on the nodes of the blocks (print output `RF`) are

| End of step | $N_A$ (kN/m) | $T_A$ (kN/m) | $N_B$ (kN/m) | $T_B$ (kN/m) |
|---|---:|---:|---:|---:|
| 1 `initial` | 1000 | 0 | – | – |
| 2 `settle` | 1000 | 0 | – | – |
| 3 `place` | 1000 | 0 | 1500 | 0 |
| 4 `slide` | 1000 | −300 | 1500 | −450 |

i.e. $N = \varepsilon_N \cdot$ penetration $\cdot L$ with $L = 1$ m (block B: 1.5 mm from its activation, since `gap=activation` takes the gap of 0.5 mm at the activation as zero) and $T = -\tan\delta\,N$ after the elastic slip $\tan\delta\,N/\varepsilon_T$ of 3 and 4.5 mm. The log file of step `slide` contains

```text
-> Model change: small sliding of surface pair "BLOCK_A_SURFACE, SUPPORT_A" (contact pair 1) from step SLIDE on, reference: configuration at the beginning of the step
-> Model change: small sliding of surface pair "BLOCK_B_SURFACE, SUPPORT_B" (contact pair 2) from step SLIDE on, reference: configuration at the beginning of the step
-> Small sliding of IPS contact pairs, step SLIDE
   contact pair 1, slave surface BLOCK_A_SURFACE, master surface SUPPORT_A:
      reference configuration captured for 8 integration points: 8 with a partner, 0 without (out of contact)
      largest difference between the converged normal gap and the normal gap of the reference projection: 0.0000E+00
   contact pair 2, slave surface BLOCK_B_SURFACE, master surface SUPPORT_B:
      reference configuration captured for 8 integration points: 8 with a partner, 0 without (out of contact)
      largest difference between the converged normal gap and the normal gap of the reference projection: 0.0000E+00
```

With finite sliding the flat interfaces of this example give the same resultants as long as the blocks stay on their master surfaces. With small sliding the paired points stay paired for any slip, as the geometrically linear continua assume.

<div class="grid cards" markdown>

- __Reference manual__

    ---

    [:octicons-arrow-right-24: Small sliding of `*Contact pair`](../contacts/contact-pair.md#sliding)

</div>
