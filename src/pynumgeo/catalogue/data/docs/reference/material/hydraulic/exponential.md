# Exponential model

This model provides a simple, single-parameter exponential function to describe the soil-water retention curve, as presented in a study by Abed and Sołowski (2017)[@Abed2017]. Its simplicity is advantageous when detailed experimental data is unavailable or for preliminary analyses. The numgeo keyword reads:

```numgeo
*Hydraulic = Exponential [, Swr = ]
zeta
```

The material parameters of the van Genuchten model are given in the following.  

* $\zeta$ is a fitting parameter with units of inverse pressure (e.g., kPa$^{-1}$) that controls the rate of desaturation. A higher value of $\zeta$ results in a steeper drop in saturation as suction increases.
* $S^{wr}$ (optional) is the residual degree of saturation (-).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/exponential.md)

</div>
