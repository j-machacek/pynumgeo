# Hypoplasticity Clay

Hypoplastic constitutive model for clays proposed by Masin (2005)[@masin2005]. The numgeo keyword reads:

```numgeo 
*Mechanical = Hypoplasticity-Clay
varphi_c [grad], p_T (F/A), lambda*(-), kappa (-), N (-), nu (-), alpha (-), K (-)
A_g (-), s_f (-), R (-), beta_r (-), chi (-), G_0 (-), n_g (-), m_rat (-), K^w (F/A), vert. direction
(-), alpha_e (-), alpha_nu (-)
```

!!! Info
    The Hypoplasticity Clay model was developed and originally implemented by David Masin. For allowing us to incorporate the model in numgeo, we sincerely thank him.