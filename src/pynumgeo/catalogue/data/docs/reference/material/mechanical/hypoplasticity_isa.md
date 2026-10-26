# Hypoplasticity + Intergranular Strain Anisotropy (HYPO+ISA): 

Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain anisotropy extension (Fuentes et al., 2020)[@fuentes2020]. The numgeo keyword reads:

```numgeo 
*Mechanical = Hypo-ISA   
phi [rad or degree], h_s (F/A), n (-), e_d0 (-), e_c0 (-), e_i0 (-), alpha (-), beta (-) 
m_R (-), R (-), beta_h0 (-), chi^0 (-), chi^max (-), epsilon^acc (-), c^z (-), beta_hmax (-)
``` 

The material parameters of the hypoplastic model with intergranular strain are given in the following.  

* $\varphi_c$ (degree or rad) is the critical friction angle and has to be provided in degree or in radian. Values larger than 1 are considered to be provided in degree.
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

## Optional parameters

```numgeo
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```

Optional mechanical parameters can be used to enable locally undrained conditions, change some default settings or activate some stabilisation methods. Their use is optional.

* `phantom_E, E_ph` and `phantom_nu, nu_ph` are the parameters of the phantom elasticity. The Hypo-ISA implementation available from [soilmodels.com](https://soilmodels.com) uses a phantom linear elasticity overlying the constitutive-model response with $E_{ph}=20$ kPa and $\nu_{ph}=0.45$ (as of 22 May 2025). We have also included this in our implementation, but it is deactivated by default. If activated, the parameters must be specified in the input for transparency. We recommend leaving it deactivated ($E_{ph}=0$). Unlike the original implementation by W. Fuentes, phantom elasticity in the numgeo implementation is active only when the mean effective stress is equal to or below $p_{min,ph}$. For more information, see the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md).

* `bulk_water, Kw`: Bulk modulus of pore water for locally undrained simulations (and only for those). By default, $K^w=0$ F/A. To activate locally undrained conditions, $K^w>0$ must be set by the user.

* `projection_dev, value`: activate projection of inadmissible stress states onto the Matsuoka-Nakai failure surface defined by a cut-off friction angle $\varphi^{cut}$. By default, `value=-1` (no projection). For `0 <= value <= 5`, the cut-off friction angle is determined automatically by numgeo; for `value>5`, $\varphi^{cut}=$ `value°` is used. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

* `projection_iso, value`: activate projection of inadmissible stress states onto a pseudo primary loading surface. By default, `value=-1` (no projection). For `value=1`, the projection is activated. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

* `min_pressure, value`: Minimum mean effective stress in kPa (compression = positive). The default is `value=0.01` kPa.

* `integrator`: a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. integrator=1 (default)corresponds to a Forward Euler (FE) integration scheme, with integrator=2 a Euler-Richards integration scheme with adaptive time incrementation is used.


??? note "Before 2026-04"

    ```numgeo 
    *Mechanical = Hypo-Isa   
    phi [rad], h_s [F/A], n [-], e_d0 [-], e_c0 [-], e_i0 [-], alpha [-], beta [-] 
    m_R [-], R [-], beta_h0 [-], chi^0 [-], chi^max [-], epsilon^acc [-], c^z [-], beta_hmax [-]
    E_ph [F/A], nu_ph [-], p_{min,ph} [F/A], K^w [F/A], IM 
    ``` 

    The material parameters of the hypoplastic model with intergranular strain are given below. Further information on the model formulation and implementation is provided in the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md).

    * $\varphi_c$ [rad] is the critical friction angle and has to be provided in radian.
    * $h_s$ [F/A] and $n$ [-] describe the decrease of the maximum void ratio $e_i$ with increasing pressure during isotropic compression.  This parameter has no unit.
    * The void ratios $e_{d0}$ [-], $e_{c0}$ [-] and $e_{i0}$ [-] correspond to the densest, the critical and the loosest state at pressure $p$ = 0 F/A. These parameters have no unit.
    * The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
    * $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
    * $m_R$ governs the increase of the stiffness due to changes in the direction of the strain path. The parameter has no unit.
    * $R$ is the radius of intergranular strain. This parameter has no unit.
    * $\beta_{h0}$ and $\beta_{hmax}$ are the minimum and maximum hardening parameters of the intergranular strain and describe the evolution of the intergranular strain tensor along a strain path. These parameters have no unit.
    * $\chi^0$ and $\chi^{max}$ are the minimum and maximum intergranular strain exponent. These parameters have no unit.
    * $\epsilon^{acc}$ is the accumulation rate factor. This parameter has no unit.
    * $c_z$ is the cyclic mobility factor. This parameter has no unit.
    * $E_{ph}$ and $\nu_{ph}$ are the parameters of the phantom elasticity. The implementation of W. Fuentes uses a phantom linear elasticity overlying the constitutive model response of the Hypo-ISA model with $E_{ph}=40$ kPa and $\nu_{ph}=0.3$. We have also     included this in our implementation, but the parameters must be specified in the input for transparency. We recommend turning them off by default ($E_{ph}=0$). Deviating from the original implementation from W. Fuentes, the phantom elasticity in the numgeo    implementation is only active when the mean effective stress is equal to or drops below $p_{min,ph}$.
    * $\bar{K}^w$ is the bulk modulus of pore water for locally undrained simulations (and only for those). If no locally undrained simulation is to be performed, $K^w=0$ should be set.
    * $IM$ is a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. $IM=1$ corresponds to a Forward Euler (FE) integration scheme, with $IM=2$ a modified FE is used with (sub)substepping for the   integration of the ISA part of the model. A Modified Euler integration is currently being tested.

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
* Hypoplastic factors: `fz`, `fb`, `fd`, `fe`
* Mobilised friction angle: `phi_mob`
* Relative density: `rel-density`

---
