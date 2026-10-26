# Initial conditions, Type=pore water/air pressure
```numgeo 
*Initial conditions, Type=pore water pressure, default
<node/element set>, <ic parameter 1>, ..., <ic parameter n>`
```
or
```numgeo 
*Initial conditions, Type=pore air pressure, default  
<node/element set>, <ic parameter 1>, ..., <ic parameter n>`
```

Specify the initial values of pore water pressure or pore air pressure
at the nodes of a node set. Use one of the following `options`:

-   `Default`
    Use this option to assign an elevation-dependent initial pore water
    pressures and initial pore air pressures. The vertical direction $h$
    is assumed to be the $z$-direction in 3-D and axisymmetric models
    and the $y$-direction in 2-D models and the distribution of initial
    pore water/air pressure is assumed to vary piecewise linearly with
    this vertical coordinate. The command line takes the following form:

    `*Initial Conditions, Type = pore water/air pressure, default`  
    `<node set name>, `$h_1$`, `$p^{w/a}_0(h_1)$`, `$h_2$`, `$p^{w/a}_0(h_2)$