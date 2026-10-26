# Anisotropic Viscous ISA (AVISA)

Anisotropic Viscous ISA model after Tafili & Triantafyllidis (2020)[@Tafili20b], an advanced hypoplastic model for clayey soils incorporating effects of anisotropy and viscosity. The model is well suited for both, monotonic and cyclic loading. The base implementation has been provided by Merita Tafili. The numgeo keyword reads:

```numgeo 
*Mechanical = AVISA
lambda (-), kappa (-), e_{i0} (-), nu (-), alpha (-), M_c (-), f_{b0} (-), I_v (-)
R (-), m_R (-), beta_0 (-), chi_0 (-), chi_max (-), C_a (-) , d (-), F^ISA (-)
K^w (F/A), istep_undrained
```

The material parameters of the AVISA model are given in the following.  

- $\lambda$ is the compression index. This parameter has no unit. Typical range: $10^{-6}-1$.

- $\kappa$ is the swelling index. This parameter has no unit. Typical range: $10^{-7}-0.6$.

- The void ratio $e_{i0}$ correspond to the maximum void ratio at pressure $p$ = 1 F/A. This parameter has no unit. Typical range: $0.5-5$.

- $\nu$ is the Poisson's ratio. This parameter has no unit. Typical range: $0-0.5$.

- $\alpha$ is the anisotropy factor. This parameter has no unit. Typical range: $0-5$.

- $M_c$ is the slope of the critical state line. This parameter has no unit. Typical range: $0.5-2$.

- $f_{b0}$ is the loading surface factor. This parameter has no unit. Typical range: $1-3$.

- $I_v$ is the viscosity index. This parameter has no unit. Typical range: $0-2$.

- $m_R$ and $m_T$ govern the increase of the stiffness due to changes of the direction of the strain path. This parameter has no unit and is only used if the IGS model is used ($F^{ISA}=1$). Typical range: $1-7$.

- $R$ is the radius of intergranular strain. This parameter has no unit. Typical range: $10^{-6}-10^{-2}$.

- $\beta_{h0}$ and $\beta_{hmax}$ are the hardening parameter of the intergranular strain and describes the evolution of the intergranular strain tensor along a strain path. These parameters have no unit. Typical range: $0-2$.

- $\chi_0$ and $\chi_{max}$ are the minimum and maximum intergranular strain exponent. These parameters have no unit. Typical range: $1-10$ for $\chi_0$ and $20 - 50$ for $\chi_{max}$.

- $C^{acc}$ is the accumulation rate factor. This parameter has no unit. Typical range: $0-0.2$.

- $d$ is the intergranular strain bounding surface radius. This parameter has no unit. Typical range: $1-10$.

- $F^{ISA}$ is a switch that decides whether the ISA ($F^{ISA}=1$) model should be used or not $F^{ISA}=0$.

- $\bar{K}^w$ is the bulk modulus of pore water for locally undrained simulations (and only for those). The parameter is not mandatory and zero per default.

## State variables {#state-variables-6 .unnumbered}

In addition to the (effective) stress, the AVISA constitutive model makes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are
contained in the model:

- Void ratio: $e$, `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort. In general, the initial void ratio should be prescribed using the following expression: $e_0 = e_{i0}- \lambda \cdot ln(\text{OCR}_0\cdot p_0)$. Therein, $\text{OCR}_0$ is the initial overconsolidation ratio and $p_0$ is the initial mean effective stress.

- Intergranular strain anisotropy: $R_{ij}$, `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`. Only in combination with the intergranular strain extension. Prescribing $R_0$ is not mandatory, if omitted, $R_{ij}$ is assumed. $R_{ii} = R_0 / \sqrt{3}$ corresponds to an isotropically consolidated state.

The state variables can be initialized in two different ways:

-   Using the `*Initial conditions, type = state variables` command in the input file, e.g.

    `*Initial conditions, type = state variables`  
    `element_set_name, void_ratio, <value>`  
    `**`  
    `element_set_name, int_strain11, <value>`  
    `element_set_name, int_strain22, <value>`  
    `element_set_name, int_strain33, <value>`  

-   Using the interface for user-defined initial state variables. In
    this approach, the vector holding the state variables is filled
    directly in a Fortran [user routine](../../user/initial-statev.md). The position of the state
    variables in the associated vector are as follows: `statev(1)` =
    $e$, `statev(3)` = $R_{11}$, `statev(4)` = $R_{22}$, `statev(5)` =
    $R_{33}$, `statev(6)` = $R_{12}$, `statev(7)` = $R_{23}$,
    `statev(8)` = $R_{13}$

## Additional output variables {#additional-output-variables-6 .unnumbered}

The following additional output variables are available in the `*Output` command (see [here](../../output/field.md)):

- Void ratio: `void_ratio`

- Intergranular strain: `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`.

- Over consolidation ratio: `ocr`.

## References
