# Hardening-Soil (MN)

`Hardening-Soil-MN` is an elastoplastic soil model that follows the Hardening Soil (HS) concept with a Matsuoka–Nakai (MN) failure surface. It combines:

- Stress-dependent stiffness governed by a power law with exponent $m$ and reference moduli at the reference stress $p_{ref}$.
- Different stiffness for primary loading (initial tangent stiffness $E_i^{ref}$ with failure ratio $R_f$) and for unloading/reloading ($E_{ur}^{ref}$, $\nu_{ur}$).
- Frictional strength and dilatancy described by $\varphi$, $c$ and $\psi$, with a Rowe-type stress–dilatancy relation below failure.
- A cap mechanism controlled by $\alpha$ and $H_{pp}$ (evolution of the preconsolidation stress).
- Automatic determination of the internal constants $E_i^{ref}$, $\alpha$ and $H_{pp}$ from the targets $E_{50}^{ref}$, $E_{oed}^{ref}$ and $K_0^{nc}$.

The Matsuoka–Nakai surface coincides with the Mohr–Coulomb surface in triaxial compression and extension and lies outside it for intermediate Lode angles, e.g. in plane strain. It is smooth, which avoids the corners of the Mohr–Coulomb surface in general 3D stress paths.

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
|  1 |  $E_{50}^{ref}$ |  F/A | Triaxial secant stiffness for primary loading (50 % of the strength) at $\sigma_3 = p_{ref}$. Target of the automatic determination of $E_i^{ref}$; without effect if $E_i^{ref} > 0$ is given. |
|  2 | $E_{oed}^{ref}$ |  F/A | Oedometric tangent stiffness for primary loading at $\sigma_v = p_{ref}$. Used only for the automatic determination of $\alpha$ and $H_{pp}$.                                                           |
|  3 |  $E_{ur}^{ref}$ |  F/A | Unloading/reloading stiffness at $\sigma_3 = p_{ref}$.                                                                                                                                                  |
|  4 |       $m$       |   –  | Exponent controlling the stress dependence of the stiffness.                                                                                                                                           |
|  5 |    $c_{eff}$    |  F/A | Effective cohesion (typically $0$ for sands).                                                                                                                                                           |
|  6 |    $\varphi$    |  deg | Peak friction angle (triaxial compression).                                                                                                                                                             |
|  7 |      $\psi$     |  deg | Dilatancy angle at failure. Use $\psi = 0$ for no dilation at failure.                                                                                                                                  |
|  8 |    $\nu_{ur}$   |   –  | Poisson’s ratio for unloading/reloading.                                                                                                                                                                |
|  9 |    $p_{ref}$    |  F/A | Reference stress of the stiffness moduli (typically $100$ kPa). The moduli depend on the minor compressive principal stress $\sigma_3$, not on the mean stress.                                       |
| 10 |    $K_0^{nc}$   |   –  | At-rest earth pressure coefficient for normally consolidated conditions. Used only for the automatic determination of $\alpha$ and $H_{pp}$; it does not set initial stresses.                         |
| 11 |      $R_f$      |   –  | Failure ratio $q_f/q_a$ of the hyperbolic stress–strain relation (typical range: $0.8$–$0.95$).                                                                                                         |
| 12 |   $E_i^{ref}$   |  F/A | Initial tangent stiffness in triaxial loading at $\sigma_3 = p_{ref}$. Set to `0` to let numgeo determine it automatically from $E_{50}^{ref}$. |
| 13 |     $\alpha$    |   –  | Cap shape parameter (controls the steepness of the cap in $p$–$q$ space). Set $\alpha$ and $H_{pp}$ both to `0` to let numgeo determine them automatically from $E_{oed}^{ref}$ and $K_0^{nc}$.        |
| 14 |     $H_{pp}$    |  F/A | Cap hardening parameter, the ratio of the increase of the preconsolidation stress to the plastic volumetric strain of the cap at $\sigma_3 = p_{ref}$. Set $\alpha$ and $H_{pp}$ both to `0` to let numgeo determine them automatically. |

