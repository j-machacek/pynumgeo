# Hardening-Soil (MN, Bricks)

`Hardening-Soil-MN-Bricks` extends [`Hardening-Soil-MN`](hardening_soil_MN.md) with the **BRICK** small-strain stiffness formulation of Cudny & Truty (2020), based on the nested strain-space multi-surface concept of Simpson (1992). All plasticity mechanisms — the Matsuoka–Nakai shear cone, the elliptical volumetric cap, the non-associative flow rule and the tensile-apex cut-off — are identical to `Hardening-Soil-MN`; only the elastic stiffness and the hardening rate are affected. In addition to the parameters of the base model, it uses:

- A small-strain reference shear modulus $G_0^{ref}$ that governs the (much stiffer) tangent stiffness immediately after a strain reversal.
- A threshold shear strain $\gamma_{0.7}$ that controls how quickly this small-strain stiffness degrades towards $E_{ur}^{ref}$ as straining continues.

Away from recent strain reversals the model reproduces the same response as `Hardening-Soil-MN`; the difference is confined to a stiffer, history-dependent elastic response within a small range of strain around the current point of last reversal.

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
|  1 |  $E_{50}^{ref}$ |  F/A | Triaxial secant stiffness for primary loading at $p = p_{ref}$.                                                                                                                                     |
|  2 | $E_{oed}^{ref}$ |  F/A | Oedometer tangent stiffness for primary loading at $p = p_{ref}$.                                                                                                                                   |
|  3 |  $E_{ur}^{ref}$ |  F/A | Unloading/reloading stiffness at $p = p_{ref}$. Also sets the fully-degraded (large-strain) reference shear modulus $G_{ur}^{ref}=E_{ur}^{ref}/2(1+\nu_{ur})$.                                       |
|  4 |       $m$       |   –  | Exponent controlling stress dependency of stiffness.                                                                                                                                                    |
|  5 |    $c_{eff}$    |  F/A | Effective cohesion used in the strength formulation (typically $0$ for sands).                                                                                                                          |
|  6 |    $\varphi$    |  deg | Peak friction angle.                                                                                                                                                                                    |
|  7 |      $\psi$     |  deg | Peak dilatancy angle. Use $\psi = 0$ for no dilation.                                                                                                                                                   |
|  8 |    $\nu_{ur}$   |   –  | Poisson’s ratio for unloading/reloading. Assumed constant across the small-strain degradation (only the shear modulus degrades).                                                                      |
|  9 |    $p_{ref}$    |  F/A | Reference mean effective stress (typical default: $100$ kPa in kPa-based unit systems).                                                                                                                 |
| 10 |    $K_0^{nc}$   |   –  | At-rest earth pressure coefficient for normally consolidated conditions.                                                                                                                                |
| 11 |      $R_f$      |   –  | Failure ratio controlling the stress level at which the secant stiffness definition reaches the failure envelope (typical range: $0.8$–$0.95$).                                                         |
| 12 |   $E_i^{ref}$   |  F/A | Initial tangent stiffness in triaxial loading at $p = p_{ref}$. If not available, a common approximation is $E_i^{ref} \approx 2E_{50}^{ref}/(2 - R_f)$.                                                |
| 13 |     $\alpha$    |   –  | Cap shape parameter (controls steepness of the cap in $p$–$q$ space). Set to `0` to let numgeo determine $\alpha$ automatically from $E_{oed}^{ref}$ and $K_0^{nc}$.                                |
| 14 |     $H_{pp}$    |  F/A | Hardening parameter relating plastic volumetric strain to the evolution of pre-consolidation stress. Set to `0` to let numgeo determine $H_{pp}$ automatically from $E_{oed}^{ref}$ and $K_0^{nc}$. |
| 15 |  $\gamma_{0.7}$ |   –  | Shear strain at which the small-strain secant shear modulus has decayed to $72.2\%$ of $G_0^{ref}$ (Hardin–Drnevich threshold strain).                                                                 |
| 16 |     $G_0^{ref}$ |  F/A | Small-strain reference shear modulus at $p = p_{ref}$, valid immediately after a strain reversal.                                                                                                      |

!!! note "Automatic determination of cap parameters"

    As for the base model, if $\alpha = 0$ and/or $H_{pp} = 0$, numgeo determines the missing parameter(s) such that the model reproduces the target oedometric stiffness $E_{oed}^{ref}$ and the target $K_0^{nc}$ under oedometric loading at the reference stress level. This optimisation always targets the fully-degraded (base-model) response, independently of $\gamma_{0.7}$ and $G_0^{ref}$.

!!! warning "Parameter validity"

    $G_0^{ref}$ must not be smaller than $G_{ur}^{ref}=E_{ur}^{ref}/2(1+\nu_{ur})$ — i.e. the small-strain stiffness cannot be softer than the unloading/reloading stiffness. If $G_0^{ref} > G_{ur}^{ref}$, $\gamma_{0.7}$ must be strictly positive. Setting $G_0^{ref}=G_{ur}^{ref}$ degenerates the model exactly to `Hardening-Soil-MN` and is a convenient way to disable the small-strain extension without switching models.

### Example

The example below reproduces the glacial till parameters used in Fig. 6 of Cudny & Truty (2020):

```numgeo
*Mechanical = Hardening-Soil-MN-Bricks
** E50, Eoed, Eur, me, c, phi, psi, nu_ur
8.5d3, 6.15d3, 25.75d3, 0.7, 6, 28, 6, 0.29
** pref, K0nc, Rf, Eiref, alpha, Hpp, gamma_07, G0
100, 0.8, 0.9, 15.46d3, 0.515, 9.866d3, 3e-4, 60e3
```

## Model-specific output parameters

* `Void_Ratio`: void ratio (only meaningful if an initial value was prescribed at the beginning of an analysis)
* `Strain-Dev-Pl`: Accumulated plastic deviatoric strain.
* `Stress-Precon`: Pre-consolidation stress (cap hardening variable).
* `Stiffness-Ratio-Gm`: Current small-strain stiffness ratio $G_m=\min\left(G_{ref,t}/G_{ur}^{ref}\right)$ over the loading history ($1 \le G_m \le G_0^{ref}/G_{ur}^{ref}$); $G_m=1$ indicates a fully degraded (base-model) response.
* `Active-Bricks`: Number of currently active (dragged) bricks, $0$–$10$; a diagnostic measure of how far the current strain state is from the last reversal.

!!! note "Internal state variables"

    Beyond the five output quantities above, this model requires at least 73 state variable slots per integration point to track the internal BRICK state (man and brick strain history); numgeo allocates these automatically. The additional slots are internal bookkeeping and are not exposed as named output channels.

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
