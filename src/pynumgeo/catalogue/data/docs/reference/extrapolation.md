# Extrapolation

```numgeo 
*Extrapolation, <strategy>
``` 

Use this keyword to specify an extrapolation strategy of the initial estimate of the solution at the beginning of each increment (except for the first one). By default, a `linear` extrapolation is performed.  

<div class="grid cards" markdown>
-   :material-lightbulb-on-outline:{ .lg .middle } __Theory Manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementations](../theory/solution-method/initial-solution-increment.md)
</div>

You can choose between the following `<strategy>`:

- `linear`: Default, a linear extrapolation, i.e. $\Delta d_{n+1} = \Delta d_n/\Delta t_n \Delta t_{n+1}$

- `quadratic`: quadratic extrapolation based on the last three known values of the solution $\Delta d_{n+1}(d_{n-2},d_{n-1},d_n)$. For the first three increments of each new step, `linear` extrapolation is used.

- `coupled`: Extrapolation of solution with time considering the different nature of solution variables - displacements are extrapolated linear in time and pressures (pw, pa) using a Backward Euler approach based on known velocities

- `constant`: an unscaled approximation based on the last increment is assumed, i.e. $\Delta d_{n+1} = \Delta d_n$.

- `none`: no extrapolation is performed, the elements are called with $\Delta d_{n+1} = 0$. This method usually slows down the convergence finding, but can help in case of strong convergence difficulties.

- `none-pw`: no extrapolation is performed for the pore water pressure ($\Delta d_{n+1} = 0$). For the solid displacement, a linear extrapolation is applied ($\Delta d_{n+1} = \Delta d_n/\Delta t_n \Delta t_{n+1}$). This method may help in case of convergence finding in infiltration problems.

- `fos-linear`: linear extrapolation of the solution increment with the factor of safety $\text{FoS}$ instead of time, i.e. $\Delta d_{n+1} = \Delta d_n / \Delta \text{FoS}_n \cdot \Delta \text{FoS}_{n+1}$. Intended for use in strength reduction analyses (`*Reduction`) where time has no physical meaning and the driving quantity is $\text{FoS}$. For the first increment of each step, `linear` extrapolation in time is used as a fall-back.

- `fos-hyperbolic`: hyperbolic extrapolation of the solution increment with the factor of safety $\text{FoS}$. The last three converged values of $(\text{FoS}, \max|\Delta d|)$ are used to fit a hyperbolic model of the form $\max|\Delta d| = A / (\text{FoS}_{\text{lim}} - \text{FoS})$, from which a scalar scaling factor $\kappa$ is derived and applied to the previous solution increment: $\Delta d_{n+1} = \kappa \Delta d_n$. Intended for use in strength reduction analyses near the critical $\text{FoS}$, where the relation between $\text{FoS}$ and displacements becomes strongly non-linear. Falls back to `linear` extrapolation when fewer than three converged increments are available or when the fit does not satisfy the safeguards on monotonicity, slope sign, asymptote location and scaling range.