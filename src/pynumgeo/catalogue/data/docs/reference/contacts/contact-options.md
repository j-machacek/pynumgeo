# Contact options

```numgeo
*Contact options, Name=<interaction name>, [clearance=<normal contact distance>], [ Check Disp = <Fraction of contact length>], [ Check Dist = <Fraction of contact length>], [ Reduction]
```

This option defines additional and optional contact interaction definitions. It is not mandatory to use and does not have to be altered in almost all cases.

- The `clearance` option defines an initial normal gap of the contact interaction, which enforces the contacts to remain open (or overlapped) with the defined normal distance. Positive values for `c` indicate an open contact, while negative values indicate overlapping.

    <p align="center">
    <img src="./assets/clearance.png" width=90%/><br>
    </p>

- The `Check Disp` option defines the fraction of the displacement magnitude of the contact nodes at which a update of the node-to-node connectivity is performed. The value defined is the fraction of the characteristic contact length (length of element edge) and is by default 0.05.

- `Check Dist` defines the maximum contact point distance for which contact quantities are still computed based on the fraction of the characteristic contact length. This factor is by default $2.5$. If the user encounters contacts that are not computed (identifiable e.g. by zero contact distance) even if they should have to be, an increase of `Check Dist` can be a possible solution. Likewise, if the user encounters that nodes have contact stress which should not, reducing the value of `Check Dist` (or changing the contact conditions) may help.

- With the `Reduction` keyword interface properties are included in [strength-reduction analyses](../step/reduction.md) for the determination of the Factor of Safety $FoS$. If activated, the friction coefficient, dilatation angle and adhesion are obtained by

    $$
    \tan(\delta) = \dfrac{\tan\delta_0}{FoS} ~~~;~~~ \tan(\psi) = \dfrac{\tan\psi_0}{FoS} ~~~;~~~ c = \dfrac{c_0}{FoS} ~~~ \text{for}~~~ FoS > 0
    $$

    Therein, $\delta_0$, $\psi_0$ and $c_0$ are the interface properties provided at the start of the analysis. This option is deactivated by default and (if activated) will only be considered during steps of type [*Reduction](../step/reduction.md) (strength-reduction analyses).