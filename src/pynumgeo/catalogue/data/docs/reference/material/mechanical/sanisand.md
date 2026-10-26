# Sanisand 

SANISAND is a critical state compatible bounding surface plasticity model according to Dafalias & Manzari (2004)[@dafalias2004], sometimes also referred to as DM04. SANISAND is available in two different implementations:

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Sanisand__

    ---

    [:octicons-arrow-right-24: implementation with simple Forward Euler sub-stepping and elastic tangent Jacobian only.](#sanisand)

-   :material-lightbulb-on-outline:{ .lg .middle } __Sanisand-2 (Recommended)__

    ---

    [:octicons-arrow-right-24: implementation with Forward Euler or Modified-Euler sub-stepping, elastic or elasto-plastic Jacobian and more advanced features.](#sanisand-2)
</div>

---

## Sanisand

Sanisand implementation with simple Forward Euler sub-stepping and elastic tangent Jacobian only. The numgeo keyword reads:

```numgeo 
*Mechanical = Sanisand  
p_atm (F/A), e_0 (-), lambda_c (-), xi (-), M_c (-), M_e  (-), m (-),  G_0 (-) 
nu (-), h_0 (-), c_h (-), n_b (-), A_0 (-), n^d (-), z_max (-), c_z (-)
```

The material parameters of Sanisand are given in the following.  

* $p_{atm}$ (F/A) is the atmospheric pressure usually given by 100 kPa.
* $e_0$ is the critical void ratio at zero mean effective stress and can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state. It will be in the range of  $e_{c0}$ used by the [hypoplastic model](hypoplasticity_igs.md). The parameters are not identical, however.
*  $\lambda_c$  and $\xi$ define the relation between critical void ratio and mean effective stress. Again, they can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state.
* $M_c$ and  $M_e$ are the critical stress ratios for compression and extension, respectively. They can be calculated using the critical friction angle.
*  $m$ defines the elastic range of the model. Conventionally, it is chosen to 0.05.
* $G_0$ and $\nu$ are the elastic parameters of the model. 
* $h_0$ and $c_h$ are obtained from the fitting of monotonic triaxial tests. They have no physical meaning.
* $n_b$ influences the peak in the $q$-$\varepsilon_1$ plot. Again, it has no physical meaning.
* $A_0$  and $n^d$ influence the dilatancy. They also have no physical meaning.
*  $z_{\max}$  and $c_z$ are the parameters influencing the cyclic mobility effect. They are obtained by fitting of cyclic triaxial test data. 

### State variables
From the state variables of Sanisand, only the void ratio can be initialised analogously to the procedures described for the [hypoplastic model](hypoplasticity_igs.md). The initial back stress tensor is always defined such that the initial stress state is in the centre of the elastic range of the model.

### Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Back stress tensor: `alpha_11`, `alpha_22`, `alpha_33`, `alpha_12`, `alpha_23`, `alpha_13`.
* Stress projection: `proj`. Flag that indicates if the stress correction is active (see Theory Manual). `proj` takes the value of 0 if the stress projection is inactive.
* Plastic strain: `eps_plas` 
* Value of the yield surface:  `F_yield`. Should always be less than zero. For values close to zero, the model will most likely produce plastic strain. 
* Convergence of return mapping algorithm: `no_conv`. Greater than zero if  return mapping algorithm failed.

---

## Sanisand-2

SANISAND implementation with Forward Euler or Modified-Euler[@sloan2001] sub-stepping, elastic or elasto-plastic Jacobian and more advanced features. Developed in cooperation with Sheng Zeng and Mahdi Taiebat UBC Vancouver. The numgeo keyword reads:

```numgeo 
*Mechanical = Sanisand-2 
p_atm (F/A), e_0 (-), lambda_c (-), xi (-), M_c (-), M_e  (-), m (-),  G_0 (-) 
nu (-), h_0 (-), c_h (-), n_b (-), A_0 (-), n^d (-), z_max (-), c_z (-)
```
The material parameters of Sanisand are given in the following.  

* $p_{atm}$ (F/A) is the atmospheric pressure usually given by 100 kPa.
* $e_0$ is the critical void ratio at zero mean effective stress and can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state. It will be in the range of  $e_{c0}$ used by the [hypoplastic model](hypoplasticity_igs.md). The parameters are not identical, however.
*  $\lambda_c$  and $\xi$ define the relation between critical void ratio and mean effective stress. Again, they can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state.
* $M_c$ and  $M_e$ are the critical stress ratios for compression and extension, respectively. They can be calculated using the critical friction angle.
*  $m$ defines the elastic range of the model. Conventionally, it is chosen to 0.05.
* $G_0$ and $\nu$ are the elastic parameters of the model. 
* $h_0$ and $c_h$ are obtained from the fitting of monotonic triaxial tests. They have no physical meaning.
* $n_b$ influences the peak in the $q$-$\varepsilon_1$ plot. Again, it has no physical meaning.
* $A_0$  and $n^d$ influence the dilatancy. They also have no physical meaning.
* $z_{\max}$  and $c_z$ are the parameters influencing the cyclic mobility effect. They are obtained by fitting of cyclic triaxial test data. 

### Optional Parameters

```numgeo
*Optional mechanical parameter
<property 1>, <value 1>
<property 2>, <value 2>
```

Each option can be specified individually. Omitted options use the defaults below. If a supplied value is outside its admissible range, is not finite, or is not an integer where required, SANISAND-2 uses the documented default locally during the material update. The stored material definition is unchanged and no material-point warning is printed. This also applies to the SANISAND-2 options of `HCA-SANISAND-2`.

| Property | Default | Admissible values and meaning |
| --- | --- | --- |
| `tol_yield` | $10^{-7}$ | Positive absolute yield-function tolerance, in the same pressure units as the stresses. |
| `min_pressure` | $0.5$ | Positive minimum mean effective stress (compression positive), in the chosen pressure units; $0.5$ kPa when stresses are in kPa. |
| `jacobi` | `1` | `1`: elastic Jacobian; `2`: elasto-plastic continuum tangent; `3`: numerical (algorithmic) Jacobian, see below. For `1` and `2`, Modified Euler uses the accepted final state; Forward Euler averages the substep tangents. The original elastic override for $p\leq0.05p_{atm}$ is retained for `1` and `2` and also applies at an active minimum-pressure constraint. Neither `1` nor `2` is a consistent algorithmic tangent. |
| `force_elastic` | `0` | `0`: elastoplastic response; `1`: force an elastic response. |
| `integration` | `1` | `1`: adaptive Modified Euler[@sloan2001]; `2`: Forward Euler with strain-limited subincrements. `0` is retained as a legacy alias for Modified Euler. |
| `tol_stress` | $10^{-4}$ | Positive relative local error tolerance for Modified Euler. The estimate includes the pressure-projected stress endpoints, back stress, fabric, and yield corrections. It is not a bound on accumulated error over an entire loading path. |
| `drift_correction` | `2` | Non-negative integer. `0`: adjust back stress; `1`: project stress in the deviatoric plane; `2` and larger: the original coupled Newton correction with gradient and bracket fallbacks. An unsuccessful correction requests a cutback. Corrections contribute to the Modified Euler error estimate. |
| `update_alpha` | `3` | `1`: detect reversal using the yield-surface normal; `2`: use the elastic stress increment; `3`: use the stress state relative to the yield-surface centre. |
| `minimum_dh` | $10^{-6}$ | $0 < dh_{min} \leq 1$. Minimum fraction of the imposed strain increment used for a substep. A substep at this limit is still rejected if its local error exceeds the tolerance. |
| `drift_maxiter` | `50` | Positive integer. Maximum number of coupled drift iterations; used when `drift_correction` is at least `2`. |
| `bulk_water` | `0` | Non-negative bulk modulus of pore water in the chosen pressure units. `0` disables the local pore-pressure update; positive values enable the locally undrained formulation below. |
| `maximum_strain` | $5\cdot10^{-7}$ | Positive maximum strain-increment tensor norm per Forward Euler substep. Forward Euler has no local error control; verify accuracy by refining this cap and the global increment. |
| `maximum_voidratio` | `0` | `0`: disabled; otherwise $0 < e^{max} < 2.97$, enforcing $e=\min(e,e^{max})$. |
| `minimum_voidratio` | `0` | `0`: disabled; otherwise $0 < e^{min} < 2.97$, enforcing $e=\max(e,e^{min})$. |
| `mb_formulation` | `0` | Integer. `0`: original formulation of $M_b$; any other integer: prevent the bounding stress ratio from falling below the critical-state image. |

Both integration choices retain the Sloan elastic/plastic split and Pegasus yield intersection, including unloading followed by reloading. The elastic predictor and the intersection path use the initial elastic stiffness. This retained approximation is first order in the global increment; `tol_stress` controls the adaptive plastic substeps, not the purely elastic branch. Check global increment convergence as well as local tolerance.

Modified Euler evaluates the selected reversal rule at each rate stage. The legacy `update_alpha=2` rule can miss a rotation of the yield normal on nonproportional paths: the hardening distance $(\boldsymbol\alpha-\boldsymbol\alpha_{in}):\mathbf n$ can become negative while its elastic-increment criterion stays positive. Such an undefined plastic rate requests a cutback and may not be resolved by reducing the local substep. The selected rule is not silently replaced. The default `update_alpha=3` and normal-based rule `1` were checked against an event-resolved reference on a captured reversal path.

Modified Euler keeps the second rate on the plastic branch when the first rate is plastic; small predictor drift into the yield surface must not switch that rate to elasticity. An elastic first rate does not activate this continuation. The error estimate compares the pressure-projected Euler and Modified Euler endpoints and includes the yield-correction increment. An actual interior state created by pressure projection remains elastic until loading reaches yield again.

At the active minimum-pressure constraint, the plastic multiplier is evaluated with $dp=0$ in the consistency equation. The stress rate and the coupled yield correction then preserve that pressure, while back stress, fabric and dilatancy retain their constitutive equations. Compression releases the constraint when the unconstrained rate points toward increasing pressure. Both Euler schemes share this rate calculation. This is the numerical treatment of the configured pressure floor; it is not an additional SANISAND material parameter. A Modified Euler substep that starts at the minimum pressure is accepted on the stress error alone, since the back-stress error of large dilative trial increments at the pressure floor would otherwise request a cutback.

With `jacobi=3`, the Jacobian is the derivative of the complete material update with respect to the strain increment, obtained by forward differences: after a plastic update, the update is repeated from the state at the beginning of the increment with one strain component at a time perturbed by $h=10^{-6}\max(\lVert\Delta\boldsymbol\varepsilon\rVert,10^{-6})$. The Jacobian therefore includes the intersection with the yield surface, the drift correction, the minimum pressure, the rotation of back stress and fabric with the spin and, for `bulk_water` $>0$, the pore-water pressure. The perturbed Modified Euler updates replay the accepted substeps of the unperturbed update, so that a change of the adaptive substep sequence does not enter the differences. For this, the unperturbed update limits the strain of a substep to 0.2 times the radius of the yield cone in strain space, $0.2\sqrt{2/3}\,m\,p/(2G)$, unless $p\leq1.01\,p_{min}$; the stress is then integrated somewhat more finely than with `jacobi=1` or `2`. If this update fails, the increment is integrated as with `jacobi=1` and the elastic Jacobian is returned. Elastic increments return the elastic Jacobian; the elastic override at low pressure does not apply. The Jacobian is non-symmetric and can be indefinite (contractive or softening states, minimum pressure). A plastic update costs 4 or 6 additional updates, about 10 times the cost with `jacobi=1`. In integration-point tests with mixed stress and strain control, the number of Newton iterations dropped by a factor of 7 to 16 compared with `jacobi=2`; at $p<0.05p_{atm}$, `jacobi=3` converged within 7 iterations in states in which `jacobi=1` and `2` did not converge within 50.

If both void-ratio limits are active and `minimum_voidratio` exceeds `maximum_voidratio`, SANISAND-2 uses the default `0` (disabled) for **both** local controls. A single invalid limit uses its default individually. Configured limits apply to the incoming mapped state as well as to elastic and plastic increments.

The positive scalar controls (`tol_yield`, `min_pressure`, `tol_stress`, `maximum_strain`) and `bulk_water` have a numerical upper limit of $10^{100}$. Integer options must be representable by the implementation's integer kind (absolute value smaller than its maximum representable integer). An out-of-range value uses its documented default. `ALLOW_CUTBACK` and `TANGENT_STIFFNESS` are not supported SANISAND-2 option names; unknown names are reported as input errors.

For `bulk_water` $K^w>0$, the local pore-pressure rate is $\dot p^w=-K^w\operatorname{tr}(\dot{\boldsymbol\varepsilon})(1+e)/e$. The constitutive law uses effective stress, and the pore-pressure contribution is included in the returned total stress and tangent. Use this option for a locally undrained material calculation. The original initialization convention is retained: the option is disabled during the first increment of the first step. The void-ratio update integrates $de=-(1+e)d\varepsilon_v$ in compression-positive convention, and the pore-pressure increment integrates the corresponding rate consistently, including configured void-ratio limits.

### Input errors and integration failures

Required material properties do not have fallback values. The material update checks their numerical domain before evaluating the model. Invalid values request a cutback and preserve the caller stress, state and tangent. Reducing the increment cannot repair an invalid material definition; repeated rejection reaches the existing global minimum-increment termination. All 16 required values must be finite. The implemented domain requires $p_{atm},G_0,h_0,m>0$, $M_c,M_e>m$, $0<e_{c0}<2.97$, $0<\xi\leq10$, $-1<\nu<0.5$, and non-negative $\lambda_c,c_h,n_b,A_0,n_d,z_{max},c_z$. Numerical range checks also require $p_{atm}\leq10^{100}$, the absolute values of the other properties no larger than $10^{10}$, and $n_be_{c0},n_de_{c0}\leq100$. These range checks guard the numerical evaluation; they are not recommended calibration ranges. The model supports four or six stress/strain components and requires at least 25 state variables; plane stress is not supported.

Finite incoming back-stress and fabric tensors are checked and repaired before integration, including after remapping. Repairs preserve the deviatoric constraints and impose the conservative back-stress envelope and $\lVert\mathbf z\rVert\leq z_{max}$. A valid softening state is not clipped to the instantaneous bounding surface. The constitutive state must have $0<e<2.97$, positive effective pressure, and, for plastic response, $c_he<1$.

If a material update fails, it requests a global cutback and leaves the caller's stress, state and tangent unchanged. The element discards the attempt before using the tangent or assembling its contribution. The global solver retries from the last accepted state; a material failure cannot be accepted by `NO CUTBACK`, and a failure at the minimum increment stops the calculation. No warning is printed by individual material points or rejected substeps during normal execution.

For a focused source-level investigation, set the module parameter `debug_sanisand2 = .true.` in `material_sanisand2_.f90` and rebuild. It defaults to `.false.`. Each failed complete update then prints one serialized line with element, integration point, step and increment. The original detailed drift diagnostics also use this switch. Keep it disabled for production parallel runs.

Direct Fortran callers use `sanisand2` without a separate preparation call and must inspect `request_cutback` before using an attempted update. Required-property checks and optional-control fallbacks are private to the model. The input reader and material catalogue do not call SANISAND-specific setup routines; the catalogue retains its inline default assignments.

### State variables
The void ratio must be initialized. The original SANISAND-2 initialization is retained: during the first increment of the first step, a back-stress tensor with norm below `0.1` is centered on the initial effective stress ratio. Existing larger histories pass through the mapped-state checks described above.

* Void ratio: $e$, ``void_ratio``. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.

### Additional output variables
The following additional output variables are available:

* Void ratio: `void_ratio`
* Back stress tensor: `alpha_11`, `alpha_22`, `alpha_33`.
* Value of the yield surface:  `Fyield`. Should always be less than zero. For values close to zero, the model will most likely produce plastic strain. 
* State variable $\psi = e - e_c$: `psi`
* Mean effective stress: `stress-p`
* Deviatoric stress: `stress-q`
* Pore water pressure: `stress-pw` (only for locally undrained simulations by setting `bulk_water` > 0)
---

## References