!!! note "Automatic determination of cap parameters"

    If both $\alpha = 0$ and $H_{pp} = 0$ are given, numgeo determines both parameters such that the model reproduces the target oedometric stiffness $E_{oed}^{ref}$ and the target $K_0^{nc}$ under oedometric loading at the reference stress, and reports the values in a warning. If only one of them is zero, no determination takes place and the zero value is used: give both or neither.

    Not every combination can be reproduced: $E_{oed}^{ref}$ must be smaller than the oedometric stiffness without plastic cap strains, and $K_0^{nc}$ must not be smaller than the $K_0$ obtained with a purely volumetric cap flow. If the determination fails, numgeo reports both limits and which target cannot be reached, and stops (see [Reachable targets](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#reachable-targets)).

!!! note "Automatic determination of $E_i^{ref}$"

    If $E_i^{ref} = 0$ is given, numgeo determines $E_i^{ref}$ such that a simulated drained triaxial compression test at $\sigma_3 = p_{ref}$, starting from the isotropic, normally consolidated state, reproduces $E_{50}^{ref}$ as its secant modulus at 50 % of the strength, and reports the value in a warning. If $\alpha = 0$ and $H_{pp} = 0$ are given as well, all three constants are determined together, so that $E_{50}^{ref}$, $E_{oed}^{ref}$ and $K_0^{nc}$ are reproduced. With the determined constants, element tests reproduce $E_{50}^{ref}$ within 0.01 %, $E_{oed}^{ref}$ within 0.15 % and $K_0^{nc}$ within 0.03 % (six parameter sets). The determination takes a fraction of a second to a few seconds per material. If no $E_i^{ref}$ reproduces $E_{50}^{ref}$ (e.g. $E_{50}^{ref}$ too large compared with $E_{ur}^{ref}$), numgeo reports this and stops (see [Initial stiffness](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#initial-stiffness)).

!!! warning "A given $E_i^{ref}$ and $E_{50}^{ref}$"

    If $E_i^{ref} > 0$ is given, it is used as it is and $E_{50}^{ref}$ has no effect on the result. The hyperbola alone gives $E_i^{ref} = 2E_{50}^{ref}/(2-R_f)$, but in a drained triaxial test from an isotropic, normally consolidated state the cap yields during shearing: with this value the simulated secant modulus at 50 % of the strength is 12 to 27 % below $E_{50}^{ref}$ (about 3 % below with the cap far away). The automatically determined $E_i^{ref}$ is 1.2 to 1.6 times this value in the tested parameter sets.

!!! note "Initial state"

    In the first increment of the analysis the cone and the cap are placed through the initial stress, i.e. the soil is normally consolidated. A larger preconsolidation stress $p_p$ (mean stress at which the cap meets the isotropic axis) can be prescribed with the state variable `stress-precon` ([`*Initial conditions, type=state variables`](../../initial-conditions/state-variables.md)); values $p_p \le 0$ are replaced by the normally consolidated one.

### Example

With $E_i^{ref}$, $\alpha$ and $H_{pp}$ determined automatically from $E_{50}^{ref}$, $E_{oed}^{ref}$ and $K_0^{nc}$ (numgeo reports $E_i^{ref} = 67066$, $\alpha = 1.420$ and $H_{pp} = 75338$ for this set):

```numgeo
*Mechanical = Hardening-Soil-MN
** E50, Eoed, Eur, me, c, phi, psi, nu_ur
30d3, 30d3, 90d3, 0.55, 0, 42, 16, 0.25
** pref, K0nc, Rf, Eiref, alpha, Hpp
100, 0.4, 0.9, 0, 0, 0
```

With prescribed constants:

```numgeo
*Mechanical = Hardening-Soil-MN
** E50, Eoed, Eur, me, c, phi, psi, nu_ur
30d3, 30d3, 90d3, 0.55, 0, 42, 16, 0.25
** pref, K0nc, Rf, Eiref, alpha, Hpp
100, 0.4, 0.9, 65d3, 1.46, 72028
```

## Optional parameters

```numgeo
*Optional mechanical parameter
tangent, <value>
```

* `tangent`: tangent operator (material Jacobian) of the equilibrium iteration. Default: `1`.
    * `tangent = 1`: elastic operator of the stress update. Increments with plastic strains converge linearly.
    * `tangent = 2`: consistent (algorithmic) tangent, i.e. the derivative of the complete stress update with respect to the strain increment, computed by finite differences: forward differences, and central differences where the two largest principal stresses are equal (see [Tangent operator](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#tangent-operator)). Where the stress update is smooth, increments with plastic strains converge quadratically. Elastic increments without sub-steps (strain increments up to $4\times10^{-5}$) use the elastic operator.

The consistent tangent is unsymmetric (non-associated flow); the default solver PARDISO solves unsymmetric systems. It can be indefinite close to the apex and on the failure surface, where it is in general not elliptic for $\psi < \varphi$: once a failure zone has formed, the equilibrium iteration with `tangent = 2` can diverge where `tangent = 1` still converges linearly. A plastic integration point costs 4 (2D, axisymmetric) or 6 (3D) additional stress updates per iteration, twice as many with central differences; with sub-steps (strain increments above $4\times10^{-5}$, with smaller sub-steps for a trial stress beyond the failure surface) an iteration can take several times longer than with `tangent = 1`. Whether the smaller number of iterations outweighs this depends on the analysis, and the results of both settings can differ within the convergence tolerance. Compare both settings for a new type of analysis.

```numgeo
*Optional mechanical parameter
e_max, <value>
```

* `e_max`: dilatancy cut-off (as the dilatancy cut-off of the Hardening Soil model in PLAXIS): maximum void ratio $e_{max}$, i.e. the void ratio of the critical state. Default: `0` (no cut-off). With $e_{max} > 0$ the void ratio is updated from the volumetric strain, $e_{n+1} = (1+e_n)\exp(\Delta\varepsilon_v) - 1$ per increment (dilation positive), and the mobilised dilatancy angle is zero in an increment that starts with $e \ge e_{max}$ (see [Dilatancy cut-off](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#dilatancy-cut-off)). The initial void ratio has to be given as the state variable `void_ratio` with [`*Initial conditions, type=state variables`](../../initial-conditions/state-variables.md); numgeo stops with an error if it is missing or if $e_{max} < 0$. Elements added later with `*Model change, add` keep this initial value. The cut-off acts only where the soil changes its volume: under constant volume (undrained) the void ratio does not change, and the shear strength is not limited.

Example (void ratio 0.715 at the start, cut-off at 0.989):

```numgeo
*Optional mechanical parameter
e_max, 0.989
...
*Initial conditions, type=state variables, default
Sand, void_ratio, 0.715
```

The optional parameter `min_pressure` is accepted but has no effect on this model: the lower bound of $\sigma_3$ in the stiffness, $\sigma_{min} = 0.1$ (in the stress unit of the input), is fixed.

## Model-specific output parameters

* `Void_Ratio`: void ratio (updated with the volumetric strain only with the dilatancy cut-off, `e_max` > 0, which requires an initial value).
* `Strain-Dev-Pl`: hardening variable $\gamma^p$ of the cone: $\tfrac32$ times the plastic deviatoric strain $\varepsilon_q^p$ of the cone while the cone hardens ($|\varepsilon_1^p - \varepsilon_3^p|$ in triaxial compression); on the failure surface it does not accumulate the plastic strain (see [Hardening Laws](../../../theory/constitutive-models/mechanical-models/hardening-soil-MN.md#hardening-laws)).
* `Stress-Precon`: preconsolidation stress $p_p$ (cap hardening variable).
* `Stress-P`: mean effective stress $p$ (compression positive).
* `Stress-Q`: deviatoric stress $q$.

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
