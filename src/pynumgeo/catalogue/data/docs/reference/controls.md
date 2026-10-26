# Controls

```numgeo
*Controls, method, mode
<parameter 1>, ..., <parameter n>
```

The nonlinear convergence controls are evaluated separately for every active physical field. Global convergence controls are no longer supported. Overall convergence is obtained only when all active fields with free equations have converged and any additional contact-iteration requirements are fulfilled.

The convergence evaluation requires residual equilibrium together with a secondary correction or energy criterion. For numerically stagnant fields, residual equilibrium may alternatively be established by a scale-aware absolute residual safeguard. The safeguard is generated internally from machine precision and the current force scale; it is not prescribed through `*Controls`.

Details of the mathematical formulation and acceptance logic are provided in Section [Convergence criteria](../theory/solution-method/convergence-criteria.md) of the [Theory Manual](../theory/index.md).

## Dof-based solution control

```numgeo
*Controls, <degree of freedom name>, mode
epsilon^d, epsilon^e, epsilon^r, epsilon^{Delta d}, epsilon^{Delta e}, r^epsilon
```

This optional keyword modifies or deactivates the convergence controls for an individual physical field. If no modification is given, the default values listed below are used.

### `<degree of freedom name>`

The following user-configurable fields are available:

* `u`: solid displacement in the $x_1$-, $x_2$- and $x_3$-directions;
* `r`: rotations $r_1$, $r_2$, $r_3$ (2D: $r_3$) of the nodes of beam and shell elements (moment equilibrium). Without `*Controls, r` the rotation field uses the tolerances of the displacement field, including a modification by `*Controls, u`. With `*Controls, r, modify` the rotations can be relaxed or tightened independently of the displacements, `*Controls, r, deactivate` switches off the check of the moment equilibrium. The references of the displacement and the rotation field are converted into each other with the mean element size, see [Rotation field](../theory/solution-method/convergence-criteria.md#rotation-field);
* `pw`: pore-water pressure;
* `pa`: pore-air pressure;
* `tt`: absolute temperature $T$ of [u-T solids](element/elements-ut.md), with heat rate as the conjugate residual;
* `w`: water displacement in the $x_1$-, $x_2$- and $x_3$-directions.

The mixed-element fields `J` and `pmean` are activated automatically when required by the selected element formulation and use internal default controls.

### `mode`

Set `mode` to one of the following values:

* `modify`: replace the default tolerances for the selected field. A subsequent parameter line is required;
* `deactivate`: suppress the convergence evaluation for the selected field. No subsequent parameter line is read. Temperature convergence (`tt`) cannot be deactivated.

A field can participate in convergence evaluation only if its degree of freedom exists in the model. A field whose equations are all constrained is automatically excluded from the equilibrium check and is reported with status `2` in `<jobname>.conv.fields`.

### Parameters for `modify`

The parameters are prescribed in the following order:

1. $\epsilon^{d}$: tolerance for the ratio of the largest Newton correction to the largest accumulated solution increment;
2. $\epsilon^{e}$: tolerance for the relative unbalanced energy;
3. $\epsilon^{r}$: tolerance for the relative residual norm;
4. $\epsilon^{\Delta d}$: absolute threshold used to identify a negligible accumulated increment and negligible latest correction;
5. $\epsilon^{\Delta e}$: absolute threshold for negligible unbalanced energy;
6. $r^{\epsilon}$: relaxation factor for nonquadratic convergence. The default is 2.

The negligible-response threshold $\epsilon^{\Delta d}$ does not accept a field by itself. After iteration zero, numerical stagnation is identified only when both the accumulated field increment and the latest Newton correction are not larger than $\epsilon^{\Delta d}$. A stagnant field is accepted only if either a relaxed relative residual criterion or the internal scale-aware absolute residual criterion is also fulfilled.

Residual equilibrium remains mandatory for all normal acceptance routes. Correction and energy criteria cannot establish convergence together when the residual criterion is not fulfilled.

For `tt`, the correction and increment are temperature changes and the residual is a heat rate. The quantity called "unbalanced energy" is a residual-times-temperature-correction diagnostic; it is not thermodynamic energy. Dependent temperature values of mixed elements satisfy separate interpolation constraints, checked with an absolute tolerance of $10^{-8}$ in temperature units. See [Temperature field](../theory/solution-method/convergence-criteria.md#temperature-field).

### Relaxation

The relaxation iteration is

$$
n_{rel}
=
\max\left(
1,
\min\left(
\left\lfloor\frac{n_{max}}{2}\right\rfloor,
12
\right)
\right),
$$

where $n_{max}$ is the maximum number of equilibrium iterations of the current step.

For ordinary nonlinear steps, the correction, residual and energy tolerances are multiplied by $r^{\epsilon}$ from iteration $n_{rel}$ onwards. For `*Reduction` steps, the correction tolerance is multiplied by $r^{\epsilon}$, the residual tolerance is multiplied by 5, and the energy tolerance is not relaxed.

Independently of this late-iteration relaxation, numerical stagnation activates a residual check with $5\epsilon^{r}$. This fixed factor is not changed by the user-defined value of $r^{\epsilon}$.

### Absolute residual safeguard

No absolute force tolerance is entered on the `*Controls` card. If a field has numerically stagnated, **numgeo** calculates a characteristic per-equation force scale from the current and stored force vectors and evaluates the largest residual component against

$$
\epsilon_{mach}^{2/3}F_{char}.
$$

For IEEE double precision and a unit characteristic force scale, the limit is approximately $3.67\cdot10^{-11}$. A fixed absolute tolerance of $10^{-8}$ is therefore not used and would be too permissive at unit force scale.

### Examples

Modify the displacement controls:

```numgeo
*Controls, u, modify
1e-3, 2e-3, 5e-4, 1e-6, 1e-6, 1.5
```

Relax the residual tolerance of the rotations only (e.g. a shell structure whose moment equilibrium converges slowly):

```numgeo
*Controls, r, modify
1e-2, 1e-2, 5e-2, 1e-6, 1e-5
```

Modify the temperature controls:

```numgeo
*Controls, tt, modify
1e-3, 1e-3, 1e-3, 1e-3, 1e-10, 2
```

Deactivate the pore-air-pressure convergence evaluation:

```numgeo
*Controls, pa, deactivate
```

Global controls such as

```numgeo
*Controls, global, modify
```

are obsolete and must not be used. They are still read, but have no effect.

### Default values

| dof | $\epsilon^{d}$ | $\epsilon^{e}$ | $\epsilon^{r}$ | $\epsilon^{\Delta d}$ | $\epsilon^{\Delta e}$ | $r^{\epsilon}$ |
| --- | -------------- | -------------- | -------------- | ---------------------- | ---------------------- | ---------------------- |
| `u`  | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-6}$ | $1\cdot10^{-5}$  | 2 |
| `r`  | as `u` | as `u` | as `u` | as `u` | as `u` | as `u` |
| `w`  | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-5}$ | $1\cdot10^{-5}$  | 2 |
| `pw` | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-3}$ | $1\cdot10^{-10}$ | 2 |
| `pa` | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-3}$ | $1\cdot10^{-10}$ | 2 |
| `tt` | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-2}$ | $1\cdot10^{-3}$ | $1\cdot10^{-10}$ | 2 |

