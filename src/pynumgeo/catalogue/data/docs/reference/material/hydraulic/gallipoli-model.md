# Gallipoli Model

The Gallipoli model[@gallipoli2003a] is an extension of the van Genuchten model[@vangenuchten1980] to account for the influence of the void ratio on the Soil-Water Retention Curve (SWRC). The numgeo keyword reads:

```numgeo
*Hydraulic = Gallipoli [, Swr = ]
phi, psi, n, m
```

The material parameters of the Gallipoli model are given in the following.  

* $\phi$ is an empirical parameter with units of inverse pressure (e.g., kPa$^{-1}$).
* $\psi$ and $m$ are soil constants (dimensionless). $m$ is often related to $n$ via $m=1-1/n$.
* $n > 1$ is an empirical parameter related to the pore-size distribution (dimensionless).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/gallipoli-model.md)

</div>

		
