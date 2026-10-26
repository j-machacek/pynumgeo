# Thermal stabilisation

```numgeo
*Material, ...
*Thermal stabilisation
<stabilisation factor>
```

This keyword defines the factor $\gamma$ of the incremental temperature-projection term used by the [stabilised equal-order u-T elements](../element/elements-ut.md#equal-order-elements).

- `<stabilisation factor>`: dimensionless factor $\gamma$, finite and nonnegative. It must be specified explicitly for `-STAB` elements; there is no default value.

For example:

```numgeo
*Thermal stabilisation
1.0
```

A value of zero switches the projection term off. Mixed elements and equal-order elements without the `-STAB` suffix do not use this term. The factor is a numerical parameter, separate from the physical [conductivity](thermal-conductivity.md) and [specific heat](specific-heat.md).

The projection preserves a spatially uniform temperature increment and vanishes in steady state. Its formulation and capacity scale $\tau$ are described in the [Theory Manual](../../theory/elements/thermoelastic-solids.md#when-stabilization-is-needed). The scale can be requested as `TSTAB` in [output](../output/field.md#element-output).

The value 1.0 is used in several benchmarks; select the factor together with mesh and time-step refinement for the intended problem. The [strong-coupling benchmark](../../benchmark/thermal/strong-coupling.md) compares different factors. A material may contain only one `*Thermal stabilisation` definition.
