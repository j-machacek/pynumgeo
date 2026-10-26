```numgeo 
*Dynamic
<Delta t_0>, <t_step>, <Delta t_min>, <Delta t_max>
<Time integration procedure>
```
This procedure is used to calculate the response of a structure subject
to dynamic loading using a direct integration procedure of the equations
of motion. Both following lines are mandatory. In a dynamic step, loads
are by default applied by their full magnitude at the start of the step.
Other loading patterns can be prescribed by using previously defined
amplitudes.

-   The first line specifies the time incrementation. Therein $\Delta t_0$ is the
    size of the initial time increment, $t_{step}$ is the overall step time, $\Delta t_{min}$ is the
    minimum allowed time increment and $\Delta t_{max}$ is the maximum allowed time
    increment.


-   `<Time integration procedure>`
  - Use this parameter to choose the time integration method. Note the
    asterisk starting the keyword.

    -   If `*Hilber-Hughes-Taylor` is chosen, the line may be extended by up to three parameters
        (=<$\alpha$>,<$\beta$>,<$\gamma$>), defining the Hilber-Hughes-Taylor parameters. The smaller
        the value of the parameter $\alpha$, the greater the numerical
        dissipation (note that $\alpha \leq 0$ holds). The following
        options are available:

        -   Only the parameter $\alpha$ is given by the user. $\beta$ and
            $\gamma$ are calculated using the following relations
            $\beta=(1-\alpha)^2/4$ and $\gamma=1/2 - \alpha$. For
            $\alpha = 0$ the average-acceleration Newmark method is recovered.
            The standard HHT relations give second-order accuracy for linear
            problems with consistent initial data.
            The [HHT parameter study](../../tutorial/dynamics/bouncing-ball.md#8-vary-the-hht-alpha-parameter)
            compares $\alpha=0$, $-0.05$ and $-0.1$ with backward Euler,
            including the initialization of the force history and the effect of halving the time increment.

        -   All three parameters are given in the following order: $\alpha, \beta, \gamma$.
            Note that depending on the user's entries for $\beta$ and
            $\gamma$ the aforementioned relations may be disrespected.

    -   If `*Backward Euler` is chosen, no further information is required. The parameters
        of the Hilber-Hughes-Taylor time integration scheme are set to
        $\alpha=0$, $\beta=1.0$ and $\gamma=1.0$. The solution update uses
        backward differences, $v_{n+1}=(u_{n+1}-u_n)/\Delta t$ and
        $a_{n+1}=(v_{n+1}-v_n)/\Delta t$. This implicit method is first-order
        accurate and introduces numerical damping, especially at high frequencies.
        The [bouncing-ball comparison](../../tutorial/dynamics/bouncing-ball.md#7-compare-hht-0-with-backward-euler)
        shows its influence on contact force and rebound.

## Initial velocity and acceleration

Initial translational velocities and accelerations can be specified on global node sets before the first step:

```numgeo
*Initial conditions, type=velocity
BALL, U2, -0.5
*Initial conditions, type=acceleration
BALL, U2, -9.81
```

The fields are applied once at the first regular implicit dynamic step. Subsequent steps and restarts continue the computed state. An initial acceleration does not apply a load: define gravity or other forces in the step as well. The initial acceleration must be consistent with the initial forces; numgeo does not solve for it automatically.

See [Initial velocity and acceleration](../initial-conditions/velocity-acceleration.md) for supported procedures, input checks and the HHT initial-force limitation, and [Bouncing ball: initial velocity](../../tutorial/dynamics/bouncing-ball.md) for a complete example with gravity, contact and rebound.
