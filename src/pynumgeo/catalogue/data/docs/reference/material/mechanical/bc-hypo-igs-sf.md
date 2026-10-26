# Bio-Cemented Hypoplasticity + Intergranular Strain + Semi-Fluidized State and Fabric Change Effects (BC-HYPO-IGS-SF): 

Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain extension (Niemunis and Herle, 1997)[@niemunis1997] and fabric change effects as well as semifluidized state by Tafili et al. (2025) [@tafili2024hypoplastic] as proposed by Tafili et al. (2026) [@tafili2026biocem] (referred to in the following as BC-Hypo-IGS-SF). 
The numgeo keyword reads:

```numgeo 
*Mechanical = BC-Hypo-IGS-SF   
** phi [rad/deg], h_s (F/A), n (-), e_d0 (-), e_c0 (-), e_i0 (-), alpha (-), beta (-)
** m_T (-), m_R (-), R (-), beta_R (-), chi (-), c_z (-), z_max (-)
** c_l (-), c_r (-), lambda (-), a_l (-), c_mn (-), p_th (F/A), n_l (-), f_l (-), p_inr (F/A)
** m_f (-), m_e (-), k_e (-), a_p (F/A), b_p (-), h_p (-)
``` 

The material parameters of the Hypo-IGS-SF model are given in the following. Further information on the model constitutive equations are provided in [@tafili2026biocem].

* $\varphi_c$ (degree or rad) is the critical friction angle and has to be provided in radian.
* $h_s$ (F/A) and $n$ (-) describe the decrease of the limiting void ratios $e_i$, $e_c$ and $e_d$ with increasing pressure during isotropic compression. The parameter $n$ has no unit.
* The void ratios $e_{d0}$ (-), $e_{c0}$ (-) and $e_{i0}$ (-) correspond to the densest, the critical and the loosest state at pressure $p$ = 0 F/A. These parameters have no unit.
* The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
* $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
* $R$ is the radius of intergranular strain. This parameter has no unit.
* $\beta_R$ and $\chi$ describe the evolution of the intergranular strain tensor along a strain path, i.e. the reduction of the shear modulus with increasing shear strain. These parameters have no unit.
* $m_R$ and $m_T$ govern the increase of the stiffness due to changes of the direction of the strain path by $180^\circ$ ($m_R$) or $90^\circ$ ($m_T$), respectively. These parameters have no unit. An often applied assumption is: $m_T = m_R/2$.
* $c_z$ is the cyclic mobility factor. This parameter has no unit.

Parameters of the SF extension

* $c_r$ and $c_l$ control the evolution rate of the strain liquefaction factor $l$. $c_r$ can be set to a default value of 1000.

* $\lambda$ and $a_l$ is a semi-fluidised state constants.

* $c_{mn}$ is a parameter balancing the stress-strain hystheresis under undrained triaxial loading

* $p_{th}$ is the threshold effective stress. $p_{th}$ can be set to a default value of 10.

* $n_l$ is a semi-fluidised state constant, default value is 8.0.

* $f_l$ is a semi-fluidised state constant, default value is 0.01.

* $p_{inr}$ is a semi-fluidised state constant, default value is 25 kPa.


Parameters of the (bio)cementation extension

* $a_p$ and $b_p$ are used to determine the initial bonding strength, $p_{b0}$ with different cement content $C_c$, which is a state variable (statev(37)) in %

* $h_p$ controls the rate of bonding degradation with plastic straining

* $k_e$ and $m_e$ account for the cementation influence on the characteristic void ratios

* $m_f$ controls the rate of increase in $\varphi_c$ with respect to $C_c$, which is a state variable (statev(37)) in %

## Optional parameters

```numgeo
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```
    
* `bulk_water, Kw`: Bulk modulus of pore water for locally undrained simulations (and only for those). Per default $K^w=0$ F/A. To activate locally undrained conditions, $K^w>0$ must be set by the user.

* `projection_dev, value`: specifies the friction angle for the projection of stress states onto the Matsuoka-Nakai failure surface defined by a user defined friction angle $\varphi^{cut}$ in degree. Per default `value=-1` (no projection). For `value=0` the cut-off friction angle is automatically determined by numgeo and for `value=>0°`, $\varphi^{cut}=$ `value` is used. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

* `min_pressure, value`: Minimum mean effective stress in kPa (compression = positive). The default is `value=0.01` kPa.

* `integrator`: a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. integrator=1 (default) corresponds to a Forward Euler (FE) integration scheme, with integrator=2 a Euler-Richards integration scheme with adaptive time incrementation is used.

---

## State variables

In addition to the (effective) stress, the hypoplastic constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio: $e$, `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.

* Intergranular strain: $\mathbf{h}$, `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`. Only in combination with the intergranular strain extension. Prescribing $\mathbf{h}_0$ is not mandatory, if omitted, $\mathbf{h}=\mathbf{0}$ is assumed. $h_{ii} = -R / \sqrt{3}$ for $i=\{x,y,z\}$ corresponds to an isotropically consolidated state.

The state variables can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.

```numgeo 
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
element_set_name, int_strain11, <value>
element_set_name, int_strain22, <value>
element_set_name, int_strain33, <value>\
element_set_name, cement_content, <value> (in %)
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
* *statev(37)* = $C_c$ in %

---

## Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Intergranular strain: `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`.
* Stress projection: `iproj`. Flag that indicates if the stress correction is active (see Theory Manual). `iproj` takes the value of 0 if the stress projection is inactive.
* Hypoplastic factors: `fz`, `fb`, `fd`, `fe`,
* Semi-fluidised factors: `l_sf`, `se`, `pr`
* Bonding strength $p_B$: `pbond`

---
