```numgeo 
*Static
<Delta t_0>, <t_step>, <Delta t_min>, <Delta t_max>
```
This procedure is used to perform a static analysis and is used when
inertia effects can be neglected. A static step can be linear or
nonlinear, but time-dependent material effects (e.g. creep, swelling)
are ignored. However, rate-dependent plasticity and hysteretic behavior
are taken into account.

For [u-T solid elements](../element/elements-ut.md), the static procedure solves mechanical equilibrium and steady Fourier heat conduction. Temperature capacity, reversible strain-rate heating and incremental thermal stabilisation do not contribute. Thermal expansion remains part of the mechanical response when [Thermal elasticity](../material/mechanical/thermal_elasticity.md) is selected.

-   The first line specifies the time incrementation. Therein $\Delta t_0$ is the
    size of the initial time increment, $t_{step}$ is the overall step time, $\Delta t_{min}$ is the
    minimum allowed time increment and $\Delta t_{max}$ is the maximum allowed time
    increment.

Static analysis can also be used to model partially or fully saturated
(steady-state) fluid flow through porous media, but then requires the
use of coupled elements with associated pore fluid flow properties
defined. Steady-state coupled pore pressure/effective stress analysis
assumes that there are no transient effects in the wetting liquid
continuity equation, i.e. the steady-state solution corresponds to
constant wetting liquid velocities and constant volume of wetting liquid
per unit volume in the continuum.

Steady heat conduction requires a positive [conductivity](../material/thermal-conductivity.md) and, in each connected thermal region, a prescribed [temperature](../boundary-conditions/boundary.md#temperature) or a [film condition](../boundary-conditions/dload.md#film-condition) with a positive coefficient throughout the step. Otherwise the temperature is not determined and the system of equations is singular; this is not checked before the analysis.
