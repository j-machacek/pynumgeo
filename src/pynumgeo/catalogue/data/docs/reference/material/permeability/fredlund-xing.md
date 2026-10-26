#Fredlund & Xing model		


The input line takes the form:
		
	*Relative permeability = Fredlund-Xing 
	k^w_min, k^a_min, h_r, a_f, n_f, m_f, s_i


The material parameters of the Fredlund & Xing model are given in the following.  

* $k^{w}_{min}$ and $k^{w}_{min}$ are the minimum relative permeability for the pore water and pore air phase, respectively.
* $a_f$ (kPa): A fitting parameter that is related to the air-entry value (AEV) of the soil. It generally corresponds to the capillary pressure at the inflection point of the SWRC.
* $n_f$ (-): A dimensionless parameter that controls the slope of the SWRC at the inflection point. It is related to the uniformity of the pore-size distribution.
* $m_f$ (-): A dimensionless parameter that controls the curvature at high capillary pressures and is related to the residual water content.
* $h_r$ (kPa): A fitting parameter corresponding to the capillary pressure at which the residual water content is reached. It is used in the correction function to ensure the curve reaches zero saturation at high capillary pressure.
* $s_i$:  defines the lower integration value for the suction, can be chosen as the air-entry value[@Zhang2015]. Note that this results in $k^{r,wf} = 1.0$ for $S^w \le 1.0$ which might be unfavourable for some applications.


Note that the model features a parameter for residual water content and does not require the definition of a residual degree of saturation $S^{wr}$. An adapted [Nguyen approach](../permeability/nguyen.md) with $m=1.0$ is currently used for the relative permeability of the free air phase.


---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/rel-permeability-models/fredlund-xing.md)

</div>

