#Logistic fit


The input line for the Logistic fit model takes the following form:

    *Relative permeability = Logistic-fit
	k^w_min, k^a_min, chi, zeta


The material parameters are given in the following:

* $k^{\beta}_{min}$ is the minimum relative permeability of pore water ($\beta = w$) and pore air ($\beta = a$), respectively.
* $\chi$ and $\zeta$ are curve fitting parameters.

The logistic function does not reach 1 at full saturation: $k^w(S_e = 1) = k^w_{min} + (1-k^w_{min})/(1+\exp(-\chi(1-\zeta)))$, e.g. 0.9975 for $\chi = 20$, $\zeta = 0.7$ and 0.9933 for $\chi = 10$, $\zeta = 0.5$. The saturated zone therefore flows with a slightly reduced conductivity; choose $\chi(1-\zeta)$ large enough if this matters.

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/rel-permeability-models/logistic-fit.md)

</div>
