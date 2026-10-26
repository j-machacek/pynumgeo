# Early termination

```numgeo 
*Termination
<element set>, <control quantity>, <target value>
``` 

Use this keyword to define an early termination condition for a specific element set. Once this condition is met in any of the integration points of the specified element set, the step will be terminated and the calculation proceeds with the next step.

- `<element set>`: Element set that should be monitored during the calculation.

- `<control quantity>`: The quantity to be evaluated. Currently strain and stress components can be monitored:

    - Strains: `e11`, `e22`, `e33`, `e12`, `e13`, `e23`
    - Stresses: `s11`, `s22`, `s33`, `s12`, `s13`, `s23`

- `<target value>`: the target value against `<control quantity>` is checked

Several `*Termination` criteria can be defined in one step. The step is terminated as soon as the first of them is fulfilled.

---

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } Theory Manual__

    ---

    [:octicons-arrow-right-24: How to use it](../theory/solution-method/early-termination.md)
</div>
