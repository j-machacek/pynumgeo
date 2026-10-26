# Mass points

```numgeo 
*Mass point, <amplitude type>
<node set name>, <degree of freedom>, <value>
```

With this option, a mass for dynamic analysis can be imposed for the
specified nodes. The entries of the `<subsequent lines>` are the name of
the node set `<node set name>`, the `<degree of freedom>` and the
assigned value of mass. The mass point definition has to be defined
within the step it is supposed to act. In any analysis type not taking
into account inertia, the contribution of the mass point to the system
of equation is zero. The `<amplitude type>` is mandatory.

The mass has to be in the unit conforming with the model definition. It is defined as density times volume. 