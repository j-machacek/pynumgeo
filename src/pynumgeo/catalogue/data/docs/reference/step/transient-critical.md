```numgeo 
*Transient-critial
<Delta t_0>, <t_step>, <f_t_min>, <Delta t_max>
```
This procedure is used to consider a meaningful minimum time increment based on the critical time increment $\Delta t_{\text{crit}}$ for unsaturated flow and consolidation analysis within the time-stepping of a transient analysis. A typical case is an infiltration of an initially dry or partially saturated material, where a wetting front with non-constant wetting liquid velocity propagates through the model, or a consolidation analysis, where saturated flow takes place. A critical time increment must not be undercut, to avoid spurious, non-physical oscillations in the pore water pressure evolution, which may lead to convergence difficulties, especially when hydro-mechanically coupled material behaviour is considered. More details on the computation of $\Delta t_{\text{crit}}$ within the analysis are provided in the [Theory Manual](../../theory/solution-method/critical-time-step.md). Analogously to the normal transient procedure, the unsaturated transient procedure also takes place in physical time. Note that inertia effects are not accounted for.

The first line specifies the time incrementation. Therein $\Delta t_0$ is the size of the initial time increment, $t_{step}$ is the overall step time, $f_{t_{\min}}$ is the minimum factor, which scales the critical time increment, and $\Delta t_{\max}$ is the maximum allowed time increment. The minimum time increment in each each step is computed as:

$$
\Delta t_{\min} = f_{t_{\min}}  \Delta t_{\text{crit}}.
$$

Note that $\Delta t_{\text{crit}}$ is not constant, but evolves within the coupled transient analysis. If the critical time increment is never to be undershot, $f_{t_{\min}} \geq 1$ must be specified. Between the limits of $\Delta t_{\min}$ (computed) and $\Delta t_{\max}$ (user specified), the convergence-based [automatic time stepping](../../theory/solution-method/automatic-time-stepping.md) applies.  However, $\Delta t_{\max}$ is not a hard upper limit at all times. If the critical time increment is smaller than the defined maximum time increment, the latter acts as an upper ceiling to prevent uncontrolled increase of the time increment (similar to as in normal transient analysis). However, if the critical time increment exceeds this ceiling, the latter ignored and the time step is increased according to the critical value.







