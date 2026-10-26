# Specific heat

```numgeo
*Material, ...
*Specific heat
<specific heat>
```

This keyword defines the constant specific heat at fixed strain $c_\epsilon$ of [u-T solid elements](../element/elements-ut.md). It is required for every u-T element and must be specified once within its material definition.

- `<specific heat>`: specific heat at fixed strain $c_\epsilon$ (J/(kg K) in SI units). The value must be finite and strictly positive.

Together with the solid [density](density.md) $\rho$, this parameter gives the heat capacity per unit volume $\rho c_\epsilon$. Density must also be finite and strictly positive.

For example:

```numgeo
*Specific heat
460
```

The specified value is the fixed-strain specific heat. A tabulated constant-pressure heat capacity is not automatically the same quantity. With [Thermal elasticity](mechanical/thermal_elasticity.md), reversible deformation contributes additional heat storage; see the [coupled equations](../../theory/elements/thermoelastic-solids.md#balance-equations-and-thermodynamics). Temperature-dependent specific-heat tables are not supported.

The choice of consistent or lumped discretisation of the capacity is made separately with [`*Thermal capacity`](thermal-capacity.md).
