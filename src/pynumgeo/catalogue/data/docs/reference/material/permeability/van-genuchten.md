#Van Genuchten - Mualem model

The input line for the van Genuchten-Mualem model takes the following form:
		
	*Relative permeability = van Genuchten 
	k^w_min, k^a_min,  n
		
The material parameters are given in the following:

* $k^{\beta}_{min}$ is the minimum relative permeability of pore water ($\beta = w$) and pore air ($\beta = a$), respectively.
* $n$ is the van Genuchten parameter, see the [hydraulic model](../hydraulic/van-genuchten.md).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/rel-permeability-models/van-genuchten.md)

</div>

