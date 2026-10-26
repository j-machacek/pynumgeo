# Mechanical viscosity:

```numgeo 
*Material, ...
*Mechanical viscosity = <mechanical viscosity model>
<parameter 1>, ... , <parameter n>
``` 

This parameter is used to overlay the mechanical model with an additional viscous constitutive model. This can improve the numerical stability for very fast deformations at vanishing mean effective stress (e.g. $p = |\text{tr}(\boldsymbol{\sigma})/3| > -1$ kPa). The subsequent lines `<parameter 1>, ... , <parameter n>` depend on the model chosen:

- `*Mechanical viscosity=linear`: for the linear viscosity model, the viscous stress is calculated from $\boldsymbol{\sigma}^{{\scriptsize vis}} = \lambda \boldsymbol{1} \text{tr}(\dot{\boldsymbol{\varepsilon}}) + 2\mu \dot{\boldsymbol{\varepsilon}}$. To ensure a smooth transition, $\lambda$ and $\mu$ are assumed to increase linearly with vanishing mean effective stress $p$. Details are provided in the [Theory Manual](../../theory/constitutive-models/mechanical-models/linear-viscosity.md). The command takes the following arguments:

    ```numgeo 
    *Mechanical viscosity=linear
    p_0, p_1, lambda_0, lambda_1, mu_0, mu_1
    ``` 

    where $\lambda_{0}$ and $\lambda_{1}$ in (F/A$\cdot$s), $\mu_{0}$ and $\mu_{1}$ in (F/A$\cdot$s) are material parameters.

    The (viscous) stresses from this phantom viscosity can be requested for output using the following keyword `PHANTOM-VISCOSITY`. In Paraview these stresses are labeled `Stress-Vis 11`, ...

-   `*Mechanical viscosity=bulk_explicit`:
    introduces damping in explicit dynamics in terms of volumetric straining. It is switched on by default in explicit analyses, but the two parameters $a,b$ associated with this type of viscosity can be modified. The default values are $a= 0.06$ and $b=1.2$.