# Density

```numgeo 
*Material, ... 
*Density 
<material density 1>, ..., <material density n>
... 
``` 

This keyword is used to prescribe the density of the material(s). The subsequent lines `<material density 1\>, ..., <material density n\>` depend on the number of phases defined for the current material. This parameter is mandatory. Note that:

* For elements of type *Ux* (e.g. *U8*) the density is interpreted as the initial density of the porous solid phase $\rho^s_0$. This density may change over time due to the deformation of the material.
* For elements of type *Ux-solid* (e.g. *U6-solid*) a non-porous solid continuum is assumed (although the void ratio may be calculated) the density remains constant over time.
* For [u-T solid elements](../element/elements-ut.md), prescribe one finite, strictly positive bulk density of the nonporous solid. It is constant and, together with the [specific heat](specific-heat.md), defines the heat capacity per unit volume.
* The number of densities to be prescribed equals the number of active phases and follow always the order: $\rho^s_0$ (solid), $\rho^w_0$ (water), $\rho^a_0$ (air)
