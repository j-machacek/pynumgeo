# Truss properties

!!! note "Release information"

    Truss elements were introduced in the [November 2025 release](../../release/release_notes_2025_11.md).

```numgeo
*Truss properties [, tension-only]
A, E [, f_t]
```

This keyword is used to prescribe the properties of [truss elements](../element/elements-u-truss.md). The keyword is followed by one line with the following
parameters:

* `A`: Cross-sectional area $A$ of the truss element with units of L², e.g. m². The current implementation assumes that the cross-sectional area is constant throughout the simulation.
* `E`: Elastic stiffness $E$ (Youngs modulus) of the truss material provided in units of F/L², e.g. kPa. For more information please refer to the dedicated section in the [Theory Manual](../../theory/elements/truss.md).
* `f_t` (optional): Tensile strength of the truss material in units of F/L², e.g. kPa. The normal force of the element is limited to $A\,f_t$; when this force is reached, the element elongates plastically at (practically) constant force and keeps a plastic strain when it is unloaded. If `f_t` is omitted, the strength is not limited.

The following option can be added to the keyword line:

* `tension-only`: The truss carries no compressive force. If it is shortened beyond its stress-free length, it becomes *slack* and takes up load again as soon as it is stretched. Use this option for members without compressive stiffness such as geotextiles, geogrids, cables and tie rods.

Without the option and without `f_t` the truss is linear elastic in tension and in compression.

---

## Geosynthetics

A geotextile or a geogrid in a plane strain model is a row of truss elements with `tension-only`. Manufacturers give the properties of these products per unit width: the tensile stiffness $J$ (kN/m) and the tensile strength $T_{ult}$ (kN/m). With a plane strain slice of unit thickness it is convenient to set $A = 1$ m² per metre, so that

$$
E = J , \qquad f_t = T_{ult} ,
$$

and the output variable `stress-truss` is the tensile force per unit width in kN/m. A geogrid with $J = 1000$ kN/m and a strength of 40 kN/m reads:

```numgeo
*Material, name=Geogrid-Material, phases=1
*Truss properties, tension-only
1.0, 1000.0, 40.0
```

The interaction of the layer with the soil on both faces is defined with [`*Embedded region, interaction, section=sheet`](../embedded-regions/interaction.md#geosynthetic-layers-sectionsheet). Worked examples are given in the tutorials [Pull-out test of a geogrid](../../tutorial/geosynthetics/pull-out-test.md), [Embankment with basal reinforcement](../../tutorial/geosynthetics/reinforced-embankment.md) and [Geogrid-reinforced retaining wall built in layers](../../tutorial/geosynthetics/reinforced-wall.md).

!!! note "Choice of the stiffness"

    The tensile stiffness of geosynthetics depends on the strain, the loading time and the temperature. `E` is a constant: use the secant stiffness for the strain and the loading time which are relevant for the problem, e.g. $J_{2\,\%}$ from the isochronous curve of the design life.

!!! note "Convergence"

    A slack element and an element which has reached its strength have practically no stiffness (a residual stiffness of $10^{-6}E$ keeps the system of equations regular). The nodes of such elements must therefore be held by something else, e.g. by the interface springs of an embedded layer. Steps in which many elements change their state, in particular when a slack layer is tensioned again, may need small increments: allow the automatic time incrementation to reduce the increment (minimum increment well below the initial one).

!!! warning "Limitations"

    - The strength is elastic - perfectly plastic: there is no softening and no rupture. An element at its strength keeps the force $A\,f_t$ however far it is stretched; check the strain (`strain-truss`, `pstrain-truss`) against the strain at rupture of the product.
    - The elements are geometrically linear. The membrane effect of a layer which deflects by a large amount (e.g. over a void or between piles) is not included.
