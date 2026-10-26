# Thermal elasticity

Small-strain isotropic linear thermoelasticity uses the same elastic constants and engineering-shear convention as [Linear elasticity](linear_elasticity.md). Select the model explicitly:

```numgeo
*Mechanical = Thermal_Elasticity
E, nu, alpha, T_ref
```

| Parameter | Meaning | SI units | Admissible values |
|---|---|---|---|
| $E$ | Young's modulus | Pa | finite, $E>0$ |
| $\nu$ | Poisson's ratio | — | finite, $-1<\nu<0.5$ |
| $\alpha$ | Linear thermal expansion coefficient | 1/K | finite; zero and negative values are allowed |
| $T_{\rm ref}$ | Stress-free reference temperature | K | finite, strictly positive |

For a stress-free reference configuration,

$$\boldsymbol\sigma=\mathbb C:\bigl[\boldsymbol\epsilon-\alpha(T-T_{\rm ref})\boldsymbol I\bigr].$$

All three normal components include thermal strain, including the constrained out-of-plane component in plane strain. Shear components have no isotropic thermal strain. The formulation supports plane-strain and three-dimensional [u-T solids](../../element/elements-ut.md); [density](../density.md), [conductivity](../thermal-conductivity.md) and [specific heat at fixed strain](../specific-heat.md) are defined separately.

Thermal expansion and reference temperature are the third and fourth parameters of this mechanical model. They are not separate material keywords. Use absolute temperatures throughout the input.

## State variables

| Variable | Description | Initial value |
|---|---|---|
| `TEMP_MAT` | Constitutive temperature represented by the material stress (K in SI units) | 0, interpreted as $T_{\rm ref}$ |

The state variable can be requested by name in [element and integration-point output](../../output/field.md#element-output).

## Initial stress and material state

`TEMP_MAT` stores the absolute temperature represented by the committed constitutive stress. Its default initial value of zero represents $T_{\rm ref}$. The first update therefore includes the full difference $T-T_{\rm ref}$. Prescribed initial stress is retained additively, following the ordinary linear-elastic update.

If a prescribed initial stress already corresponds to a known temperature, define that temperature through the existing material-state interface:

```numgeo
*Initial conditions, type=state variables, default
solid, TEMP_MAT, 303.15
*Initial conditions, type=temperature
all, 303.15
```

Here `solid` is an element set and `all` a node set. The material state and nodal initial temperature serve different purposes: the first identifies the thermal history represented by stress, the second initializes the heat equation. Use a finite positive temperature for an explicit material history. In an element without a temperature field, the material update is isothermal.

Request `TEMP_MAT` as element output to inspect the constitutive temperature. Restart retains it with the other material state; thermal restart files from earlier layouts must be regenerated. See [restart](../../restart.md), [field output](../../output/field.md#element-output), and the [coupled theory](../../../theory/elements/thermoelastic-solids.md).