## Failure handling and diagnostics

NaN, infinity and arithmetic overflow in the convergence quantities cause immediate rejection and an enforced cutback. This safeguard also applies when `NOCUTBACK` is active. The `.msg` file identifies the affected quantity and, where available, the global degree of freedom and node.

The `.msg` file reports the active tolerances and the exact acceptance or rejection route for every field. Two machine-readable convergence files are written:

```text
<jobname>.conv
<jobname>.conv.fields
```

The existing `<jobname>.conv` file remains compatible with the convergence viewer and contains

```text
step inc attempt iter rhs_ratio inc_ratio rhs_criterion inc_criterion
```

When the absolute stagnation safeguard is used, equivalent ratios are written so that the viewer remains consistent with the solver decision. The `attempt` column remains equal to 1 because the legacy report interface does not provide the actual attempt number.

The field-resolved `<jobname>.conv.fields` file contains

```text
step inc iter field residual_ratio correction_ratio energy_ratio force_criterion correction_criterion energy_criterion max_abs_residual abs_component_limit status
```

with the status values:

* `1`: accepted;
* `0`: rejected;
* `-1`: non-finite value or arithmetic overflow;
* `2`: no free equations.

## Maximum solution increment

```numgeo
*Controls, max-<dof>, activate
tilde{Delta}_{dof}, s^{max}
```

This optional keyword modifies the time-step control after a successful Newton iteration. If activated, all sub-keywords are mandatory.

See [Maximum solution increment](../theory/solution-method/automatic-time-stepping.md#maximum-solution-increment) for further information.

### `<dof>`

The following solution increment can currently be controlled:

* `dpw`: change in pore-water pressure.

### Parameters

* $\widetilde{\Delta}_{dof}$: target solution increment that should not be exceeded within one increment;
* $s^{max}$: maximum time-scaling factor.

### Example

```numgeo
*Controls, max-dpw, activate
50, 4
```
