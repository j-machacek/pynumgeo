# Cavitation:

```numgeo 
*Cavitation, ...
<vapour pressure> [, <bulk modulus of gas>]
``` 

This keyword limits the pore-fluid pressure (relative to atmospheric pressure) to the specified minimum `<vapour pressure>`. Numerically, this is achieved by reducing the bulk modulus if the pore-fluid pressure rate would violate the specified limit. By default, a low value of 10 [F/A] is used. The user can instead specify the `<bulk modulus of gas>` that occupies the fluid once cavitation has occurred.

!!! warning
    This keyword is currently only available for the [u-p-sat elements](../element/elements-up-sat.md)

To illustrate how to use the keyword, an undrained cyclic triaxial test with the [AVISA](./mechanical/avisa.md) model is performed. The input files are available [here](./assets/triax_clay_cavitation.zip). One sinusoidal axial stress cycle is considered.  A cavitational limit of -50 kPa is specified and the default value of the reduced bulk modulus is used. As is visible from the figure, the cavitational limit is fulfilled by the simulation for all but the first increment overshooting the limit value. This is because the limit is explicitly implemented and small time increments are required when approaching the limit. 
<p align="center">
  <img src="./assets/triax_pw_cavitation.png" alt="figure 1" width="60%"/> <br>
  <em> Pore water pressure in a triaxial test using the AVISA model considering a cavitation limit of -50 kPa  </em>
</p>
