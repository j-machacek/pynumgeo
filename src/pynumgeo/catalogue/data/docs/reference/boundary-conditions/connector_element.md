# Spring-damper element

```numgeo 
*Connector element
<node set name 1>, <node set name 2>, <degree of freedom>, <stiffness> [, <viscous damping coefficient>]
```

With this option, a connector element between two node sets is generated (i.e. a spring-damper element). The entries of the `<subsequent lines>` are the name of the first node set `<node set name 1>`, the name of the second node set `<node set name 2>`, the `<degree of freedom>` (${u_1,u_2,u_3}$), the assigned stiffness of the connector element [F/A] and, potentially, a  viscous damping coefficient  [F*t/A] (unit of force times time divided by area). If only a dashpot element is to be considered, a stiffness of zero can be specified to deactivate the force resulting from the spring. 

The difference between the `*Equation` command and the `*Connector element` definition is the possibility to define a specific stiffness (or damping) and obtain the connector force using the output variable `CON_F` (see [*Output](../output/index.md)). The connector force is the sum of the forces resulting from the spring and the damper.

Only linear spring $F^{spring} = stiffness \cdot (\boldsymbol{u}_1 - \boldsymbol{u}_2$) and linear dampers are supported $F^{damper} = damping coefficient \cdot (\boldsymbol{v}_1 - \boldsymbol{v}_2$). $\boldsymbol{u}_1$, $\boldsymbol{u}_2$ are the displacements of the nodes between which the connector element is added and $\boldsymbol{v}_1$, $\boldsymbol{v}_2$ are their velocities. 

!!! warning ""

      The output variable `CON_F` is currently a scalar. If for one node two connector elements are defined, both are considered in the analysis but only the force of the second connector element is printed as output. 
