#Brooks & Corey model

The input line for the Brooks & Corey - Mualem[@mualem1976] model takes the following form:
		
	*Relative permeability = Brooks_Corey 
	k^w_min, k^a_min, lambda

The material parameters are given in the following:

* $k^{w}_{min}$ and $k^{w}_{min}$ are the minimum relative permeability for the pore water and pore air phase, respectively.
* $\lambda$ is the pore-size distribution index; see the [hydraulic model](../hydraulic/brooks-corey.md). This dimensionless exponent reflects the uniformity of the pore sizes. A smaller $\lambda$ value corresponds to a wider range of pore sizes, while a larger value indicates a more uniform pore structure.

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/rel-permeability-models/brooks-corey.md)

</div>

