```numgeo 
*Reduction [, arc-length] [, <option>=<value>, ...]
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

## Arc-length control

```numgeo
*Reduction, arc-length [, arc-increments=<N>] [, max-displacement=<u>] [, plateau-tolerance=<tol>] [, plateau-increments=<N>] [, perturbation=<eps>]
<FoS_0>, <Delta FoS_0>, <Delta FoS_max>, <Delta FoS_min>
```

With `arc-length` the strength reduction continues into the failure mechanism, as the *Safety* calculation of PLAXIS. As soon as the prescribed increments of the factor of safety no longer converge, the factor of safety becomes an unknown of the equilibrium iteration: every increment prescribes how far the structure moves on, and the iteration determines the factor of safety that is in equilibrium with this state (indirect displacement control). The factor of safety may increase or decrease, and the analysis follows the mechanism to large displacements. The method is described in the [Theory Manual](../../theory/solution-method/strength-reduction.md#arc-length-control).

**Course of the step.**

1. The step starts with prescribed increments, as without `arc-length`.
2. A single rejected increment is repeated with a third of the increment of the factor of safety, as without `arc-length`. At the second consecutive rejected increment (or at the first, if a third of the increment would fall below the minimum increment) for which a secant of the last converged increment exists, the arc-length control takes over and stays active until the end of the step.
3. The step computes `arc-increments` arc-length increments (default 100). It ends earlier only when the largest displacement since the start of the step reaches `max-displacement`, after ten consecutive rejected arc-length increments or at the number of increments `inc` of the `*Step`.
4. If the arc-length control is never engaged (no rejected increment with a usable secant), the step ends as without `arc-length` ($\Delta \text{FoS}$ below $\Delta \text{FoS}_\text{min}$).

The arc-length increments iterate with the Jacobian of the input (for [Mohr-Coulomb-2](../material/mechanical/mohr_coulomb.md#mohr-coulomb-2) the elasto-plastic Jacobian, optional parameter `cep_ratio_reduction`), factorized in every iteration, with the force tolerance of the step and at most 60 iterations per increment (or `maxiter`, if smaller). After an increment with at most 6 iterations the next step length is doubled, after 15 or more halved; it is limited such that the factor of safety changes by at most $\Delta \text{FoS}_\text{max}$ and the largest displacement grows by at most $2^{1/(2N)}$ per increment ($N$ = `plateau-increments`, 7 % for the default). A rejected increment is repeated from the last converged state with half the step length.

**Factor of safety.** After every accepted arc-length increment numgeo checks for a plateau: with the largest displacement $u$ of the increment, the mean factor of safety of the accepted arc-length increments in the window $u/4 < u_i \le u/2$ and that in the window $u/2 < u_i \le u$ differ by no more than `plateau-tolerance` relative to the mean of the upper window; each window holds at least `plateau-increments` increments, and $u$ is at least four times the largest displacement at the switch to the arc-length control.

The plateau does not end the step.

- If the windows at the **end of the step** form a plateau, the factor of safety of the step is their mean, given with its minimum and maximum ("plateau at the end of the step").
- Otherwise, e.g. for a factor of safety that oscillates with the displacement, it is the mean over the windows of the **first plateau** of the step, marked as such. The `.sta` file always gives the first plateau as well.
- If no plateau is found, e.g. for a factor of safety that still rises with the displacement, the factor of safety is the mean over the two windows at the end of the step, marked "no plateau". It then depends on how far the analysis runs; judge it from the curve.

| Option | Meaning | Default |
| --- | --- | --- |
| `arc-length` | arc-length control of the factor of safety | not active |
| `arc-increments=<N>` | number of arc-length increments of the step (accepted increments after the switch) | 100 |
| `max-displacement=<u>` | end of the step when the largest displacement since the start of the step reaches `<u>` (length unit of the model) | not active |
| `plateau-tolerance=<tol>` | plateau: largest difference of the mean factor of safety of the two displacement windows, relative to the mean of the upper window | $2 \cdot 10^{-3}$ |
| `plateau-increments=<N>` | plateau: smallest number of accepted arc-length increments in each displacement window, at least 2; the largest displacement grows by at most $2^{1/(2N)}$ per increment | 5 |
| `perturbation=<eps>` | relative perturbation $\epsilon$ of the factor of safety for the pseudo-load $\partial r/\partial FoS$ | $10^{-3}$ |

The options are read only together with `arc-length`; an unknown option or an invalid value is an error. With arc-length control the data line keeps its meaning with two additions: $\Delta \text{FoS}_\text{max}$ is also the largest change of the factor of safety within one arc-length increment, and $\Delta \text{FoS}_\text{min}$ applies only as long as the arc-length control has not been engaged.

**Results.** The `.sta` file shows the control of every increment in the column `Ctrl` (`F`: factor of safety prescribed, `A`: arc-length control) and a summary at the end of the step: the reason for the end, the switch to the arc-length control, the windows at the end of the step and whether they agree, the mean, minimum and maximum over all arc-length increments, the first plateau of the step, the factor of safety (plateau at the end of the step, first plateau or "no plateau"), the peak of the step (flagged if it exceeds the factor of safety by more than the plateau tolerance), an estimate of the error of the factor of safety of the last accepted increment and the largest constraint error. The history file `<step name>-strength-reduction-history.csv` has the columns `FoS`, `max_disp`, `energy`, `inc` and `control` (`F` or `A`) and lists every accepted increment in the order of the increments; it contains no non-converged increment.

**Restrictions.** The arc-length control needs the direct solver PARDISO or MUMPS without reuse of the factorization (not `iterative`), and it cannot be combined with `*Accelerator, type=anderson` or with `NOCUTBACK` in the `*Step` line; these combinations end with an error message. Embedded interfaces with [`*Embedded region, interaction, ..., reduction`](../embedded-regions/interaction.md#strength-reduction-of-the-interface) enter the pseudo-load with the derivative of their capacity. Contact interactions with [`*Contact options, reduction`](../contacts/contact-options.md) are reduced, but they contribute nothing to the pseudo-load (a note is written to the `.sta` file): the equilibrium states are not affected, but if the reduced friction of a contact governs the mechanism, the arc-length increments are rejected; use prescribed increments or model the interface with elements (e.g. a thin layer).

```numgeo
*Step, name=reduction, inc=1000
*Reduction, arc-length
1.0, 0.01, 0.05, 0.0001
*Accelerator, type=linear, default
...
*End step
```
