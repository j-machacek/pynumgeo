# Initial conditions, Type=velocity / acceleration

```numgeo
*Initial conditions, Type=velocity [, default]
<node set name>, <u1 | u2 | u3>, <initial velocity>
...
*Initial conditions, Type=acceleration [, default]
<node set name>, <u1 | u2 | u3>, <initial acceleration>
...
```

These keywords define the initial time derivatives of translational degrees of freedom for a regular implicit [`*Dynamic`](../step/dynamic.md) analysis. Either field may be supplied independently. Only the `default` option is available; it may be omitted. Place the definitions before the analysis steps, after the referenced global node sets have been defined.

* `<node set name>`: name of a previously defined global node set. The value is assigned to every node of the set.
* `<u1 | u2 | u3>`: translational degree of freedom whose initial derivative is assigned. The selected degree of freedom must exist at every node in the set. Rotational and other degrees of freedom are not supported.
* `<initial velocity>` or `<initial acceleration>`: finite, signed value in the units of the model (m/s or m/s² in SI units).

Specify each keyword at most once and list all required sets and components below it. A node/component can only be assigned once per field, including through overlapping node sets. Nonzero initial values on prescribed degrees of freedom are rejected; zero values are permitted. Unspecified components retain their existing values, which are zero at a fresh start.

For a body whose node set is `BALL`, with positive $y$ upwards:

```numgeo
*Initial conditions, Type=velocity
BALL, u2, -0.5
*Initial conditions, Type=acceleration
BALL, u2, -9.81
```

This gives the whole body a downward initial velocity of 0.5 m/s and a downward initial acceleration of 9.81 m/s². These are starting values; subsequent velocities and accelerations follow from the solution. Loads such as gravity still need to be defined in the step.

---

## Application and supported procedures

The fields initialize the current and committed velocity and acceleration once, at the beginning of the first regular implicit dynamic step. Static preparation steps may precede it. Later dynamic steps continue the computed state, and restart values take precedence over these input fields.

HHT/Newmark and backward Euler time integration are supported. The fields are not supported with explicit integration, IMEX or the special `*Dynamic, INITIAL` procedure; attempting to initialize them in these procedures produces an error.

---

## Consistent initial acceleration

numgeo does not automatically solve an initial mass-matrix equilibrium problem. Supply an initial acceleration consistent with the initial stresses, loads, contact, damping and constraints when the zero initial value is inappropriate. For a stress-free body in free flight under constant gravity, the initial acceleration equals gravity. An acceleration field does not apply the corresponding body force or prescribe the acceleration for the rest of the step.

For a fresh HHT analysis with nonzero loads at $t=0$, use $\alpha=0$ initially: the current implementation does not assemble the initial force history needed by a nonzero HHT $\alpha$. For the stress-free ball starting in free flight under gravity, the [HHT parameter study](../../tutorial/dynamics/bouncing-ball.md#8-vary-the-hht-alpha-parameter) uses one HHT = 0 increment to establish this history before continuing with $\alpha=-0.05$ or $-0.1$. The initial fields are applied once; the second step continues the motion. The tutorial [Bouncing ball: initial velocity](../../tutorial/dynamics/bouncing-ball.md) demonstrates this setup, including the load, contact, analytical free-flight check and rebound.
