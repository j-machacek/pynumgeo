# Thermal capacity

```numgeo
*Material, ...
*Thermal capacity
<capacity type>
```

This optional keyword selects the discretisation of the temperature capacity matrix of [u-T solid elements](../element/elements-ut.md).

- `<capacity type>`:
    - `consistent` (default): use the consistent capacity matrix.
    - `lumped`: use positive row-sum lumping of the linear temperature capacity.

For example:

```numgeo
*Thermal capacity
lumped
```

Both options use the physical [density](density.md) and [specific heat](specific-heat.md) of the material. This setting does not change the [conductivity](thermal-conductivity.md) or select the [stabilisation factor](thermal-stabilisation.md). The projection matrix is formed from the consistent temperature interpolation even when the physical capacity is lumped.
