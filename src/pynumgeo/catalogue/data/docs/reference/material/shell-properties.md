# Shell Properties

## Syntax

```numgeo
*Shell properties
t, E, nu [, kappa [, drill]]
```

## Description

This keyword defines the wall thickness and the elastic constants of [shell elements](../element/elements-shell.md). It is a sub-keyword of `*Material`; the material is assigned to the shell elements with `*Solid section` like any other material. The wall is homogeneous, isotropic and linear elastic.

## Parameters

| Parameter | Description | Units | Notes |
|-----------|-------------|-------|-------|
| `t` | Wall thickness | L (e.g., m) | $t>0$; distributed symmetrically about the surface defined by the nodes |
| `E` | Young's modulus | F/L² (e.g., kPa) | $E>0$ |
| `nu` | Poisson's ratio | -- | $-1<\nu<0.5$ |
| `kappa` | Shear correction factor | -- | optional, default $5/6$ (homogeneous wall) |
| `drill` | Drilling stiffness factor | -- | optional, default $0.1$; the penalty stiffness of the rotation about the shell normal is `drill`$\cdot G\,t$ |

The section stiffnesses which follow from these parameters are the membrane stiffness $Et/(1-\nu^2)$, the bending stiffness $Et^3/(12(1-\nu^2))$ and the transverse shear stiffness $\kappa G t$ with $G=E/(2(1+\nu))$.

A density assigned with `*Density` is used for the mass matrix and for body forces (load per unit area $\rho\,t\,g$), see [Shell elements](../element/elements-shell.md#notes-on-density-and-body-forces). numgeo requires a `*Density` for every material; use `0.0` for a weightless structure.

!!! note "Drilling stiffness"

    Shell nodes carry three rotations, but the shell theory provides no stiffness for the rotation about the normal. The elements tie this *drilling rotation* to the in-plane rotation of the membrane displacement field with the penalty stiffness `drill`$\cdot G\,t$ (see the [Theory Manual](../../theory/elements/shell.md#drilling-rotation)). The results are insensitive to the factor over several orders of magnitude; the default should only be changed for testing.

## Examples

Steel wall of a monopile with a thickness of 60 mm ($E=210$ GPa, $\nu=0.3$), units kN and m, weightless:

```numgeo
*Material, name=steel, phases=1
*Shell properties
0.06, 2.1e8, 0.3
*Density
0.0
*Solid section, elset=pile, material=steel
```

Reinforced concrete slab with a thickness of 0.4 m ($E=30$ GPa, $\nu=0.2$) with self weight ($\rho=2.5$ t/m³):

```numgeo
*Material, name=concrete, phases=1
*Shell properties
0.4, 3.0e7, 0.2
*Density
2.5
```

## Notes

- Only single-phase materials (`phases=1`) can carry shell properties.
- The material of shell elements can be exchanged during the analysis with [`*Model change, material`](../model-change/material.md), e.g. to install a wall after the geostatic step.

## See Also

- [Shell Elements](../element/elements-shell.md)
- [Theory Manual: Shell Elements](../../theory/elements/shell.md)
- [Embedded shells](../embedded-regions/interaction-surface-plate.md)
