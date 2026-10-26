# Hypoplasticity + Intergranular Strain Anisotropy + Semi-Fluidized State and Fabric Change Effects (HYPO-ISA-SF): 

Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain anisotropy extension (Fuentes et al., 2020)[@fuentes2020] and fabric change effects as well as semifluidized state as proposed by Tafili et al. (2025) [@tafili2024hypoplastic] (referred to in the following as Hypo-ISA-SF). 
The numgeo keyword reads:

```numgeo 
*Mechanical = Hypo-ISA-SF   
** phi_c (degree or rad), h_s (F/A), n (-), e_c0 (-), e_d0 (-), e_i0 (-), alpha (-), beta (-)
** m_R (-), R (-), beta_h0 (-), chi_0 (-), chi_max (-), eps_acc (-), c_z (-), beta_hmax (-)
** c_r (-), c_l (-), lambda_1 (-), lambda_2 (-) (-), c_mn (-), p_th (F/A), n_l (-), f_l (-)
``` 

The material parameters of the Hypo-ISA-SF model are given in the following. Further information on the model constitutive equations are provided in [@tafili2024hypoplastic].

* $\varphi_c$ (degree or rad) is the critical friction angle and has to be provided in radian.
* $h_s$ (F/A) and $n$ (-) describe the decrease of the limiting void ratios $e_i$, $e_c$ and $e_d$ with increasing pressure during isotropic compression. The parameter $n$ has no unit.
* The void ratios $e_{d0}$ (-), $e_{c0}$ (-) and $e_{i0}$ (-) correspond to the densest, the critical and the loosest state at pressure $p$ = 0 F/A. These parameters have no unit.
* The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
* $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
* $m_R$ governs the increase of the stiffness due to changes in the direction of the strain path. The parameter has no unit.
* $R$ is the radius of intergranular strain. This parameter has no unit.
* $\beta_{h0}$ and $\beta_{hmax}$ are the minimum and maximum hardening parameters of the intergranular strain and describe the evolution of the intergranular strain tensor along a strain path. These parameters have no unit.
* $\chi^0$ and $\chi^{max}$ are the minimum and maximum intergranular strain exponent. These parameters have no unit.
* $\epsilon^{acc}$ is the accumulation rate factor. This parameter has no unit.
* $c_z$ is the cyclic mobility factor. This parameter has no unit.

Parameters of the SF extension
* $c_r$ and $c_l$ control the evolution rate of the strain liquefaction factor $l$. $c_r$ can be set to a default value of 1000.
* $\lambda_1$ and $\lambda_2$ are semi-fluidised state constants. $\lambda_2$ can be set to a default value of 3.0.
* $c_{mn}$ is a parameter balancing the stress-strain hystheresis under undrained triaxial loading
* $p_{th}$ is the threshold effective stress. $p_{th}$ can be set to a default value of 10.
* $n_l$ is a semi-fluidised state constant, default value is 8.0.
* $f_l$ is a semi-fluidised state constant, default value is 0.01.

    ## Optional parameters

    ```numgeo
    *Optional mechanical parameter
    <property 1>, <value 1>...
    <property 2>, ...
    ```

    Optional mechanical parameters can be used to enable locally undrained conditions, change some default settings or activate some stabilisation methods. Their use is optional.

    * `phantom_E, E_ph` and `phantom_nu, nu_ph` are the parameters of the phantom elasticity. The Hypo-ISA implementation available from [soilmodels.com](https://soilmodels.com) uses a phantom linear elasticity overlying the constitutive-model response with $E_{ph}=20$ kPa and $\nu_{ph}=0.45$ (as of 22 May 2025). We have also included this in our implementation, but it is deactivated by default. If activated, the parameters must be specified in the input for transparency. We recommend leaving it deactivated ($E_{ph}=0$). Unlike the original implementation by W. Fuentes, phantom elasticity in the numgeo implementation is active only when the mean effective stress is equal to or below $p_{min,ph}$. For more information, see the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md).

    * `bulk_water, Kw`: Bulk modulus of pore water for locally undrained simulations (and only for those). Per default $K^w=0$ F/A. To activate locally undrained conditions, $K^w>0$ must be set by the user.

    * `projection_dev, value`: specifies the friction angle for the projection of stress states onto the Matsuoka-Nakai failure surface defined by a user defined friction angle $\varphi^{cut}$ in degree. Per default `value=-1` (no projection). For `value=0` the cut-off friction angle is automatically determined by numgeo and for `value=>0°`, $\varphi^{cut}=$ `value` is used. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

    * `min_pressure, value`: Minimum mean effective stress in kPa (compression = positive). The default is `value=0.01` kPa.

    * `integrator`: a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. integrator=1 (default) corresponds to a Forward Euler (FE) integration scheme, with integrator=2 a Euler-Richards integration scheme with adaptive time incrementation is used.

---

## State variables
In addition to the (effective) stress, the hypoplastic constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio: $e$, `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.
* Intergranular strain: $\mathbf{h}$, `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`. Only in combination with the intergranular strain extension. Prescribing $\mathbf{h}_0$ is not mandatory, if omitted, $\mathbf{h}=\mathbf{0}$ is assumed. $h_{ii} = -R / \sqrt{3}$ for $i=\{x,y,z\}$ corresponds to an isotropically consolidated state.
* Intergranular back strain: $\mathbf{c}$, `int_back_strain11`, `int_back_strain22`, `int_back_strain33`, `int_back_strain12`, `int_back_strain23`, `int_back_strain13`. Only in combination with the intergranular strain extension. $\mathbf{c}_0=\mathbf{h}_0/2$, however, prescribing $\mathbf{c}_0$ is not mandatory, if omitted, $\mathbf{c}=\mathbf{0}$ is assumed.
* Relative density, `rel-density`. $D_r = \dfrac{e_c-e}{e_c-e_d}$. Note that $e_c$ and $e_d$ are pressure dependent (see the [Theory manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md)). The relative density can also be used to initialise the void ratio $e_0$.

The state variables can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.

```numgeo 
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
element_set_name, int_strain11, <value>
element_set_name, int_strain22, <value>
element_set_name, int_strain33, <value>
element_set_name, int_back_strain11, <value>
element_set_name, int_back_strain22, <value>
element_set_name, int_back_strain33, <value>
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
* *statev(9)* = $c_{11}$ 
* *statev(10)* = $c_{22}$ 
* *statev(11)* = $c_{33}$ 
* *statev(12)* = $c_{12}$ 
* *statev(13)* = $c_{23}$ 
* *statev(14)* = $c_{13}$
* *statev(43)* = $D_{r}$

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
* Intergranular back strain: `int_back_strain11`, `int_back_strain22`, `int_back_strain33`, `int_back_strain12`, `int_back_strain23`, `int_back_strain13`.
* Stress projection: `iproj`. Flag that indicates if the stress correction is active (see Theory Manual). `iproj` takes the value of 0 if the stress projection is inactive.
* Hypoplastic factors: `fz`, `fb`, `fd`, `fe`,
* Mobilised friction angle: `phi_mob`
* Semi-fluidised factors: `l_sf`, `se`, `pr`
* Relative density: `rel-density`

---
