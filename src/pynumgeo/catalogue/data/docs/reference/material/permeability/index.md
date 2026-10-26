# Permeability - Relative permeabiliy constitutive model

```numgeo 
*Material, ...
**Relative Permeability = <relative permeability model> 
*<parameter 1>, ... , <parameter n>
...
``` 

This parameter is only needed for porous materials with more than one phase. The available models in numgeo are described in the subsections accessible through the navigation bar on the left. $k^w$ and $k^a$ are the relative permeability with respect to the pore water and pore air, respectively.

Note that all models in numgeo include minimum relative permeabilities $k^\beta_{min}$ for the pore fluids $\beta= \{w,a\}$. The usage often reduces convergence issues and numerical instabilities at nearly dry or nearly saturated states with (often) only small losses in accuracy. 

Available relative permeability models in numgeo are:

**Model** | **Description**
---|---
[Nguyen](./nguyen.md) | Generalised version of the exponential relative permeability model originally proposed by Nguyen et al. (2006)[@nguyen2006]
[Van Genuchten](./van-genuchten.md) | Van Genuchten type relative permeability model according to Dury et al. (1999) [@dury1999]
[Brooks & Corey](./brooks-corey.md) | Modified version of the original formulation of the Brooks & Corey - Mualem[@mualem1976] model according to Dury et al. (1999)[@dury1999]
[Fredlund & Xing](./fredlund-xing.md) | Relative permeability model according to Fredlund & Xing (1994)[@Fredlund1994]
[Logistic (curve) fit](./logistic-fit.md) | Simple logistic fit function


!!! note "Choice of relative permeability model"

    When selecting a constitutive model for relative permeability, it is essential to ensure compatibility with the previously chosen soil-water retention curve (SWRC). In particular, the air entry value (AEV) of the SWRC should coincide with the onset of permeability reduction in the relative permeability function. Inconsistencies between these two models may lead to unrealistic simulation results.