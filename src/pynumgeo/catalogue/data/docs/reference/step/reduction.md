```numgeo 
*Reduction
<FoS_0>, <Delta FoS_0>, <Delta FoS_max>, <Delta FoS_min>
```
This procedure is used to perform a strength reduction analysis. In a reduction analysis, inertia effects are not taken into consideration. A reduction step can be linear or nonlinear, but time-dependent material effects (e.g. creep, swelling) are ignored. However, rate-dependent plasticity and hysteretic behavior are taken into account.

The following line specifies the 
- Initial factor of safety $\text{FoS}_0$
- The initial increment of the factor of safety $\Delta \text{FoS}_0$
- The maximum increment of the factor of safety $\Delta \text{FoS}_\text{max}$
- The minimum increment of the factor of safety $\Delta \text{FoS}_\text{min}$

Recommended values are:

|$\text{FoS}_0$|$\Delta \text{FoS}_0$|$\Delta \text{FoS}_\text{max}$|$\Delta \text{FoS}_\text{min}$|
|--------------|---------------------|------------------------------|------------------------------|
|1.            | 0.01                | 0.05                         | 0.0001                       |

Only materials with `*Reducible strength` are reduced. The recommended setup is [Mohr-Coulomb-2](../material/mechanical/mohr_coulomb.md#mohr-coulomb-2), which uses its elasto-plastic Jacobian in reduction steps by default, with the line search [`*Accelerator, type=linear, default`](../accelerator.md) and the default controls and maximum number of iterations (`maxiter=100`) of the reduction step:

```numgeo
*Step, name=reduction, inc=1000
*Reduction
1.0, 0.01, 0.05, 0.0001
*Accelerator, type=linear, default
...
*End step
```

Once the increment $\Delta \text{FoS}$ falls below $\Delta \text{FoS}_\text{min}$, the analysis is terminated; the factor of safety is the factor of the last converged increment. The step writes the factor of safety, the largest displacement and the energy of every converged increment to `<step name>-strength-reduction-history.csv`; its last line is the increment at which the step stopped, which did not converge. Details are provided in the [Theory Manual](../../theory/solution-method/strength-reduction.md).

Note that time intervals $\Delta t$ are set to 1 and the total time is automatically set equal to the maximum number of increments specified in the step definition. This should be considered when using amplitude definitions such as loading or unloading ramps.
