# Ta-Ger

`Ta-Ger` is an elastoplastic sand model based on the Ta-Ger formulation of Tasiopoulou and Gerolymos [@tasiopoulou2016,@tasiopoulou2016a]. It combines an explicit elastoplastic stiffness matrix with a Bouc-Wen type mapping variable, critical-state-compatible evolution of the bounding and phase transformation stress ratios, Rowe-type dilatancy and a stress-induced peak-strength correction.

## Input syntax

```numgeo
*Mechanical = Ta-Ger
G0, m, nu, Q, R, emin, emax, phics
delta, kappa, Gmodel
```

### Material parameters

The material parameters for `Ta-Ger` are:

|  # | Symbol | Unit | Description |
| :-: | :----: | :--: | ----------- |
| 1 | $G_0$ | model-dependent | Shear stiffness coefficient. Its interpretation depends on `Gmodel`. |
| 2 | $m$ | - | Exponent controlling pressure dependency of the shear modulus. |
| 3 | $\nu$ | - | Poisson's ratio used to compute the bulk modulus from the shear modulus. |
| 4 | $Q$ | - | First parameter of Bolton's relative dilatancy index $I_r=D_r[Q-\ln(p)]-R$. |
| 5 | $R$ | - | Second parameter of Bolton's relative dilatancy index. |
| 6 | $e_{min}$ | - | Minimum void ratio used to calculate relative density. |
| 7 | $e_{max}$ | - | Maximum void ratio used to calculate relative density. |
| 8 | $\varphi_{cs}$ | deg | Critical-state friction angle. |
| 9 | $\delta$ | - | Intrinsic calibration coefficient for $c=6+\delta I_{r0}$. |
| 10 | $\kappa$ | - | Intrinsic calibration coefficient for $\varphi_{s0}=\kappa\varphi_{cs}+5I_{r0}$. |
| 11 | `Gmodel` | - | Shear modulus option. `1`: $G=G_0(0.13D_{r0}+3.6)p^m$; otherwise: $G=G_0p_a(2.97-e)^2/(1+e)(p/p_a)^m$. |

!!! note "Pressure units"

    The relative dilatancy index uses $\ln(p)$ directly. The pressure unit convention must therefore be consistent with the calibration of $Q$ and $R$. The commonly used calibration is based on stresses in kPa.

!!! note "Reference state"

    The initial void ratio must be provided as the first state variable before the first increment. At the first increment of the first step numgeo stores the reference state $p_0$, $e_0$, $D_{r0}$ and $I_{r0}$. These values remain fixed afterwards.

### Typical values

For clean sands, values close to $Q=9$--$10$ and $R=0.5$--$1.0$ are commonly used. The coefficients $\kappa$ and $\delta$ are sand-dependent calibration parameters. Typical values reported in the Ta-Ger calibration study include approximately:

| Sand | $\kappa$ | $\delta$ |
| ---- | :------: | :------: |
| Toyoura sand | 0.9 | 1 |
| Fontainebleau sand | 0.8 | 4 |
| Sacramento River sand | 0.7 | 3 |

These values should be regarded as calibration guidance rather than universal defaults.

### Example

```numgeo
*Mechanical = Ta-Ger
** G0, m, nu, Q, R, emin, emax, phics, delta, kappa, Gmodel
130, 0.8, 0.15, 9.15, 0.77, 0.597, 0.977, 32, 1, 0.9, 2
```

For the density-based shear modulus option, a possible input is:

```numgeo
*Mechanical = Ta-Ger
** G0, m, nu, Q, R, emin, emax, phics, delta, kappa, Gmodel
1000, 0.5, 0.15, 9.15, 0.77, 0.597, 0.977, 32, 1, 0.9, 1
```

---

## State variables

At least 14 state variables are required. The state-variable layout is:

| # | Symbol | Description |
| :-: | :----: | ----------- |
| 1 | $e$ | Current void ratio. Must contain the initial void ratio before the first increment. |
| 2 | $p_0$ | Initial mean effective stress, stored at the first increment. |
| 3 | $dW_{old}$ | First-order work indicator from the previous substep. |
| 4 - 9 | $\mathbf{r}_p$ | Stress-ratio tensor at the last loading reversal. |
| 10 | $\sum d\varepsilon_q$ | Accumulated deviatoric strain measure. |
| 11 | $K_w$ | Auxiliary water bulk modulus for locally undrained calculations. |
| 12 | $e_0$ | Initial void ratio, stored at the first increment. |
| 13 | $D_{r0}$ | Initial relative density. |
| 14 | $I_{r0}$ | Initial relative dilatancy index. |

The following state quantities can be accessed by their respective names instead of their index in the array `statev`

* `Void_Ratio`: current void ratio $e$.
* `Bulk_Water`: Bulk modulus of water $K_w$.

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/ta-ger.md)

</div>

---

---

## References