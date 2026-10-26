# Matsuoka Nakai: 

Linear elastic - perfectly plastic model with Matsuoka-Nakai yield and failure criterion. The material parameters of the Matsuoka-Nakai elasto-plasticity model are given in the following. The numgeo keyword reads:

```numgeo 
*Mechanical = Matsuoka-Nakai-2
E (F/A), nu (-), tan(phi_c) (-), c (F/A), F^{fr} (-), omega (-)
```

* $E$ (F/A) is the Young's modulus of the material.
* $\nu$ (-) is the Poisson's ratio.
* $\text{tan}(\varphi_c)$ is the critical friction angle.
* $c$ (F/A) is the cohesion.
* $F^{fr}$ is a switch for the calculation of the flow rule. For $F^{fr}=0$ the Matsuoka-Nakai flow rule is used and for $F^{fr}=1$ the Drucker-Prager one.
* $\omega$ is the ratio between the dilatancy angle $\psi$ and the friction angle $\phi_c$. For $\omega=\psi/\phi_c=1$ an associated flow rule is used. Note that a non-associated flow rule ($\omega \neq 1$) is only allowed in combination with the Drucker-Prager flow rue ($F^{fr}=1$).

## State variables
In addition to the (effective) stress, the Matsuoka-Nakai constitutive model takes additional state variables. Performing simulations with this model requires the prescription of those. The following state variables are contained in the model:

* Void ratio: $e$, `void_ratio`. The prescription of the void ratio is mandatory, if the initialization is omitted or wrong values are prescribed the simulation will abort. However, for the evaluation of the material response, the void ratio is not considered in the constitutive model. It is just for output-purposes.

The state variables can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.
```numgeo 
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
```
* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section: User defined state variables. The position of the state variable in the associated vector is as follows: *statev(1)* = $e$

## Additional output variables
The following additional output variables are available in the [*Output](../../output/index.md) command:

* Void ratio: `void_ratio`
* Mobilized friction angle: `friction_angle`
* Mean effective stress $p=\sigma_{ii}/3$: `stress_mean`
* Deviatoric stress: `stress_dev`
* Lode angle: `lode_angle`
* Plastic points (areas undergoing plastic deformation): `plastic_points`
* Volumetric plastic strain: `strainpl_vol`
* Deviatoric plastic strain: `strainpl_dev`
