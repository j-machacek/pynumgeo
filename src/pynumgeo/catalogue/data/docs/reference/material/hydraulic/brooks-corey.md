# Brooks & Corey model

The Brooks and Corey (1964)[@brooks1964] model is an empirical relationship for the soil-water retention curve. It is particularly known for its simple power-law formulation and its explicit definition of an air-entry pressure. The relationship is defined as a piecewise function, distinguishing between the behavior below and above this pressure threshold.

```numgeo
*Hydraulic = Brooks-Corey [, Swr = ]
lambda, p^b
```

The material parameters of the Brooks & Corey model are given in the following.  

* $p_b$ is the air-entry pressure. This is the minimum capillary pressure required for air to begin entering the largest pores, marking the onset of desaturation. It is also referred to as the bubbling pressure.
* $\lambda$ is the pore-size distribution index. This dimensionless exponent reflects the uniformity of the pore sizes. A smaller $\lambda$ value corresponds to a wider range of pore sizes, while a larger value indicates a more uniform pore structure.
* $S^{wr}$ (optional) is the residual saturation (-). 


---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/brooks-corey.md)

</div>
