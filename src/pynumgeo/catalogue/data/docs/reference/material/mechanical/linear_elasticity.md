# Linear elasticity: 

A simple linear elastic material: a linear relationship between stress and strain is assumed. Note that linear elasticity is valid only for stress states that do not produce yielding. The numgeo keyword reads:

```numgeo 
*Mechanical = Linear_Elasticity  
E (F/A), nu (-)
```

The material parameters of the linear elastic model are given in the following.  

* $E$ (F/A) is the Young's modulus of the material.
* $\nu$ (-) is the Poisson's ratio.