# Hardening-Soil (MN, Bricks)

`Hardening-Soil-MN-Bricks` extends [`Hardening-Soil-MN`](hardening_soil_MN.md) with the **BRICK** small-strain stiffness formulation of Cudny & Truty (2020), based on the nested strain-space multi-surface concept of Simpson (1992). All plasticity mechanisms — the Matsuoka–Nakai shear cone and failure surface, the elliptical volumetric cap, the non-associated flow rule and the tensile apex — are identical to `Hardening-Soil-MN`; only the elastic stiffness and the hardening rate are affected. In addition to the parameters of the base model, it uses:

- A small-strain reference shear modulus $G_0^{ref}$ that governs the (much stiffer) tangent stiffness immediately after a strain reversal.
- A threshold shear strain $\gamma_{0.7}$ that controls how quickly this small-strain stiffness degrades towards $G_{ur}^{ref} = E_{ur}^{ref}/(2(1+\nu_{ur}))$ as straining continues.

Once the strain has moved far enough from the last reversal for all bricks to be dragged, the elastic stiffness equals that of `Hardening-Soil-MN`; the hardening is enhanced until the stiffness has degraded fully once (see [Theory](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN-bricks.md#hardening-enhancement)).

!!! Info "Credits"

    The initial implementation of the underlying Hardening-Soil-MN model was provided by Leonardo José Cocco. The BRICK small-strain extension is based on the base subroutines for string properties and brick movement kindly provided by Marcin Cudny. Both have since undergone refactoring and further development for integration into numgeo.

## Input syntax

```numgeo
*Mechanical = Hardening-Soil-MN-Bricks
E50 (F/A), Eoed (F/A), Eur (F/A), m (-), c (F/A), phi (deg), psi (deg), nu_ur (-)
pref (F/A), K0nc (-), Rf (-), Eiref (F/A), alpha (-), Hpp (F/A), gamma_07 (-), G0 (F/A)
```

### Material parameters

The material parameters for `Hardening-Soil-MN-Bricks` are the 14 parameters of `Hardening-Soil-MN`, extended by two small-strain parameters:

|  # |      Symbol     | Unit | Description                                                                                                                                                                                             |
| :-: | :-------------: | :--: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1 |  $E_{50}^{ref}$ |  F/A | Triaxial secant stiffness for primary loading (50 % of the strength) at $\sigma_3 = p_{ref}$. Target of the automatic determination of $E_i^{ref}$, and used in the exponent of the hardening enhancement. |
|  2 | $E_{oed}^{ref}$ |  F/A | Oedometric tangent stiffness for primary loading at $\sigma_v = p_{ref}$. Used only for the automatic determination of $\alpha$ and $H_{pp}$.                                                           |
|  3 |  $E_{ur}^{ref}$ |  F/A | Unloading/reloading stiffness at $\sigma_3 = p_{ref}$. Also sets the fully degraded (large-strain) reference shear modulus $G_{ur}^{ref}=E_{ur}^{ref}/(2(1+\nu_{ur}))$.                               |
|  4 |       $m$       |   –  | Exponent controlling the stress dependence of the stiffness.                                                                                                                                           |
|  5 |    $c_{eff}$    |  F/A | Effective cohesion (typically $0$ for sands).                                                                                                                                                           |
|  6 |    $\varphi$    |  deg | Peak friction angle (triaxial compression).                                                                                                                                                             |
|  7 |      $\psi$     |  deg | Dilatancy angle at failure. Use $\psi = 0$ for no dilation at failure.                                                                                                                                  |
|  8 |    $\nu_{ur}$   |   –  | Poisson’s ratio for unloading/reloading. Constant across the small-strain degradation (only the shear modulus degrades).                                                                               |
|  9 |    $p_{ref}$    |  F/A | Reference stress of the stiffness moduli (typically $100$ kPa). The moduli depend on the minor compressive principal stress $\sigma_3$, not on the mean stress.                                       |
| 10 |    $K_0^{nc}$   |   –  | At-rest earth pressure coefficient for normally consolidated conditions. Used only for the automatic determination of $\alpha$ and $H_{pp}$; it does not set initial stresses.                         |
| 11 |      $R_f$      |   –  | Failure ratio $q_f/q_a$ of the hyperbolic stress–strain relation (typical range: $0.8$–$0.95$).                                                                                                         |
| 12 |   $E_i^{ref}$   |  F/A | Initial tangent stiffness in triaxial loading at $\sigma_3 = p_{ref}$. Set to `0` to let numgeo determine it automatically from $E_{50}^{ref}$. |
| 13 |     $\alpha$    |   –  | Cap shape parameter (controls the steepness of the cap in $p$–$q$ space). Set $\alpha$ and $H_{pp}$ both to `0` to let numgeo determine them automatically from $E_{oed}^{ref}$ and $K_0^{nc}$.        |
| 14 |     $H_{pp}$    |  F/A | Cap hardening parameter, the ratio of the increase of the preconsolidation stress to the plastic volumetric strain of the cap at $\sigma_3 = p_{ref}$. Set $\alpha$ and $H_{pp}$ both to `0` to let numgeo determine them automatically. |
| 15 |  $\gamma_{0.7}$ |   –  | Shear strain at which the small-strain secant shear modulus has decayed to $70\,\%$ of $G_0$ (shear strain invariant $\gamma = \tfrac32\varepsilon_q$, i.e. $\gamma = \lvert\varepsilon_1 - \varepsilon_3\rvert$ in triaxial compression). |
| 16 |     $G_0^{ref}$ |  F/A | Small-strain shear modulus at $\sigma_3 = p_{ref}$, valid immediately after a strain reversal.                                                                                                          |

!!! warning "$\gamma_{0.7}$ is not the HS-Small value"

    The secant modulus of this model passes through $0.700\,G_0$ at $\gamma_{0.7}$, that of HS-Small (Benz 2007) through $0.722\,G_0$. To reproduce an HS-Small parameter $\gamma_{0.7}^{HSS}$ enter $\gamma_{0.7} = 1.113\,\gamma_{0.7}^{HSS}$ (see [Theory](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN-bricks.md#discretisation-of-the-stiffness-degradation-curve)).

!!! note "Automatic determination of cap parameters"

    As for the base model, if both $\alpha = 0$ and $H_{pp} = 0$ are given, numgeo determines both parameters such that the model reproduces the target oedometric stiffness $E_{oed}^{ref}$ and the target $K_0^{nc}$ under oedometric loading at the reference stress; if only one of them is zero, no determination takes place. The determination always targets the fully degraded (base-model) response, independently of $\gamma_{0.7}$ and $G_0^{ref}$. Not every combination can be reproduced; if the determination fails, numgeo reports the limits of the reachable targets and stops (see [Reachable targets](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#reachable-targets)).

!!! note "Automatic determination of $E_i^{ref}$"

    As for the base model, $E_i^{ref} = 0$ lets numgeo determine $E_i^{ref}$ such that a simulated drained triaxial compression test at $\sigma_3 = p_{ref}$ from the isotropic, normally consolidated state reproduces $E_{50}^{ref}$; together with $\alpha = 0$ and $H_{pp} = 0$ all three constants are determined, so that $E_{50}^{ref}$, $E_{oed}^{ref}$ and $K_0^{nc}$ are reproduced (see [Hardening-Soil-MN](hardening_soil_MN.md#material-parameters)). The test is simulated with the fully degraded (base-model) response, independently of $\gamma_{0.7}$ and $G_0^{ref}$: the determined constants are those of `Hardening-Soil-MN` for the same parameters. A given $E_i^{ref} > 0$ is used as it is.

!!! warning "Parameter validity"

    $G_0^{ref}$ must not be smaller than $G_{ur}^{ref}=E_{ur}^{ref}/(2(1+\nu_{ur}))$ — i.e. the small-strain stiffness cannot be softer than the unloading/reloading stiffness. If $G_0^{ref} > G_{ur}^{ref}$, $\gamma_{0.7}$ must be positive. Otherwise numgeo stops with an error message. Setting $G_0^{ref}=G_{ur}^{ref}$ reduces the model to `Hardening-Soil-MN` (up to round-off) and is a convenient way to disable the small-strain extension without switching models.

The note on the initial state of [Hardening-Soil-MN](hardening_soil_MN.md#material-parameters) applies.

### Example

The example below reproduces the glacial till parameters used in Fig. 6 of Cudny & Truty (2020):

```numgeo
*Mechanical = Hardening-Soil-MN-Bricks
** E50, Eoed, Eur, me, c, phi, psi, nu_ur
8.5d3, 6.15d3, 25.75d3, 0.7, 6, 28, 6, 0.29
** pref, K0nc, Rf, Eiref, alpha, Hpp, gamma_07, G0
100, 0.8, 0.9, 15.46d3, 0.515, 9.866d3, 3e-4, 60e3
```

## Optional parameters

```numgeo
*Optional mechanical parameter
tangent, <value>
```

* `tangent`: tangent operator (material Jacobian) of the equilibrium iteration. Default: `1`.
    * `tangent = 1`: elastic operator of the stress update with the small-strain stiffness $E_t$ at the end of the increment. Increments with plastic strains converge linearly.
    * `tangent = 2`: consistent (algorithmic) tangent, the derivative of the complete stress update (including the brick predictor) with respect to the strain increment, computed by finite differences as in [Hardening-Soil-MN](hardening_soil_MN.md#optional-parameters). Elastic increments without sub-steps (strain increments up to $4\times10^{-5}$) use the elastic operator with the small-strain stiffness $E_t$ of the increment, the derivative of their stress update.

The remarks on symmetry, cost and robustness of [Hardening-Soil-MN](hardening_soil_MN.md#optional-parameters) apply. In addition, the stress update can change discontinuously with the strain increment where a brick becomes active within a sub-step (see [Theory](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN-bricks.md#integration-algorithm-notes)); the equilibrium iteration cannot converge below such a jump with either tangent.

```numgeo
*Optional mechanical parameter
e_max, <value>
```

* `e_max`: dilatancy cut-off with the maximum void ratio $e_{max}$, default `0` (no cut-off). Input, initial void ratio and behaviour as for [Hardening-Soil-MN](hardening_soil_MN.md#optional-parameters).

As for the base model, the optional parameter `min_pressure` is accepted but has no effect.

!!! warning "Small-strain stiffness and increment size"

    Strain increments are integrated in sub-steps of up to $4\times10^{-5}$ (strain norm). All bricks whose strings become taut within a sub-step are dragged in one brick update, and the stiffness after this update is used for the whole sub-step, so that the small-strain stiffness is underestimated at practical increment sizes: with $G_0^{ref} = 3\,G_{ur}^{ref}$ and $\gamma_{0.7} = 2\times10^{-4}$ the deviatoric stress of a drained triaxial test at 100 kPa is 8 % too low at 0.05 % axial strain and 1 % too low at 0.5 %. The response converges with smaller increments; use them where the response at very small strains matters.

## Model-specific output parameters

* `Void_Ratio`: void ratio (updated with the volumetric strain only with the dilatancy cut-off, `e_max` > 0, which requires an initial value).
* `Strain-Dev-Pl`: hardening variable $\gamma^p$ of the cone, as for [Hardening-Soil-MN](hardening_soil_MN.md#model-specific-output-parameters); its increase is enhanced by the factor $H_i$ in the small-strain range.
* `Stress-Precon`: preconsolidation stress $p_p$ (cap hardening variable).
* `Stress-P`: mean effective stress $p$ (compression positive).
* `Stress-Q`: deviatoric stress $q$.

!!! note "Internal state variables"

    Beyond the five output quantities above, this model uses 73 state variables per integration point to track the internal BRICK state (man and brick strain history); numgeo allocates them automatically. The additional variables (including the stiffness ratio $G_m$ and the number of dragged bricks) are not available as output.

---

<div class="grid cards" markdown>

-   :material-arrow-left:{ .lg .middle } __Base model__

    ---

    [:octicons-arrow-right-24: Hardening-Soil-MN](hardening_soil_MN.md)

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN-bricks.md)


</div>

---
