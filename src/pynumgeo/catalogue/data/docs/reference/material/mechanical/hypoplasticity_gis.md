# Hypoplasticity + Generalized Intergranular Strain (HYPO+GIS): 

Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with generalized intergranular strain extension after Mugele et al. (2024)[@mugele2024] including the extracted asymptotic state boundary surface of the base model:

```numgeo 
*Mechanical = Hypo-GIS   
phi (degree or rad), h_s (F/A), n (-), e_d0 (-), e_c0 (-), e_i0 (-), alpha (-), beta (-) 
m_R (-), m_T (-), R (-), beta_R (-), chi^R (-), chi^0 (-), chi^max (-), gamma_chi (-),
gamma_omega (-), c_omega (-)
``` 

The material parameters of the hypoplastic model with GIS extension are given in the following. 

* $\varphi_c$ (degree or rad) is the critical friction angle and has to be provided in degree or in radian. Values larger than 1 are considered to be provided in degree.
* $h_s$ (F/A) and $n$ (-) describe the decrease of the limiting void ratios $e_i$, $e_c$ and $e_d$ with increasing pressure during isotropic compression. The parameter $n$ has no unit.
* The void ratios $e_{d0}$ (-), $e_{c0}$ (-) and $e_{i0}$ (-) correspond to the densest, the critical and the loosest state at pressure $p$ = 0 F/A. These parameters have no unit.
* The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
* $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
* $m_R$ and $m_T$ govern the increase of the stiffness due to changes of the direction of the strain path by $180^\circ$ ($m_R$) or $90^\circ$ ($m_T$), respectively. These parameters have no unit. An often applied assumption is: $m_T = m_R/2$.
* $R$ is the radius of intergranular strain. This parameter has no unit.
* $\beta_R$ and $\chi_R$ describe the evolution of the intergranular strain tensor along a strain path, i.e. the reduction of the shear modulus with increasing shear strain. These parameters have no unit.
* $\gamma_\chi$ scales the strain accumulation upon cyclic loading or loading reversal
* $\chi_0$, $\chi_{max}$ and $\gamma_\Omega$ control the evolution of the historiotropic (cyclic pre-loading) variable $\Omega$ and can be used to simulate nonlinear accumulation behavior.

!!! Info "Note that"

    * For $m_T=m_R=1$ the Hypo-GIS model reduces to the base hypoplastic model according to von Wollfersdorff (1996)[@wolffersdorff1996]. This is not the case for the Hypo-IGS and Hypo-ISA model
    * By setting $\chi_0=\chi_{max}=1$ the influence of the cyclic preloading variable $\Omega$ is deactivated, which reduces the number of model constants to be calibrated.

## Optional parameters

```numgeo
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```

Optional mechanical parameters can be used to enable locally undrained conditions, change some default settings or activate some stabilisation methods. Their use is optional.

* `phantom_E, E_ph` and `phantom_nu, nu_ph` are the parameters of the phantom elasticity. In analogy to the Hypo-ISA implementation available from [soilmodels.com](https://soilmodels.com), a phantom linear elasticity overlying the constitutive model response of the constitutive model with $E_{ph}=20$ kPa and $\nu_{ph}=0.45$ is also included in our implementation. However, it is deactivated by default and if activated, the parameters must be specified in the input for transparency. We recommend turning them off by default ($E_{ph}=0$).

* `bulk_water, Kw`: Bulk modulus of pore water for locally undrained simulations (and only for those). Per default $K^w=0$ F/A. To activate locally undrained conditions, $K^w>0$ must be set by the user.

* `min_pressure, value`: Minimum mean effective stress in kPa (compression = positive). The default is `value=0.01` kPa.

* `integrator`: a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. integrator=1 corresponds to a Forward Euler (FE) integration scheme, with integrator=2 (default) a Euler-Richards integration scheme with adaptive time incrementation is used.

---

## State variables
In addition to the (effective) stress, the hypoplastic constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio, $e$: `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.
* Intergranular strain, $\mathbf{h}$: `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`. Only in combination with the intergranular strain extension. Prescribing $\mathbf{h}_0$ is not mandatory, if omitted, $\mathbf{h}_0=\mathbf{0}$ is assumed. $h_{ii} = -R / \sqrt{3}$ for $i=\{x,y,z\}$ corresponds to an isotropically consolidated state.
* Cyclic preloading variable $\Omega$: `GIS-Omega`. If the initialisation is omitted by the user, $\Omega_0=0$ is assumed.
* Relative density, `rel-density`. $D_r = \dfrac{e_c-e}{e_c-e_d}$. Note that $e_c$ and $e_d$ are pressure dependent (see the [Theory manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md)). The relative density can also be used to initialise the void ratio $e_0$.

The state variables can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.

```numgeo 
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
element_set_name, int_strain11, <value>
element_set_name, int_strain22, <value>
element_set_name, int_strain33, <value>
...
```

* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section User defined state variables. The position of the state variables in the associated vector are as follows: 

* *statev(1)* = $e$ 
* *statev(3)* = $h_{11}$ 
* *statev(4)* = $h_{22}$ 
* *statev(5)* = $h_{33}$ 
* *statev(6)* = $h_{12}$ 
* *statev(7)* = $h_{23}$ 
* *statev(8)* = $h_{13}$
* *statev(43)* = $D_{r}$
* *statev(44)* = $\Omega$

The relative density can also be used to initialise the void ratio $e_0$. If $D_{r0}$ is provided by the user, e.g. by the following input command:

```
*Initial conditions, type = state variables
element_set_name, rel-density, <value>
```

and no initial void ratio is specified, numgeo will calculate the initial void ratio according to the following equation

$$
e_0(p') = \left(  e_{c0} - D_{r0}(e_{c0}-e_{d0}) \right) \exp\left(\dfrac{-3p'}{h_s}\right)^n
$$

where $p'$ is the mean effective stress (compression is positive), $e_{c0}$ and $e_{d0}$ are the void ratios at the critical and densest state for $p'=0$ (material parameters).

---

## Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Intergranular strain: `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`.
* Hypoplastic factors: `fz`, `fb`, `fd`, `fe`
* Mobilised friction angle: `phi_mob`
* Relative density: `rel-density`
* State mobilisation $S$: `GIS-S`
* Cyclic variable $\Omega$: `GIS-omega`

---