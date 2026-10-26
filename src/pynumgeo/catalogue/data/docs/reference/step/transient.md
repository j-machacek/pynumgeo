```numgeo 
*Transient
<Delta t_0>, <t_step>, <Delta t_min>, <Delta t_max>
```
This procedure is used to perform a transient analysis, i.e. an analysis
in physical time. A typical case is a consolidation analysis with
non-constant wetting liquid velocity. For [u-T solid elements](../element/elements-ut.md), it advances temperature with backward Euler and includes heat storage, conduction and the reversible thermoelastic heating of [Thermal elasticity](../material/mechanical/thermal_elasticity.md). The step time and increments are physical times.

-   The first line specifies the time incrementation. Therein $\Delta t_0$ is the
    size of the initial time increment, $t_{step}$ is the overall step time, $\Delta t_{min}$ is the
    minimum allowed time increment and $\Delta t_{max}$ is the maximum allowed time
    increment.

Note that inertia effects are not accounted for.
