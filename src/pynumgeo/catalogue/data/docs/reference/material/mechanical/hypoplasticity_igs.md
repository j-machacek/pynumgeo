# Hypoplasticity + Intergranular Strain (Hypo+IGS): {#sec:mat_hypoplasticity}

Hypoplastic model for sand according to von Wollfersdorff (1996)[@wolffersdorff1996] with intergranular strain extension (Niemunis and Herle, 1997)[@niemunis1997] in two different implementations:

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Hypoplasticity__

    ---

    [:octicons-arrow-right-24: The original implementation in numgeo based on an adaptive Modified Euler scheme](#hypoplasticity)

-   :material-lightbulb-on-outline:{ .lg .middle } __Hypo-IGS__

    ---

    [:octicons-arrow-right-24: Novel implementation introduced in 2025 featuring increased user-friendliness and projection methods preventing/reducing overshooting](#hypo-igs)
</div>

---

## Hypoplasticity

```numgeo 
*Mechanical = Hypoplasticity   
phi [rad], nu (-), h_s (F/A), n (-), e_d0 (-), e_c0 (-), f_ei0 (-), alpha (-) 
beta (-), m_T (-), m_R (-), R (-), beta_R (-), chi (-), K^w (F/A)
```
The material parameters of the hypoplastic model with intergranular strain are given in the following.  

* $\varphi_c$ [rad] is the critical friction angle and has to be provided in radian.
* $h_s$ (F/A) and $n$ (-) describe the decrease of the limiting void ratios $e_i$, $e_c$ and $e_d$ with increasing pressure during isotropic compression. The parameter $n$ has no unit.
* The void ratios $e_{d0}$ (-) and $e_{c0}$ (-) correspond to the densest and the critical state. The parameter $f_{ei0}$ is used to calculate the void ratio at the loosest state $e_{i0}=f_{ei0}\cdot e_{c0}$ at pressure $p$ = 0 F/A. Usually $f_{ei0}=1.15$ is used. These parameters have no unit.
* The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
* $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
* $R$ is the radius of intergranular strain. This parameter has no unit.
* $\beta_R$ and $\chi$ describe the evolution of the intergranular strain tensor along a strain path, i.e. the reduction of the shear modulus with increasing shear strain. These parameters have no unit.
* $m_R$ and $m_T$ govern the increase of the stiffness due to changes of the direction of the strain path by $180^\circ$ ($m_R$) or $90^\circ$ ($m_T$), respectively. These parameters have no unit. An often applied assumption is: $m_T = m_R/2$.
* $\bar{K}^w$ is the bulk modulus of pore water for locally undrained simulations (and only for those). The parameter is not mandatory and zero per default.

### State variables
In addition to the (effective) stress, the hypoplastic constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio: $e$, ``void_ratio``. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort.
* Intergranular strain: $R_{ij}$, ``int_strain11``, ``int_strain22``, ``int_strain33``, ``int_strain12``, ``int_strain23``, ``int_strain13``. Only in combination with the intergranular strain extension. Prescribing $R_0$ is not mandatory, if omitted, $R_{ij}$ is assumed. $R_{ii} = R_0 / \sqrt{3}$ corresponds to an isotropically consolidated state.
* Relative density $D_{r0}: `rel-density`

The state variables can be initialized in two different ways:

* Using the ``*Initial conditions, type = state variables`` command in the input file, e.g.

    ```numgeo 
    *Initial conditions, type = state variables  
    element_set_name, void_ratio, <value>  
    element_set_name, int_strain11, <value>  
    element_set_name, int_strain22, <value>  
    element_set_name, int_strain33, <value>
    ...
    ```

* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section: User defined state variables. The position of the state variables in the associated vector are as follows: 

    * *statev(1)* = $e$ 
    * *statev(2)* = $h_{11}$ 
    * *statev(3)* = $h_{22}$ 
    * *statev(4)* = $h_{33}$ 
    * *statev(5)* = $h_{12}$ 
    * *statev(6)* = $h_{23}$ 
    * *statev(7)* = $h_{13}$


### Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: ``void_ratio``
* Intergranular strain: ``int_strain11``, ``int_strain22``, ``int_strain33``, ``int_strain12``, ``int_strain23``, ``int_strain13``.
* Stress projection: ``proj``. Flag that indicates if the stress correction is active (see *Theory Manual*). ``iproj`` takes the value of 0 if the stress projection is inactive.

---

## Hypo-IGS

```numgeo 
*Mechanical = Hypo-IGS   
phi (degree or rad), h_s (F/A), n (-), e_d0 (-), e_c0 (-), e_i0 (-), alpha (-), beta (-) 
m_R (-), m_T (-), R (-), beta_R (-), chi (-)
``` 

The material parameters of the hypoplastic model with intergranular strain are given in the following. Further information on the model formulation and implementation are provided in the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md).

* $\varphi_c$ (degree or rad) is the critical friction angle and has to be provided in degree or in radian. Values larger than 1 are considered to be provided in degree.
* $h_s$ (F/A) and $n$ (-) describe the decrease of the limiting void ratios $e_i$, $e_c$ and $e_d$ with increasing pressure during isotropic compression. The parameter $n$ has no unit.
* The void ratios $e_{d0}$ (-), $e_{c0}$ (-) and $e_{i0}$ (-) correspond to the densest, the critical and the loosest state at pressure $p$ = 0 F/A. These parameters have no unit.
* The material constant $\alpha$ describes the influence of density on the peak friction angle. This parameter has no unit.
* $\beta$ mainly influences the stiffness of dense soil skeletons. This parameter has no unit.
* $m_R$ and $m_T$ govern the increase of the stiffness due to changes of the direction of the strain path by $180^\circ$ ($m_R$) or $90^\circ$ ($m_T$), respectively. These parameters have no unit. An often applied assumption is: $m_T = m_R/2$.
* $R$ is the radius of intergranular strain. This parameter has no unit.
* $\beta_R$ and $\chi$ describe the evolution of the intergranular strain tensor along a strain path, i.e. the reduction of the shear modulus with increasing shear strain. These parameters have no unit.

### Optional parameters

```numgeo
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```

Optional mechanical parameters can be used to enable locally undrained conditions, change some default settings or activate some stabilisation methods. Their use is optional.

* `phantom_E, E_ph` and `phantom_nu, nu_ph` are the parameters of the phantom elasticity. In analogy to the Hypo-ISA implementation available from [soilmodels.com](https://soilmodels.com), a phantom linear elasticity overlying the constitutive model response of the constitutive model with $E_{ph}=20$ kPa and $\nu_{ph}=0.45$ is also included in our implementation. However, it is deactivated by default and if activated, the parameters must be specified in the input for transparency. We recommend turning them off by default ($E_{ph}=0$).

* `bulk_water, Kw`: Bulk modulus of pore water for locally undrained simulations (and only for those). Per default $K^w=0$ F/A. To activate locally undrained conditions, $K^w>0$ must be set by the user.

* `projection_dev, value`: activate projection of inadmissible stress states onto the Matsuoka-Nakai failure surface defined by a cut-off friction angle $\varphi^{cut}$. By default, `value=-1` (no projection). For `0 <= value <= 5`, the cut-off friction angle is determined automatically by numgeo; for `value>5`, $\varphi^{cut}=$ `value°` is used. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

* `projection_iso, value`: activate projection of inadmissible stress states onto a pseudo primary loading surface. By default, `value=-1` (no projection). For `value=1`, the projection is activated. Consultation of the [Theory Manual](../../../theory/constitutive-models/mechanical-models/hypo-isa.md) is strongly advised before use.

* `min_pressure, value`: Minimum mean effective stress in kPa (compression = positive). The default is `value=0.01` kPa.

* `integrator`: a flag controlling which integration method should be used to advance the stress from time $t_0$ to time $t=t_0 + \Delta t$. integrator=1 (default) corresponds to a Forward Euler (FE) integration scheme, with integrator=2 a Euler-Richards integration scheme with adaptive time incrementation is used.

### State variables

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
    ```

* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section User defined state variables. The position of the state variables in the associated vector are as follows: 

    * *statev(1)* = $e$ 
    * *statev(2)* = $h_{11}$ 
    * *statev(3)* = $h_{22}$ 
    * *statev(4)* = $h_{33}$ 
    * *statev(5)* = $h_{12}$ 
    * *statev(6)* = $h_{23}$ 
    * *statev(7)* = $h_{13}$
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

### Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Intergranular strain: `int_strain11`, `int_strain22`, `int_strain33`, `int_strain12`, `int_strain23`, `int_strain13`.
* Intergranular back strain: `int_back_strain11`, `int_back_strain22`, `int_back_strain33`, `int_back_strain12`, `int_back_strain23`, `int_back_strain13`.
* Stress projection: `iproj`. Flag that indicates if the stress correction is active (see Theory Manual). `iproj` takes the value of 0 if the stress projection is inactive.
* Hypoplastic factors: `fz`, `fb`, `fd`, `fe`
* Mobilised friction angle: `phi_mob`
* Relative density: `rel-density`

---

## References
