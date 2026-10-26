# Hardening-Soil (MN)

`Hardening-Soil-MN` is an elastoplastic soil model follows the Hardening Soil (HS) concept with stress-dependent stiffness and a Matsuoka–Nakai (MN) failure surface. It combines:

- Stress-dependent stiffness governed by a power law with exponent $m$ and reference moduli at $p=p_{ref}$.
- Different stiffness for primary loading ($E_{50}^{ref}$, $E_{oed}^{ref}$), unloading/reloading ($E_{ur}^{ref}$), and the initial tangent ($E_i^{ref}$).
- Frictional strength and dilatancy described by $\varphi$ and $\psi$.
- A cap mechanism controlled by $\alpha$ and $H_{pp}$ (pre-consolidation stress evolution).

The Matsuoka-Nakai surface introduces Lode-angle dependence and provides a smooth strength description beyond Mohr–Coulomb, which improves robustness for general 3D stress paths.

!!! Info "Credits"

    The initial implementation of this model was provided by [Leonardo José Cocco](https://fcefyn.unc.edu.ar/perfiles/lcoco). It has since undergone substantial refactoring and further development for integration into numgeo, including improvements to code structure, numerical robustness, and performance.

!!! tip "Small-strain stiffness"

    `Hardening-Soil-MN` uses stress-dependent, but strain-history-independent stiffness moduli. If a stiffer response is required immediately after strain reversals (small-strain stiffness), use [Hardening-Soil-MN-Bricks](hardening_soil_MN_bricks.md), which extends this model with the BRICK small-strain stiffness formulation.

## Input syntax

```numgeo
*Mechanical = Hardening-Soil-MN
E50 (F/A), Eoed (F/A), Eur (F/A), m (-), c (F/A), phi (deg), psi (deg), nu_ur (-)
pref (F/A), K0nc (-), Rf (-), Eiref (F/A), alpha (-), Hpp (F/A)
```

### Material parameters

The material parameters for `Hardening-Soil-MN` are:

|  # |      Symbol     | Unit | Description                                                                                                                                                                                             |
| :-: | :-------------: | :--: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1 |  $E_{50}^{ref}$ |  F/A | Triaxial secant stiffness for primary loading at $p = p_{ref}$.                                                                                                                                     |
|  2 | $E_{oed}^{ref}$ |  F/A | Oedometer tangent stiffness for primary loading at $p = p_{ref}$.                                                                                                                                   |
|  3 |  $E_{ur}^{ref}$ |  F/A | Unloading/reloading stiffness at $p = p_{ref}$.                                                                                                                                                         |
|  4 |       $m$       |   –  | Exponent controlling stress dependency of stiffness.                                                                                                                                                    |
|  5 |    $c_{eff}$    |  F/A | Effective cohesion used in the strength formulation (typically $0$ for sands).                                                                                                                          |
|  6 |    $\varphi$    |  deg | Peak friction angle.                                                                                                                                                                                    |
|  7 |      $\psi$     |  deg | Peak dilatancy angle. Use $\psi = 0$ for no dilation.                                                                                                                                                   |
|  8 |    $\nu_{ur}$   |   –  | Poisson’s ratio for unloading/reloading.                                                                                                                                                                |
|  9 |    $p_{ref}$    |  F/A | Reference mean effective stress (typical default: $100$ kPa in kPa-based unit systems).                                                                                                                 |
| 10 |    $K_0^{nc}$   |   –  | At-rest earth pressure coefficient for normally consolidated conditions.                                                                                                                                |
| 11 |      $R_f$      |   –  | Failure ratio controlling the stress level at which the secant stiffness definition reaches the failure envelope (typical range: $0.8$–$0.95$).                                                         |
| 12 |   $E_i^{ref}$   |  F/A | Initial tangent stiffness in triaxial loading at $p = p_{ref}$. If not available, a common approximation is $E_i^{ref} \approx 2E_{50}^{ref}/(2 - R_f)$.                                                |
| 13 |     $\alpha$    |   –  | Cap shape parameter (controls steepness of the cap in $p$–$q$ space). Set to `0` to let numgeo determine $\alpha$ automatically from $E_{oed}^{ref}$ and $K_0^{nc}$.                                |
| 14 |     $H_{pp}$    |  F/A | Hardening parameter relating plastic volumetric strain to the evolution of pre-consolidation stress. Set to `0` to let numgeo determine $H_{pp}$ automatically from $E_{oed}^{ref}$ and $K_0^{nc}$. |

!!! note "Automatic determination of cap parameters"

    If $\alpha = 0$ and/or $H_{pp} = 0$, numgeo determines the missing parameter(s) such that the model reproduces the target oedometric stiffness $E_{oed}^{ref}$ and the target $K_0^{nc}$ under oedometric loading at the reference stress level.


### Example

```numgeo
*Mechanical = Hardening-Soil-MN
** E50, Eoed, Eur, me, c, phi, psi, nu_ur
30d3, 30d3, 90d3, 0.55, 0, 42, 16, 0.25
** pref, K0nc, Rf, Eiref, alpha, Hpp
100, 0.4, 0.9, 65d3, 1.46, 72028
```

## Model-specific output parameters

* `Void_Ratio`: void ratio (only meaningful if an initial value was prescribed at the beginning of an analysis)
* `Strain-Dev-Pl`: Accumulated plastic deviatoric strain.
* `Stress-Precon`: Pre-consolidation stress (cap hardening variable).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md)

-   :material-update:{ .lg .middle } __Benchmark manual__

    ---

    [:octicons-arrow-right-24: Validation](../../../benchmark/constitutive-models/hardening-soil-MN.md)

-   :material-cube-outline:{ .lg .middle } __Small-strain extension__

    ---

    [:octicons-arrow-right-24: Hardening-Soil-MN-Bricks](hardening_soil_MN_bricks.md)

</div>

---
