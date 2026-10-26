# Hydraulic constitutive model

```numgeo 
*Material, ...
...
*Hydraulic = <hydraulic model> [,Swr=residual water saturation]
*<parameter 1>, ... , <parameter n>
[*Jacobian = <method>]
[*Hydraulic iteration = Newton | Modified-Picard]
...
``` 

Use this keyword to specify the hydraulic model to be used for the calculation of the degree of saturation. The subsequent lines `<parameter 1>, ... , <parameter n>}` depend on the constitutive model chosen. A list of available soil-water retention models implemented in numgeo is given in Section [Soil-water retention models](#soil-water-retention-models). In addition, optional settings (given in squared brackets `[...]` in above keyword snipped) can be prescribed by the user as outlined in Section [Optional settings](#optional-settings).

The `*Hydraulic` keyword is only allowed for materials with more than one phase.

## Soil-water retention models

**Model** | **Dependence** | **Hysteresis**
---|---|---
[Van Genuchten](./van-genuchten.md) | capillary pressure $p^c$ | no
[Brooks & Corey](./brooks-corey.md) | capillary pressure $p^c$ | no
[Fredlund & Xing](./fredlund-xing.md) | capillary pressure $p^c$ | no
[Exponential model](./exponential.md) | capillary pressure $p^c$ | no
[Gallipoli Model](./gallipoli-model.md) | capillary pressure $p^c$, void ratio $e$ | no
[Karlsruhe Model](./karlsruhe-model.md) | capillary pressure $p^c$, void ratio $e$ | yes

## Optional settings

In addition to the selection of the constitutive model for the soil-water retention behaviour, users can specify the following optional settings:

* Residual water saturation $S^{wr}$ 

    $S^{wr}$ can be prescribed by adding `[,Swr=<residual water saturation>]` after the model specification. $S^{wr}$ is given as fraction of 1, e.g. $S^{wr}=0.32$ for a residual degree of saturation of 32 %. If this parameter is omitted, $S^{wr}=0$ is assumed.

* Jacobian $d(S^w)/d(s)$

    The iteration matrix can use different approximations of $d(S^w)/d(s)$. The default remains the "smoothed derivative". Add `*Jacobian = <method>` after the hydraulic material parameters to select the method. These choices concern the nonlinear linearisation; they are not different physical retention curves.
    
    The `method`s available in numgeo are:

    - `Analytical`: The analytical derivative of the respective constitutive model for the current suction $s$ is used. 

    - `Smoothed`: The analytical derivation is smoothed by evaluating the Jacobian over 10 substeps. This is the default option. 
    
    - `Chord-Slope`: A chord-slope approximation of the Jacobian for the current values of $d (S^w)$ and $d(s)$ is used. 

    - `Time-Step-Centered`: The analytical derivation is averaged for the current suction $s$ and previous suction $s_0$. 

* Hydraulic iteration

    `*Hydraulic iteration=Modified-Picard` omits mobility derivatives from the element matrix while updating mobility in the residual at every iterate. This is the default. `*Hydraulic iteration=Newton` includes mobility derivatives using the selected retention and relative-permeability Jacobians. Near full saturation the slope of the relative permeability of van Genuchten type is unbounded, and Newton can then need considerably more iterations and increments than Modified-Picard (seepage benchmarks with a wetting front: up to three times as many). The option is independent of the hydraulic `*Jacobian` option and uses the same global solve and time-increment controller. See [Nonlinear solution of unsaturated flow](../../../theory/solution-method/unsaturated-flow.md).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/index.md)

</div>
