# Fredlund & Xing model		

The model proposed by Fredlund and Xing (1994) [@Fredlund1994a] and revised in Fredlund and Xing (2012)  [@fredlund2012] provides a continuous mathematical relationship for the soil-water retention curve over the entire capillary pressure range, from zero to an oven-dry state (typically $10^6$ kPa). A key advantage of this model is that it avoids the slope discontinuity present in models like Brooks & Corey, making it more robust for numerical applications. The numgeo keyword reads:

```numgeo
*Hydraulic = Fredlund-Xing 
h_r, a_f, n_f, m_f
```

The material parameters of the Fredlund & Xing model are given in the following.  

* $a_f$ (kPa): A fitting parameter that is related to the air-entry value (AEV) of the soil. It generally corresponds to the capillary pressure at the inflection point of the SWRC.
* $n_f$ (-): A dimensionless parameter that controls the slope of the SWRC at the inflection point. It is related to the uniformity of the pore-size distribution.
* $m_f$ (-): A dimensionless parameter that controls the curvature at high capillary pressures and is related to the residual water content.
* $h_r$ (kPa): A fitting parameter corresponding to the capillary pressure at which the residual water content is reached. It is used in the correction function to ensure the curve reaches zero saturation at high capillary pressure.


Note that the model accounts for residual saturation through its fitting parameters, primarily $m_f$, and thus does not require a separate residual degree of saturation $S^{wr}$ as an input.

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/fredlund-xing.md)

</div>