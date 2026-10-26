# Sanisand-F 

The extension of the well known Sanisand model[@dafalias2004] to incorporate effects of **fabric** by Petalas et al (2019)[@petalas2020]. The implementation has been developed in cooperation with Sheng Zeng and Mahdi Taiebat UBC Vancouver. The numgeo keyword reads:

```numgeo 
*Mechanical = Sanisand-F
p_atm (F/A), e_0 (-), lambda_c (-), xi (-), M_c (-), M_e  (-), m (-),  G_0 (-) 
nu (-), h_0 (-), c_h (-), n_b (-), A_0 (-), n^d (-), z_max (-), c_z (-)
eA (-), r (-)
```
The material parameters of Sanisand-F are given in the following.  

* $p_{atm}$ (F/A) is the atmospheric pressure usually given by 100 kPa.
* $e_0$ is the critical void ratio at zero mean effective stress and can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state. The parameters are not identical, however.
*  $\lambda_c$  and $\xi$ define the relation between critical void ratio and mean effective stress. Again, they can for instance be obtained from (several) undrained monotonic triaxial tests reaching the critical state.
* $M_c$ and  $M_e$ are the critical stress ratios for compression and extension, respectively. They can be calculated using the critical friction angle.
*  $m$ defines the elastic range of the model. Conventionally, it is chosen to 0.05.
* $G_0$ and $\nu$ are the elastic parameters of the model. 
* $h_0$ and $c_h$ are obtained from the fitting of monotonic triaxial tests. They have no physical meaning.
* $n_b$ influences the peak in the $q$-$\varepsilon_1$ plot. Again, it has no physical meaning.
* $A_0$  and $n^d$ influence the dilatancy. They also have no physical meaning.
* $z_{\max}$  and $c_z$ are the parameters influencing the cyclic mobility effect. They are obtained by fitting of cyclic triaxial test data. 

## Optional Parameters

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```
Definition of optional parameters is not mandatory. The specification can also be made individually:

* `integration`
Flag controlling the integration method, available are: 0 = explicit with constant subincrement size, 1 = Modified-Euler[@sloan2001] (default), 2 = Forward Euler
* `min_pressure`
Minimum mean effective stress in kPa (compression = positive). The default is 0.5 kPa.
* `tol_stress`
Tolerance for stress error of the explicit integration scheme, default is $1\cdot 10^{-4}$.
* `minimum_dh`
Minimum subincrement size for the integration scheme, default is $10^{-6}$.
* `allow_cutback`
Controlling if the constitutive model is allowed to request a ''global cutback'' from numgeo: 0 = not allowed (default), 1 = allowed.
* `drift_correction`
Method for drift correction: 0 = map yield surface by adjusting alpha (default), 1 = projection along deviatoric plane, else = drift correction based on Sloan et al. (2001)[^3].
* `drift_maxiter`
Maximum number of iterations for drift correction (only for the OpenSees drift correction, ignored otherwise). The default is 50.
* `tol_yield`
Tolerance for yield surface. Default is $10^{-7}$.
* `tangent_stiffness`
When the contribution of the constitutive model $J=\dfrac{\partial \sigma}{\partial \varepsilon}$ to the element stiffness is computed. 1 = tangent stiffness (evaluated at the end of the increment for the updated stress state), else = "incremental" stiffness (evaluated at the end of each subincrement, a weighted average is returned to the element, default).
* `jacobi`
How $J=\dfrac{\partial \sigma}{\partial \varepsilon}$ is evaluated:  1 = elastic Jacobian (default), 2 = elasto-plastic Jacobian.
* `maximum_strain`
Maximum strain $\Delta \varepsilon^{sub}$ for subincrement size in explicit integration, default is $\Delta \varepsilon^{sub} = 5 \cdot 10^{-7}$. This option is only relevant for the Forward Euler (FE) integration.
* `maximum_voidratio, maximum_voidratio`
Maximum and minimum allowed void ratios $e^{max}$ and $e^{min}$, respectively (off per default). If active (for any value larger than zero), $e=min(e,e^{max})$ and/or $e=max(e,e^{min})$ is/are enforced.
* `bulk_water, 0.0` - Bulk modulus of pore water $K^w$ for locally undrained simulations $tr(\dot{\boldsymbol{\varepsilon}})=0$. For any value of $K^w > 0$ the rate of pore water pressure is calculated as follows $\dot{p}^w = - K^w tr(\dot{\boldsymbol{\varepsilon}}) (1+e)/e$. The constitutive behaviour is governed by the effective stress $\boldsymbol{\sigma} = \boldsymbol{\sigma}^{tot}-p^w \boldsymbol{\delta}$, where $\boldsymbol{\sigma}^{tot}$ is the total stress and $\boldsymbol{\delta}$ is the Kronecker delta.

## State variables
The following state variables are contained in the model and can (must) be initialized:

* Void ratio: $e$, ``void_ratio``. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.
* Unitnorm direction of fabric tensor $\boldsymbol{n}_F$: `Fnorm_11`, `Fnorm_22`, `Fnorm_33`
* Initial value of the norm of the fabric tensor $F_{in}$: `F_in`

The initial back stress tensor is always defined such that the initial stress state is in the centre of the elastic range of the model.

## Additional output variables
The following additional output variables are available:

* Void ratio: `void_ratio`
* Back stress tensor: `alpha_11`, `alpha_22`, `alpha_33`.
* Value of the yield surface:  `Fyield`. Should always be less than zero. For values close to zero, the model will most likely produce plastic strain. 
* State variable $\psi = e - e_c$: `psi`
* Mean effective stress: `stress-p`
* Deviatoric stress: `stress-q`
* Pore water pressure: `stress-pw` (only for locally undrained simulations by setting `bulk_water` > 0)
* Fabric tensor: `fabric_11`, `fabric_22`, `fabric_33`.
* Unitnorm direction of fabric tensor $\boldsymbol{n}_F$: `Fnorm_11`, `Fnorm_22`, `Fnorm_33`.
* The initial value of the norm of the fabric tensor $F_{in}$: `F_in`.

---

## References