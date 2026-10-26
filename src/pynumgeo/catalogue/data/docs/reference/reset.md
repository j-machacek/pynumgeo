# Reset

```numgeo 
*Reset
<subsequent line>
``` 


Use this keyword to reset the displacement to zero at the beginning of
any step during a calculation. Optionally, the previously created
strains can also be set to zero.

-   `<subsequent line> = Displacement`: Set the
    displacements calculated so far to zero, i.e. reset the mesh to its
    initial (reference) configuration. All other solution variables
    (e.g. pore water pressure) and state variables (e.g. stress, void
    ratio) retain their current value.

    [Beam](element/elements-beam.md#construction-stages-reset-and-restart), [truss](element/elements-u-truss.md#construction-stages-reset-and-restart) and [shell elements](element/elements-shell.md#construction-stages-reset-and-restart) keep their deformation, forces and moments. The interface of embedded line elements ([`*Embedded region, interaction`](embedded-regions/interaction.md#construction-stages-reset-and-restart)) keeps its tractions and its slip.

-   `<subsequent line> = Displacement, Strain`:
    Set the displacements and the strains calculated so far to zero,
    i.e. reset the mesh to its initial (reference) configuration. All
    other solution variables (e.g. pore water pressure) and state
    variables (e.g. stress, void ratio) retain their current value.