# Accelerators

```numgeo
*Accelerator, Type = <method> [, default]
<subsequent line>
```

The `*Accelerator` keyword replaces the former keyword `*Line search`, which is still accepted.

In strongly nonlinear problems, the Newton-Raphson solution procedure - used by default in `numgeo` - may fail to converge or even diverge during equilibrium iterations. To address such issues and improve convergence behaviour, solution accelerators are available.

Two fundamentally different strategies are provided. Line search methods scale the iterative correction along its original direction:

$$
\boldsymbol{u}^{t+\Delta t} = \boldsymbol{u}^t + \Delta \boldsymbol{u}^{\Delta t}_{i=0} + \lambda \boldsymbol{c}_i
$$

Anderson acceleration combines information from successive iterations to modify both the magnitude and the direction of the update. Both approaches are disabled by default and can be activated using the `*Accelerator` command.

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: Learn more about the theoretical background](../theory/solution-method/accelerator.md)
</div>

### Keyword Options

- `Type = <method>`

    Specifies the acceleration strategy to be used. This keyword is mandatory. Available options are:

    - `Relaxation` - uses a fixed scaling factor
    - `Back-looking` - determines $\lambda$ from the previous iteration using a linear model
    - `Linear` - determines $\lambda$ using a linear model with an additional residual assembly
    - `Anderson` - depth-1 or depth-2 Anderson acceleration of the fixed-point iteration

--------

## Type = Relaxation

```numgeo
*Accelerator, type = relaxation [, default]
lambda
```

This option applies a constant scaling factor $\lambda$ to the correction vector in each iteration. A typical value is in the range $0 \leq \lambda \leq 1$.

If `default` is specified, $\lambda = 0.8$ is used.

---------

## Type = Back-looking

```numgeo
*Accelerator, type = back-looking [, default]
lambda_min, lambda_max
```

This method estimates an optimal scaling factor $\lambda$ from a linear interpolation of the residual using information already available from the previous iteration. No additional residual assembly is required.

- `lambda_min`: Lower bound for the scaling factor  
- `lambda_max`: Upper bound for the scaling factor

If `default` is specified, no subsequent line is required and `lambda_min = 0.5` and `lambda_max = 1.0` are used.

---------

## Type = Linear

```numgeo
*Accelerator, type = linear [, default]
lambda_min, lambda_max
```

This method estimates an optimal scaling factor $\lambda$ by linearly interpolating the residual. Unlike the back-looking method, this requires one additional residual assembly per iteration. `*Accelerator, type=linear, default` is recommended in [strength-reduction](./step/reduction.md) steps.

- `lambda_min`: Lower bound for the scaling factor  
- `lambda_max`: Upper bound for the scaling factor

If `default` is specified, no subsequent line is required and `lambda_min = 0.5` and `lambda_max = 1.0` are used.

!!! note "Multi-field simulations"
    `Linear` computes one factor from the complete residual and correction vectors and applies it to the complete correction. `Back-looking` instead has separate branches for displacement, water pressure and volumetric Jacobian $J$, but no dedicated air-pressure branch. Neither option implements repeated backtracking with a scaled residual-norm acceptance test. See [Nonlinear solution of unsaturated flow](../theory/solution-method/unsaturated-flow.md) for the implications in coupled hydraulic problems.


---------

## Type = Anderson

```numgeo
*Accelerator, type = anderson [, default]
alpha_max, depth
```

This method accelerates the convergence of fixed-point iterations by combining the current and previous corrections in a least-squares optimal way. Unlike line search, it modifies both the magnitude and the direction of the iterative update. It is particularly effective in problems where the Jacobian is held constant across iterations, such as strength reduction analyses with an elastic tangent (Mohr-Coulomb-2 with `cep_ratio_reduction, 0`). If the mixing coefficients are not finite (overflow in a diverging iteration), a plain step is taken.

- `alpha_max`: Upper bound for the mixing parameter $|\alpha|$
- `depth`: depth of the Anderson accelerator

If `default` is specified, no subsequent line is required and `alpha_max = 2.0` and `depth=1` is used.
