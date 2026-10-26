# Mohr-Coulomb: 

Linear elastic - perfectly plastic model with Mohr-Coulomb yield and failure criterion available in two different implementations:

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Mohr-Coulomb__

    ---

    [:octicons-arrow-right-24: Mohr-Coulomb with rounded corners and elasto-plastic consistent Jacobian](#mohr-coulomb)

-   :material-lightbulb-on-outline:{ .lg .middle } __Mohr-Coulomb-2__

    ---

    [:octicons-arrow-right-24: Mohr-Coulomb with exact yield surface, elastic Jacobian and elasto-plastic Jacobian in strength reduction](#mohr-coulomb-2)

-   :material-lightbulb-on-outline:{ .lg .middle } __Mohr-Coulomb-3__

    ---

    [:octicons-arrow-right-24: Mohr-Coulomb with exact yield surface and elasto-plastic tangent Jacobian](#mohr-coulomb-3)

</div>

---

## Mohr-Coulomb

A Mohr-Coulomb model in the version proposed by Abbo et al. (2011)[@abbo2011] has been implemented in *numgeo*. The numgeo keyword reads:

```numgeo 
*Mechanical = Mohr-Coulomb   
E (F/A), nu (-), c (F/A), phi_c (rad),  psi (rad), theta_t [deg]
```
The material parameters of the Mohr-Coulomb model with elasto-plastic Jacobian are given in the following.  

* $E$ (F/A) is the Young's modulus of the material.
* $\nu$ (-) is the Poisson's ratio.
* $c$ (F/A) is the cohesion.
* $\varphi_c$ (rad) is the critical friction angle.
* $\psi$ (rad) is the dilation angle.
* $\theta_t$ [deg] is the transition lode angle for the round-off at the compression and extension corners. Following the recommendations by Abbo et al. (2011)[@abbo2011], the transition angle is restricted to $25.0^\circ \le \theta_t \le 29.5^\circ$.

!!! note "Rounded corners in deviatoric plane"
    This model slightly deviates from the original Mohr-Coulomb model in terms of the shape of the yield surface due to a hyperbolic approximation in the meridional plane and rounded corners in the deviatoric plane, controlled by the distance towards the apex $a = \alpha \cot\varphi$ and the transition lode angle $\theta_t$, respectively. In the current implementation, a constant value of $\alpha = 0.05$ is used, while $\theta_t$ is a material parameter.

### State variables
In addition to the (effective) stress, the Mohr-Coulomb constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio: $e$, `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort. However, for the evaluation of the material response, the void ratio is not considered in the constitutive model. It is just for output-purposes.

The state variables can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.
```numgeo
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
```
* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section User defined state variables. The position of the state variable in the associated vector is as follows: *statev(1)* = $e$

### Optional Parameters

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```
Definition of optional parameters is not mandatory. The specification can also be made individually:

* `tol_yield`: Tolerance for yield surface. Default is $10^{-4}$.
* `min_pressure`: Minimum mean effective stress in kPa (compression = positive). Use this parameter to define a tension cut-off, e.g. `min_pressure, 0.` to cut-off any tensile stresses.
* `return_mapping`: Method for returning inadmissible stress states on the yield surface. You can choose between Closest Point Projection (CPP) `return_mapping, 0` and Cutting Plane Algorithm (CPA) `return_mapping, 1`. Default is CPA.
* `cep_ratio`: Ratio between elastic and elasto-plastic tangent stiffness $\boldsymbol{C}$ returned by the constitutive model. For `cep_ratio, 0.0` the linear elastic tangent stiffness $\boldsymbol{C}=\boldsymbol{C}^{el}$ is returned, for `cep_ratio, 1.0` the consistent algorithmic (elasto-plastic) tangent stiffness $\boldsymbol{C}=\boldsymbol{C}^{ep}$ is returned. Default is `cep_ratio, 0.999`, i.e. $\boldsymbol{C}=0.001\boldsymbol{C}^{el}+0.999\boldsymbol{C}^{ep}$
* `reduction_psi`: Flag that controls whether the reduction of dilatancy angle $\psi$ should be considered during a strength-reduction analysis. For `reduction_psi = 1`, the dilatancy angle is updated according to $\psi^{red}=\tan^{-1}\left(\dfrac{\tan \psi}{FoS}\right)$. See also [Strength reduction](../../../theory/solution-method/strength-reduction.md) in the Theory Manual.
* `reduction_nu`: Flag that controls whether Poisson's ratio $\nu$ should be modified during a strength-reduction analysis to guarantee the inequality $\sin \varphi \leq 1 - 2\nu$ according to Zheng et al.[@zheng2005]. For `reduction_nu = 1`, $\nu$ is modified; for `reduction_nu = 0`, $\nu=const.$ (default). See also [Strength reduction](../../../theory/solution-method/strength-reduction.md) in the Theory Manual.

### Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Current cohesion: `cohesion`
* Current friction angle: `friction_angle`
* Current dilation angle: `dilation_angle`
* Plastic points (areas undergoing plastic deformation): `plastic_points`

---

## Mohr-Coulomb-2

This implementation of the Mohr-Coulomb model utilizes the exact formulation of the yield surface. It provides the elastic Jacobian, except in [strength-reduction](../../step/reduction.md) steps, where it provides the elasto-plastic Jacobian of the stress return (optional parameter `cep_ratio_reduction`). Compared to the first [Mohr-Coulomb](#mohr-coulomb) implementation, this version is significantly faster as it eliminates the need for sub-stepping. The numgeo keyword reads:

```numgeo 
*Mechanical = Mohr-Coulomb-2   
E (F/A), nu (-), c (F/A), phi_c (deg),  psi (deg), p_t (F/A)
```

The material parameters of the Mohr-Coulomb-2 model are given in the following.  

* $E$ (F/A) is the Young's modulus of the material.
* $\nu$ (-) is the Poisson's ratio.
* $c$ (F/A) is the cohesion.
* $\varphi_c$ (deg) is the critical friction angle.
* $\psi$ (deg) is the dilation angle.
* $p_t$ (F/A) is the tension cut value, positive values refer to tension, i.e. $p_t=1$ kPa will cut the models response at tensile stresses smaller that 1 kPa.

!!! warning "Elastic Jacobian"

    The use of elastic tangent stiffness offers both advantages and disadvantages: it is more robust in the plastic limit, but it may require more iterations to achieve global equilibrium. Nevertheless, the increased calculation speed due to the absence of sub-stepping—often results in a substantial reduction in overall simulation time compared to its elasto-plastic counterpart. In strength-reduction steps the elasto-plastic Jacobian is used by default; `cep_ratio_reduction, 0` selects the elastic Jacobian also there.

!!! warning "Angles in degree"

    Unlike [Mohr-Coulomb](#mohr-coulomb) (radian), Mohr-Coulomb-2 expects the friction and dilatation angle in degree.

### Optional Parameters

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```
Definition of optional parameters is not mandatory. The specification can also be made individually:

* `fos-dilatation, <value>`: switch for the reduction of the dilatation angle $\psi$ in [strength-reduction](../../../theory/solution-method/strength-reduction.md) simulations. For `<value>` $\geq 0.999$, $\tan\psi$ is divided by the factor of safety like $\tan\varphi_c$; for `<value>` $< 0.999$, $\psi$ is kept constant. In both cases $\psi$ never exceeds the (reduced) friction angle. Default is `<value>` = 1 (reduction).
* `fos-poisson, <value>`: switch for the modification of the Poisson's ratio $\nu$ in [strength-reduction](../../../theory/solution-method/strength-reduction.md) simulations (Zheng et al.[@zheng2005]). For `<value>` $\geq 0.999$, $\nu$ is modified; for `<value>` $< 0.999$, $\nu$ is kept constant. Default is `<value>` = 1 (modification).
* `cep_ratio_reduction, <value>`: ratio $r$ of the elasto-plastic Jacobian in [strength-reduction](../../step/reduction.md) steps, $\boldsymbol{C} = (1-r)\,\boldsymbol{C}^{el} + r\,\boldsymbol{C}^{ep}$. $\boldsymbol{C}^{ep}$ is the derivative of the returned stress with respect to the strain increment, computed by forward differences of the stress return (one additional return per strain component at plastic integration points); it is consistent with the return in all regimes, including the rotation of the principal axes. At the apex the elastic stiffness is used. Default is `<value>` = 1 (elasto-plastic Jacobian in strength-reduction steps; the elastic Jacobian in all other steps). `cep_ratio_reduction, 0` selects the elastic Jacobian also in strength-reduction steps. With the elastic Jacobian the iteration of a strength reduction converges linearly and may stop before the mechanism has formed; see [strength reduction](../../../theory/solution-method/strength-reduction.md#jacobian-of-mohr-coulomb-2) and the [geogrid-reinforced wall](../../../benchmark/strength-reduction/geogrid-wall-feligha-2023.md).

### Additional (material) state variables

The `Mohr-Coulomb-2` model features additional state variables. These variables can be initialised using the [*Initial conditions, type = state variables](../../initial-conditions/state-variables.md) command or visualised using the [*Output](../../output/index.md) command. The following state variables are available:

* `void_ratio` (position 1 in `statev`): void ratio.
* `fos` (position 2 in `statev`): factor of safety (only meaningful in strength-reduction analyses).
* `eps_pl_dev` (position 3 in `statev`): equivalent deviatoric plastic strain.
* `coh` (position 4 in `statev`): cohesion.
* `fric` (position 5 in `statev`): friction angle (deg).
* `dil` (position 6 in `statev`): dilatation angle (deg).
* `yield-surf` (position 7 in `statev`): regime of the last stress return: 0 elastic, 1 triaxial compression edge, 2 regular (Coulomb plane), 3 triaxial extension edge, 9 apex.

!!! warning ""

    Notice that values of `coh`, `fric` or `dil` greater than zero specified in `*Initial conditions` override the respective material parameters given in the `*Material` definition.

!!! info "Properties as random fields"

    You to tell numgeo that properties (friction angle `fric`, cohesion `coh` or/and dilatation angle `dil`) should be read in from a text file, e.g. as random fields (spatially varying distributions) using the [*Initial conditions, type = state variables](../../initial-conditions/state-variables.md). An example is provided in the tutorial [Slope with random field](../../../tutorial/slope-stability-simulations/pruska-2009-rf.md).

---

## Mohr-Coulomb-3

This implementation of the Mohr-Coulomb model was provided by [Johan Clausen](https://www.au.dk/en/jc@cae.au.dk/)[@clausen2006,@clausen2006b,@clausen2007,@clausen2007b,@clausen2015] from Aarhus University. It uses the exact formulation of the yield surface and provides the elasto-plastic Jacobian. Compared to the first [Mohr-Coulomb](#mohr-coulomb) implementation, this version is significantly faster because it eliminates the need for sub-stepping; compared to [Mohr-Coulomb-2](#mohr-coulomb-2), it returns the elasto-plastic Jacobian in all steps. Of the three available Mohr-Coulomb implementations, this one is the most sophisticated. The numgeo keyword reads:

```numgeo 
*Mechanical = Mohr-Coulomb-3   
E (F/A), nu (-), c (F/A), phi_c (deg), psi (deg), p_t (F/A)
```

The material parameters of the Mohr-Coulomb-3 model are given in the following.  

* $E$ (F/A) is the Young's modulus of the material.
* $\nu$ (-) is the Poisson's ratio.
* $c$ (F/A) is the cohesion.
* $\varphi_c > 0$ (deg) is the critical friction angle.
* $\psi$ (deg) is the dilatancy angle.
* $p_t$ (F/A) is the tension cut value, positive values refer to tension, i.e. $p_t=1$ kPa will cut the models response at tensile stresses smaller that 1 kPa.

!!! warning "Nonzero $\varphi$"

    The Mohr–Coulomb–3 formulation does not support $\varphi=0^\circ$. For such cases, use Mohr–Coulomb–2, which does permit $\varphi=0^\circ$. A Tresca model by [Johan Clausen](https://www.au.dk/en/jc@cae.au.dk/) is planned for a future release. To guarantee robustness of the elasto-plastic Jacobian at the Apex, $\psi \geq 0.01^\circ$ is recommended for this implementation, which is rigorously enforced in the code.

### Optional Parameters

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
```
Definition of optional parameters is not mandatory. The specification can also be made individually:

* `fos-dilatation, <value>`: switch for the reduction of the dilatation angle $\psi$ in [strength-reduction](../../../theory/solution-method/strength-reduction.md) simulations. For `<value>` $\geq 0.999$, $\tan\psi$ is divided by the factor of safety like $\tan\varphi_c$; for `<value>` $< 0.999$, $\psi$ is kept constant. In both cases $\psi$ never exceeds the (reduced) friction angle. Default is `<value>` = 1 (reduction).
* `fos-poisson, <value>`: switch for the modification of the Poisson's ratio $\nu$ in [strength-reduction](../../../theory/solution-method/strength-reduction.md) simulations (Zheng et al.[@zheng2005]). For `<value>` $\geq 0.999$, $\nu$ is modified; for `<value>` $< 0.999$, $\nu$ is kept constant. Default is `<value>` = 1 (modification).

### Additional (material) state variables

The `Mohr-Coulomb-3` features additional state variables. These variables can be initialised using the [*Initial conditions, type = state variables](../../initial-conditions/state-variables.md) command or visualised using the [*Output](../../output/index.md) command. The following state variables are available:

* `void_ratio` (position 1 in `statev`): void ratio.
* `fos` (position 2 in `statev`): factor of safety (only meaningful in strength-reduction analyses).
* `coh` (position 4 in `statev`): cohesion.
* `fric` (position 5 in `statev`): friction angle (deg).
* `dil` (position 6 in `statev`): dilatation angle (deg).
* `eps_pl_dev` (position 7 in `statev`): equivalent deviatoric plastic strain.

!!! warning ""

    Notice that values of `coh`, `fric` or `dil` greater than zero specified in `*Initial conditions` override the respective material parameters given in the `*Material` definition.

!!! info "Properties as random fields"

    You to tell numgeo that properties (friction angle `fric`, cohesion `coh` or/and dilatation angle `dil`) should be read in from a text file, e.g. as random fields (spatially varying distributions) using the [*Initial conditions, type = state variables](../../initial-conditions/state-variables.md). An example is provided in the tutorial [Slope with random field](../../../tutorial/slope-stability-simulations/pruska-2009-rf.md).

---

## References
