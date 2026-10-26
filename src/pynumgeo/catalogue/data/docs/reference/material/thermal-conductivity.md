# Thermal conductivity

```numgeo
*Material, ...
*Thermal conductivity
<thermal conductivity>
```

This keyword defines the constant isotropic thermal conductivity $k$ of [u-T solid elements](../element/elements-ut.md). It is required for every u-T element and must be specified once within its material definition.

- `<thermal conductivity>`: thermal conductivity $k$ (W/(m K) in SI units). The value must be finite and nonnegative. A [static](../step/static.md) heat-conduction analysis requires $k>0$.

The conductive heat flux is

$$\boldsymbol q=-k\nabla T.$$

For example:

```numgeo
*Thermal conductivity
45
```

The conductivity does not define thermal expansion. Select the stress-strain law with [`*Mechanical`](mechanical/index.md), and define [density](density.md) and [specific heat](specific-heat.md) separately. Temperature-dependent conductivity tables are not supported.
