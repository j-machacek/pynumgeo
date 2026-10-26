# Initial conditions
```numgeo 
*Initial conditions, Type=<ic type>, default
<...>
```
This option is used to define initial conditions, e.g. initial stresses.
Initial conditions are specified for particular nodes or elements, as
appropriate. The data can be provided directly or by a user subroutine.
The parameter `Type` is mandatory. Additional options, such as `default` or `user`, depend on the selected initial condition and are described in the corresponding section.

Use the `Type = <ic type>` keyword to specify for
which field the initial condition is to be applied (depending on the
analysis to be performed). The following
`<field>`s are currently available:

|**Variable**                |                                       **Section**
|----------------------------| ---------------------------------------------------------------------------------------
|Void ratio (element level)  |  [Initial conditions, Type=void ratio](./void-ratio.md)
|Stress                      |     [Initial conditions, Type=stress](./stress.md)
|Temperature (nodes; required for u-T solids) | [Initial conditions, Type=temperature](./temperature.md)
|Pore water/air pressure     |      [Initial conditions, Type=pore water/air pressure](./pore-pressure.md)
|Velocity (nodes)            | [Initial conditions, Type=velocity](./velocity-acceleration.md)
|Acceleration (nodes)        | [Initial conditions, Type=acceleration](./velocity-acceleration.md)
|State variables             |        [Initial conditions, Type=state variables](./state-variables.md)
|Contact                     |        [Initial conditions, Type=contact](./contact.md)
