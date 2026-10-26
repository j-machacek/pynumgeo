# Phantom elasticity:

```numgeo 
*Material, ...
*Phantom elasticity
E, nu
``` 

This parameter is used to overlay the mechanical model with an
additional linear elastic constitutive model. This can improve the
numerical stability when using advanced constitutive models (e.g.
hypoplasticity with intergranular strain) in regions of vanishing mean
effective stress, but can be applied to all constitutive (mechanical)
models of the `numgeo` library. This is especially true if these models
are used in conjunction with "no separation" contact conditions. The
`*Phantom elasticity` keyword takes the following
parameter:

-   $E$: Young's modulus in F/A, e.g. kPa

-   $\nu$: Poissons ratio

The (elastic) stresses from this phantom elasticity can be requested for
output using the following keyword `PHANTOM-ELASTICITY`. In Paraview
these stresses are labeled `Stress-El 11`, \...