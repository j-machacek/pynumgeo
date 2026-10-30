# Change friction
```numgeo
*Model change, friction
<interaction name>, <parameters of the friction model>
```

!!! note "Release information"

    `*Model change, friction` is part of the [upcoming release](../../release/release_notes_upcoming.md).

Use this option to change the parameters of the friction model of an [interaction](../contacts/interaction.md) at the beginning of a step, for example the friction of an interface that is smooth in the first stages of an analysis and rough in the later ones. The option corresponds to `*Change friction` of Abaqus/Standard; the theory and the differences are described in the [Theory Manual](../../theory/model-change/friction.md).

---

## Data lines

Each data line names an interaction and gives the new parameters of its friction model. Any number of data lines (interactions) may follow the keyword.

* `<interaction name>`: name of an interaction defined with [`*Friction`](../contacts/interaction.md#tangential-contact-settings) before the first step.
* `<parameters of the friction model>`: the values of the data line of the `*Friction` definition of the interaction, in the same order and with the same number of values:

    | Friction model | Values |
    |---|---|
    | `Coulomb` | `[ε_T,] tan(δ), c` |
    | `Mohr-Coulomb` | `[ε_T,] tan(δ), tan(ϑ), c` |

    The tangential penalty factor $\varepsilon_T$ is given if, and only if, it is given in the `*Friction` definition, and with the same value: it cannot be changed (otherwise it is calculated from the material stiffness, as before the change). The two surfaces of a contact use the smaller of their tangential penalty factors, so that a larger value would not act.

---

## Behaviour

* The new parameters act from the first increment of the step on. They are kept in the following steps until they are changed again, like a [material change](material.md); loads and boundary conditions, in contrast, act only in the step in which they are defined.
* The change is instantaneous at the beginning of the step (no ramp). The contact state is kept: status (open or closed), normal and tangential contact stresses, state variables of the interaction. The friction law continues from the converged tangential stress with the new parameters:
    * increased friction: the contact sticks until the shear stress reaches the new capacity;
    * decreased friction below the current shear stress: the shear stress is returned to the new capacity in the first increment of the step, the surfaces slip. The resulting change of the contact forces is applied in a single increment; a large decrease can be split over several steps.
* Frictionless contact up to the change: define the interaction with `*Friction, model=Coulomb` and $\tan\delta = 0$, $c = 0$. With these parameters the Coulomb model gives the tractions and the tangent of frictionless contact (no shear stress, no tangential stiffness).
* Available for the friction models `Coulomb` and `Mohr-Coulomb` (all discretisations). The interaction has to be defined before the first step. Not available for the hypoplastic friction model and for interactions with user-defined contact properties ([`*Interaction, user`](../contacts/interaction.md)).
* In a [strength-reduction](../step/reduction.md) step with the option `Reduction` of [`*Contact options`](../contacts/contact-options.md), the parameters valid in that step are reduced.
* In a [restart analysis](../restart.md) the friction changes of the skipped steps are applied when the analysis is restarted (log message `Model change of the skipped step ... replayed (restart)`).
* The log file reports every change with the old and the new parameters.

---

## Example

An interface without friction in the first steps and with $\tan\delta = 0.7$ from the step `rough` on (the tangential penalty factor is repeated unchanged):

```numgeo
*Interaction, name=interface
*Normal, mechanical=penalty
1.0e6
*Friction, model=Coulomb
1.0e6, 0.0, 0.0
...
*Step, name=rough
*Static
0.1, 1.0, 1e-5, 0.1
*Model change, friction
interface, 1.0e6, 0.7, 0.0
...
*End step
```

The [benchmark](../../benchmark/contacts/friction-change.md) slides a block over a support with a sequence of friction changes.

<div class="grid cards" markdown>

- __Theory manual__

    ---

    [:octicons-arrow-right-24: Corresponding section in the Theory Manual](../../theory/model-change/friction.md)

</div>
