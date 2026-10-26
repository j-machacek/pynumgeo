---
title: Modified Cam Clay (Modified-Cam-Clay)
---


```numgeo 
*Mechanical = Modified-Cam-Clay
nu (-), kappa (-), lambda (-), varphi [^circ], e_{ref} (-), beta (-), K_{Lode} (-), K^w (F/A)
f^Lambda (-), f^1 (-)
```

!!! note "Good to know"
    The model is implemented using different explicit integration methods which required a reformulation of the equation for the plastic multiplier $\dot{\Lambda}$. For this, two approaches are implemented from which the user can choose. For more information on the equations and details on the integration methods, please refer to the Theory Manual.

The Modified Cam Clay model requires 6 material parameters ($\nu$, $\kappa$, $\lambda$, $\varphi$, $\beta$, $K_{Lode}$). The current implementation requires the specification of 4 additional parameters, these are not model parameters per se but parameters that control the integration and the drainage conditions of the implementation.


-   $\nu$ is the Poisson's ratio. This parameter has no unit. Typical range: $0-0.499$.

-   $\kappa$ is the swelling index. This parameter has no unit.

-   $\lambda$ is the compression index. This parameter has no unit.

-   $\varphi$ is the friction angle. This parameter is given in degree.

-   $e_{ref}$ is the reference void ratio defined as the void ratio at a reference mean effective stress $p_{ref}=1$ kPa in $w-ln(p)$-space, i.e. it pins the NCL to a reference point.



**Parameters controlling the implementation:**

-   $f^\Lambda$ is a switch to choose between two methods to approximate the plastic multiplier $\Lambda$. Recommended value is $f^{\Lambda}=1$.

    -   $f^{\Lambda}=1$: The plastic multiplier is approximated as follows:

        $\dot{\Lambda} = \text{exp}\left(f^1 F / (f^2 p)\right) ||\dot{\varepsilon}||$, 
        
        where $F$ is the value of the yield surface evaluated for the current stress state, $\dot{\varepsilon}$ is the (total) strain rate, $p$ is the mean effective stress and $f^1$ and $f^2$ are material parameter.

    -   $f^{\Lambda} \neq 1$: The plastic multiplier is approximated as follows:

        $\dot{\Lambda} = \text{OCR}^{f^1} ||\dot{\varepsilon}||$, 
        
        where OCR is the overconsolidation ratio OCR$=p_c/p_{c0}$, $\dot{\varepsilon}$ is the (total) strain rate and $f^1$ is a material parameter.

-   $c^1$ controls the "sharpness" of the transition between elastic and plastic behavior. Recommended values are:

    - $f^{\Lambda}=1$:
        - $f^1 \approx 50-100$
    - $f^{\Lambda} \neq 1$:
        - $c^1 \approx 10$

-   $K^w$ (in kPa) is the Bulk modulus of water.

    -   For drained simulations or simulations using coupled elements (pore-pressure elements): $K^w = 0$

    -   For simulations assuming ideally undrained conditions (with standard solid elements): $K^w > 0$, e.g. for pure water $K^w=2.2$ GPa.

## Optional Parameters

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...`
```

A list of currently supported optional parameters is given below:

-   `integrator`: Numerical integrator:

    -   `integrator = 1`: Modified-Euler

    -   `integrator = 2`: Explicit Euler with Richards extrapolation of Order 2

    Per default, the Explicit Euler with Richards extrapolation method is used (`integrator = 1`).

-   `tol_stress`: Tolerance $T^\sigma$ for error $\epsilon^\sigma$ evaluated based on constitutive stress. The solution is accepted if $\epsilon^\sigma < T^\sigma$. Per default $T^\sigma = 10^{-4}$. Stress control can be deactivated by setting $T^\sigma=1$ (not recommended!).

-   `num_diff`: Method for the numerical differentiation used for the estimation of the material Jacobian
    (tangent stiffness) $(\partial \boldsymbol{\sigma})/(\partial \boldsymbol{\varepsilon})$:

    -   `num_diff=1`: Forward Euler of $O(h)$, $\dfrac{\partial f}{\partial x} \approx \dfrac{f(x_0+\theta)-f(x_0)}{\theta}$

    -   `num_diff=2`: Central Differences of $O(h^2)$, $\dfrac{\partial f}{\partial x} \approx \dfrac{f(x_0+\theta)-f(x_0-\theta)}{2\theta}$

-   `perturbation`: The perturbation factor $f^\theta$ used in the numerical differentiation to evaluate the
    material tangent stiffness $(\partial \boldsymbol{\sigma})/(\partial \boldsymbol{\varepsilon})$.
    The perturbation is $\theta=\text{max}(||\dot{\varepsilon}||)f^\theta$, where $||\dot{\varepsilon}||$ is  the $L_2$ norm of the strain rate. The default value is $f^\Theta=10^{-7}$.

-   `jacobi`: Method to evaluate the Jacobian:

    -   `jacobi = 1` (Default): The material Jacobian is determined at the end of the numerical integration as the tangent at the final stress state.

    -   `jacobi = 2`: The material Jacobian is calculated as the
        weighted sum of all Jacobians evaluated at the end of each
        converged Runge-Kutta substep.

## State variables

In addition to the (effective) stress, the Modified Cam-Clay
constitutive model takes additional state variables. Performing
simulations with this model requires the prescription of those. The
following state variables are contained in the model:

-   Void ratio: $e$, `void_ratio`. For $f^{pc}=1$, the prescription of
    the void ratio is mandatory, if the initialization is omitted or
    wrong values are prescribed the simulation will abort.

-   Overconsolidation ratio: `OCR`, the prescription of `OCR` is
    mandatory, if the initialization is omitted or wrong values are
    prescribed the simulation will abort.

-   Pore water pressure: $p^w$, `Pw`. Only in case of ideally undrained
    conditions $K^w>0$. If no value for $p^w$ is prescribed, $p^w_0=0$
    kPa is assumed.

### Initialisation
The state variables can be initialized in two different ways:

-   Using the `*Initial conditions, type = state variables` command in
    the input file, e.g.

    `*Initial conditions, type = state variables`  
    `element_set_name, OCR, <value>`

-   Using the interface for user-defined initial state variables. In
    this approach, the vector holding the state variables is filled
    directly in a Fortran [user routine](../../user/initial-statev.md). The position of the state variable
    in the associated vector is as follows:

    -   `statev(1)` = $e$

    -   `statev(4)` = $p^w$

    -   `statev(8)` = OCR

!!! tip "Recommended initialisation method"

    We recommend the initialisation of the model using the overconsolidation rato OCR. From the user prescribed OCR the initial void ratio $e_0$ and the preconsolidation pressure $p_C$ will be automatically determined by the constitutive model.


## Additional output variables

The following additional output variables are available in the `*Output`
command (see [here](../../output/index.md)):

-   Void ratio $e$: `void_ratio`

-   Preconsolidation pressure $p_c$: `Pc`

-   mean effective stress $p_{c0}$ for which a pseudo yield surface
    passes the current stress state: `Pc0`

-   Overconsolidation ratio OCR: `OCR`

-   Pore water pressure $p^w$ (for ideally undrained simulations with
    $K^w > 0$): `Pw`

-   Value of the yield function $F(\boldsymbol{\sigma})$ for the current
    stress state $\boldsymbol{\sigma}$: `Fyield`

-   Slope $M(\varphi,\boldsymbol{\sigma})$ of the critical state line
    for the current stress state $\boldsymbol{\sigma}$: `CSL`

-   Lode angle $\cos\left(3\varTheta(\boldsymbol{\sigma})\right)$:
    `Lode`