# Karlsruhe model

The Karlsruhe model, developed by Fuentes and Triantafyllidis (2013)[@fuentes2013], is an advanced hydro-mechanical constitutive model for unsaturated soils. Its primary features are the ability to simulate **hysteretic** water retention behavior (drying and wetting scanning curves) and to couple the retention properties with the soil's mechanical state through the **void ratio** ($e$).

The numgeo keyword reads:

```numgeo
*Hydraulic = Karlsruhe-Model
alpha^d, n^d, alpha^w, n^w, kappa, n, m^e, S_rd, S_rw
```

The material parameters of the Karlsruhe hydraulic model are given in the following.  
	
* Bounding Curve Parameters:

    * `alpha^d`, `n^d`, `S_rd`: Van Genuchten parameters for the main drying curve.
    * `alpha^w`, `n^w`, `S_rw`: Van Genuchten parameters for the main wetting curve.

* Hydro-Mechanical Coupling Parameter:

    * `m^e`: Exponent controlling the influence of void ratio on the retention curves.

* Hysteresis Parameters:

    * `kappa` ($\kappa_w$ in equations): Controls the slope of the initial reversal from a bounding curve.
    * `n` ($n_w$ in equations): Controls the shape of the scanning curves during interpolation.

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind the implementation](../../../theory/constitutive-models/hydraulic-models/karlsruhe-model.md)

</div>