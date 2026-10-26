# Van Genuchten model

The van Genuchten model (1980)[@vangenuchten1980] is a widely-used mathematical model for the Soil-Water Retention Curve (SWRC). It describes the relationship between the degree of saturation $S^w$ and capillary pressure $p^c$ in a porous medium. The numgeo keyword reads:

```numgeo
*Hydraulic = van Genuchten [, Swr = ]
alpha, n
```

The material parameters of the van Genuchten model are given in the following.  

* $\alpha$ is an empirical parameter with units of inverse pressure (e.g., kPa$^{-1}$).
* $n > 1$ is an empirical parameter related to the pore-size distribution (dimensionless).
* $S^{wr}$ (optional) is the residual degree of saturation (-).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/van-genuchten.md)

</div>

		
