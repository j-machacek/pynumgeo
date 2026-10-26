# FPL stabilisation:

```numgeo 
*Material, ...
*FPL-stabilisation
alpha_fpl
``` 

Use this command to control the stabilisation parameter $\alpha$ in the stabilized u-p elements for [saturated soils](../element/elements-up-sat.md#stabilized-first-order-elements) and [partially saturated soils](../element/elements-up.md#stabilized-equal-order-elements).

For these elements the conversation of mass for the free water is enhanced by adding a stabilisation term $f^{wf,\text{stab}}_K$. The stabilisation term used in numgeo is a modified version of the Fluid-Pressure-Laplacian (FPL) stabilisation [@Brezzi1984]:

$f^{wf,\text{stab}}_K = \int_\mathfrak{B}  \dfrac{\partial N_I^p}{\partial x_i}  \kappa^{FPL}    \dfrac{\partial N_I^p}{\partial x_i}  \dot{p}^{wf}_K \mbox{d} v,$

wherein $\kappa^{FPL}$ is the stabilisation factor and is implemented in numgeo based on the FPL for unsaturated materials [@truty2006]:

$$
\kappa^{FPL} = \alpha^{FPL} \left(\dfrac{\left(S^w l_e\right)^2}{4 M} + \dfrac{l_e^2 c}{6} - \dfrac{\Delta t k}{\rho^w g}\right).
$$

**Therein are:**

- $S^w$ the degree of saturation, 

- $\Delta t$ the time increment, 

- $l_e$ the characteristic element length (approximated as the longest distance of any two nodes of a finite element),

- $M$ the constrained modulus of the material (approximated from the current material tangent stiffness $\frac{\partial \sigma_{ij}}{\partial \varepsilon_{kl}}$ assuming incremental linear elasticity),

- $c$ the storage capacity assuming incompressibility of the solid particles: $c=\frac{\varphi^{wf}}{\bar{K}^{wf}} + \frac{\partial \varphi^w}{\partial \bar{p}^{w}}$ and

- $k$ the representative hydraulic conductivity [@truty2001] $k = \frac{p^w_{,i}}{\parallel p^w_{,i}\parallel} \frac{k^{wf} K_{ij}^{ref}}{\mu^{wf}} \frac{p^w_{,j}}{\parallel p^w_{,j}\parallel}.$

- $\alpha^{FPL}$ controls the amount of numerical diffusion and is typically in the range of $0 \leq \alpha^{FPL} \leq 1$. If the keyword `*FPL-stabilisation` is not defined, a default value of $\alpha^{FPL}=0.5$ is used.

---

## References
