# Bathytropic elasticity:

The **bathytropic elasticity** model is a depth-initialised, isotropic linear-elastic constitutive model. At each integration point, the model derives the shear modulus and Young's modulus from prescribed depth profiles of shear-wave velocity and density. The Young's modulus is stored during the first constitutive evaluation and remains constant afterwards; subsequent deformation therefore does not change the elastic properties.

## Input syntax

```numgeo
*Mechanical = Bathytropic_Elasticity
v_s^0 (m/s), rho^0 (kg/m^3), epsilon_rho (kg/m^3), m (-), nu (-), z^ref (m)
```

### Material parameters

The material parameters for `Bathytropic_Elasticity` are:

| Index | Symbol | Unit | Description |
| :---: | :---: | :---: | :--- |
| 1 | $v_s^0$ | m/s | Reference shear-wave velocity at zero depth. |
| 2 | $\rho^0$ | kg/m³ | Reference density at zero depth, used to derive the elastic stiffness. This parameter does not replace the density assigned with `*Density`. |
| 3 | $\epsilon_\rho$ | kg/m³ | Coefficient controlling the logarithmic increase of the stiffness-calibration density with depth. |
| 4 | $m$ | - | Exponent controlling the increase of shear-wave velocity with depth. |
| 5 | $\nu$ | - | Poisson's ratio. A mechanically admissible isotropic stiffness requires $-1<\nu<0.5$. |
| 6 | $z^{ref}$ | m | Reference elevation at which the depth is zero. |

The depth $d$ is calculated as

$$
d=\max\!\left(z^{ref}-x_v,0\right),
$$

where $x_v$ is the vertical integration-point coordinate. The implementation uses

* `coords(2)` as $x_v$ for two-dimensional stress layouts (`ntens = 4`), and
* `coords(3)` as $x_v$ for three-dimensional stress layouts (`ntens = 6`).

Points above the reference elevation are assigned $d=0$ and therefore receive the surface values $v_s^0$ and $\rho^0$.

The depth profiles are

$$
v_s(d)=v_s^0(1+d)^m
$$

and

$$
\rho(d)=\rho^0+\epsilon_\rho\ln(1+d).
$$

The shear modulus and Young's modulus are then calculated as

$$
G(d)=\frac{\rho(d)v_s(d)^2}{1000}
\qquad\text{and}\qquad
E(d)=2G(d)(1+\nu).
$$

### Unit convention

The current implementation has a fixed SI-based unit convention:

* coordinates and $z^{ref}$ are entered in metres,
* $v_s^0$ is entered in m/s,
* $\rho^0$ and $\epsilon_\rho$ are entered in kg/m³, and
* the resulting $G$ and $E$ are obtained in kPa because the implementation divides $\rho v_s^2$ by 1000.

The expressions `1+d` and $\ln(1+d)$ are implemented using the numerical depth in metres; equivalently, they represent $1+d/(1\,\mathrm{m})$.

!!! warning "Density used for dynamic analyses"

    The profile $\rho(d)$ is used only to derive the elastic stiffness. It does not change the mass density assigned through `*Density`. In a wave-propagation analysis, the prescribed mass density must be consistent with $\rho(d)$ if the numerical shear-wave speed is intended to equal the specified profile $v_s(d)$.

### Example

```numgeo
*Mechanical = Bathytropic_Elasticity
** v_s^0 [m/s], rho^0 [kg/m^3], epsilon_rho [kg/m^3], m [-], nu [-], z^ref [m]
500., 2000., 50., 0.20, 0.25, 0.
```

For this example, the reference elevation is zero. In a two-dimensional model, an integration point at $y=-100$ m has a depth of 100 m. In a three-dimensional model, the same depth is obtained for an integration point with $z=-100$ m.

## Initialisation and state variable

The implementation requires one state variable:

| Index | Internal entry | Unit | Description |
| :---: | :--- | :---: | :--- |
| 1 | `matvar(1)` | kPa | Young's modulus $E$ derived from the depth profile. |

When `matvar(1)` is zero, the model calculates $E$ from the supplied coordinates and stores it in `matvar(1)`. On all later calls, the stored value is reused and coordinate changes no longer affect the stiffness.

If no named state-variable alias is registered for this model, the stored modulus can be requested as `sdv1`.

!!! warning "Meaning of initial depth"

    The supplied implementation evaluates the depth during the first constitutive call at an integration point. Without geometric nonlinearity, numgeo supplies the original coordinates. With geometric nonlinearity, numgeo supplies current coordinates. To guarantee initial-geometry depth, the material must therefore be initialised before the geometry changes. An element that first becomes active later in an analysis is initialised from its coordinates at that later first call.

!!! note "Restart and manual state initialisation"

    A nonzero initial value of `matvar(1)` is interpreted as an already initialised Young's modulus and bypasses the depth calculation. For a restart that must retain the original stiffness field, this state variable has to be preserved or reinitialised consistently.

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/bathytropic-elasticity.md)

</div>
