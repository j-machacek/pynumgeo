# Beam Properties

!!! note "Release information"
    Beam elements were introduced in the [November 2025 release](../../release/release_notes_2025_11.md).

## Syntax

```numgeo 
*Beam properties
A, E, G, Iyy, Izz, J, kappaY, kappaZ
``` 

## Description

This keyword defines the mechanical and geometric properties of [Timoshenko beam elements](../element/elements-beam.md). The beam properties are specified on a single line with eight parameters.

## Parameters

| Parameter | Description | Units | Notes |
|-----------|-------------|-------|-------|
| `A` | Cross-sectional area | L² (e.g., m²) | Assumed constant during simulation |
| `E` | Young's modulus | F/L² (e.g., kPa) | Elastic axial and bending stiffness |
| `G` | Shear modulus | F/L² (e.g., kPa) | Typically G = E/[2(1+ν)] where ν is Poisson's ratio |
| `Iyy` | Second moment of area around local y-axis | L$^4$ (e.g., m$^4$) | Bending about local y-axis |
| `Izz` | Second moment of area around local z-axis | L$^4$ (e.g., m$^4$) | Bending about local z-axis |
| `J` | Torsional constant | L$^4$ (e.g., m$^4$) | Also known as polar moment of inertia |
| `kappaY` | Shear correction factor in local y-direction | Dimensionless | Accounts for non-uniform shear stress distribution |
| `kappaZ` | Shear correction factor in local z-direction | Dimensionless | Accounts for non-uniform shear stress distribution |

For 2D simulations, typically only `Izz` (bending about the out-of-plane axis) and `kappaZ` are relevant.

## Shear Correction Factors

The shear correction factors depend on the cross-sectional shape and account for the non-uniform distribution of shear stresses. Recommended values are provided below:

| Cross-Section Type | Configuration | Shear Correction Factor (κ) | Notes |
|-------------------|---------------|----------------------------|-------|
| **Rectangular** | Homogeneous | 0.8333 (5/6) | Standard value derived from elasticity theory |
| **I-Sections & IPE Profiles** | Strong-axis bending (⊥ to web) | 0.3-0.4 | Lower values for deeper sections |
| | Weak-axis bending (∥ to web) | 0.5-0.6 | Depends on flange width/thickness ratio |
| **Circular** | Solid | 0.9 | Highest κ among common sections |
| | Thin-walled tube | 0.5-0.6 | Decreases as wall thickness decreases |
| **Box Sections** | Square hollow (thin walls) | 0.4-0.5 | Higher values for thicker walls |
| | Rectangular hollow | 0.35-0.5 | Varies with aspect ratio |
| **Channel Sections** | C-shaped (strong-axis) | 0.35-0.45 | Depends on web/flange proportions |
| | U-shaped (weak-axis) | 0.45-0.55 | Higher for more compact sections |
| **T-Sections** | All orientations | 0.3-0.4 | Similar to asymmetric I-sections |
| **Angle Sections** | L-shaped | 0.45-0.55 | Varies with leg length ratio |

## Examples

### Simple Rectangular Beam (2D)

For a rectangular beam with width 0.2 m and height 0.4 m made of concrete (E = 30 GPa, ν = 0.2):

```numgeo
*Beam properties
0.08, 3.0e7, 1.25e7, 0.00107, 0.00107, 0.00167, 0.8333, 0.8333
```

Where:

- A = 0.2 m × 0.4 m = 0.08 m²
- E = 30 GPa = 3.0e7 kPa
- G = E/[2(1+ν)] = 30/(2×1.2) = 12.5 GPa = 1.25e7 kPa
- Iyy = Izz = bh³/12 = 0.2×0.4³/12 = 0.00107 m$^4$ (assuming same bending capacity in both directions)
- J = Iyy + Izz = 0.00167 m$^4$ (for rectangular section, approximate)
- kappaY = kappaZ = 5/6 = 0.8333 (rectangular section)

### IPE 200 Steel Beam (3D)

For an IPE 200 steel section (E = 210 GPa, ν = 0.3):

```numgeo
*Beam properties
0.00285, 2.1e8, 8.08e7, 1.94e-5, 1.42e-6, 7.02e-8, 0.4, 0.55
```

Where:

- A = 0.00285 m² (from section tables)
- E = 210 GPa = 2.1e8 kPa
- G = E/[2(1+ν)] = 210/[2(1+0.3)] = 80.8 GPa = 8.08e7 kPa
- Iyy = 1.94e-5 m⁴ (weak axis, from section tables)
- Izz = 1.42e-6 m⁴ (strong axis, from section tables)
- J = 7.02e-8 m⁴ (from section tables)
- kappaY = 0.4 (strong axis of I-section)
- kappaZ = 0.55 (weak axis of I-section)

## Notes

- The local coordinate system of the beam determines the orientation of the cross-section.
- For non-standard cross-sections, refer to the [Theory Manual](../../theory/elements/beam.md) for guidance on calculating appropriate parameters.
- The beam formulation assumes linear elastic behavior.

## See Also

- [Beam Elements](../element/elements-beam.md)
- [Theory Manual: Timoshenko Beams](../../theory/elements/beam.md)
- [Output of Beam Forces and Moments](../../reference/output/index.md)
