# Change Material
```numgeo 
*Model change, Material
<element set>, <new material name>
```

!!! note "Release information"

    `*Model change` was introduced in the [November 2025 release](../../release/release_notes_2025_11.md).

Use this option to reassign materials during analysis by changing the material definition for all elements in the specified `<element set>` to the `<new material name>`.

Note that:

* Both the `<element set>` and the `<new material name>` must be defined before any step definitions, even if they weren't previously used.

* Changing the stress-strain relation model (`*Mechanical` model) requires careful consideration, particularly when failure criteria are involved, as admissible stress states may change. This can cause numerical difficulties if the current stress state is invalid under the new model, potentially resulting in sudden plastic strain jumps.

* For challenging material transitions, consider a two-step approach:
    1. First `*Step`: Change the material model while constraining all displacements of nodes in the `<element set>` using `*Boundary, increment` and record reaction forces with `*Save reaction forces`.
    2. Second `*Step`: Gradually release these reaction forces using `*Reaction force, amplitude = ...` to establish a new equilibrium that finds an admissible stress state through controlled plastic deformations.


<div class="grid cards" markdown>

- __Reference manual__

    ---

    [:octicons-arrow-right-24: Corresponding section in the Theory Manual](../../theory/model-change/material.md)

</div>
