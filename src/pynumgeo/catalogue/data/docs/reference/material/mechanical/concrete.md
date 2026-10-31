# Concrete

Elastoplastic model for concrete, shotcrete, grout and other cementitious materials after Schädlich & Schweiger (2014)[@schaedlich2014shotcrete], known as the "Concrete model" of PLAXIS[@plaxis2019mm]: linear elasticity, a Mohr-Coulomb yield surface with strain hardening and softening in compression, Rankine yield surfaces with linear strain softening in tension (cracking) and non-associated flow in compression. The softening is regularised with the fracture energies and the equivalent length of the finite element (crack band). numgeo implements the rate-independent part of the model with constant (28-day) parameters; the time dependency of stiffness and strength, creep and shrinkage of the original model are not included. The formulation is described in the [theory manual](../../../theory/constitutive-models/mechanical-models/concrete.md).

---

## Input syntax

```numgeo
*Mechanical = Concrete
E (F/A), nu (-), f_c (F/A), f_t (F/A), phi_max (deg), psi (deg), f_c0n (-)
f_cfn (-), f_cun (-), G_c (F/L), eps_cp^p (-), a (-), f_tun (-), G_t (F/L)
```

### Material parameters

| Index | Symbol | Unit | Description |
| :---: | :---: | :---: | :--- |
| 1 | $E$ | F/A | Young's modulus, $E > 0$ |
| 2 | $\nu$ | - | Poisson's ratio, $0 \le \nu < 0.5$ |
| 3 | $f_c$ | F/A | Uniaxial compressive strength (positive), $f_c > 0$ |
| 4 | $f_t$ | F/A | Uniaxial tensile strength (positive), $0 < f_t < \sigma_{rot} = \tfrac{f_c}{2}\left(\tfrac{1}{\sin\varphi_{max}} - 1\right)$ |
| 5 | $\varphi_{max}$ | deg | Maximum friction angle, $0 < \varphi_{max} < 90°$ |
| 6 | $\psi$ | deg | Dilatancy angle, $0 \le \psi \le \varphi_{max}$ |
| 7 | $f_{c0n}$ | - | Normalised initial yield stress in compression $f_{c0}/f_c$, $0 < f_{c0n} \le 1$ |
| 8 | $f_{cfn}$ | - | Normalised failure strength in compression $f_{cf}/f_c$ (end of the softening controlled by $G_c$), $0 < f_{cfn} \le 1$ |
| 9 | $f_{cun}$ | - | Normalised residual strength in compression $f_{cu}/f_c$, $0 < f_{cun} \le f_{cfn}$ |
| 10 | $G_c$ | F/L | Fracture energy in compression, $G_c > 0$ |
| 11 | $\varepsilon_{cp}^p$ | - | Plastic strain at the peak in uniaxial compression (negative), $\varepsilon_{cp}^p < 0$ |
| 12 | $a$ | - | Increase of the peak strain with the confining pressure; $a = 0$: constant plastic peak strain, otherwise $a \ge a_{min}$ (see below) |
| 13 | $f_{tun}$ | - | Normalised residual tensile strength $f_{tu}/f_t$, $0 \le f_{tun} \le 1$ |
| 14 | $G_t$ | F/L | Fracture energy in tension, $G_t > 0$ |

All 14 parameters are required. Stresses are positive in tension in numgeo; $f_c$, $f_t$ and the normalised strengths are entered as positive values, the plastic peak strain $\varepsilon_{cp}^p$ as a negative value (compression). The fracture energies are energies per crack area (e.g. kN/m with kN and m). The parameters are checked when the input file is read; an inadmissible value stops the analysis with a message that names the material and the parameter.

With $a > 0$ the plastic peak strain increases with the mean stress beyond the uniaxial state ($p < -f_c/3$). The increase must not be negative, which requires

$$
a \ge a_{min} = \frac{2\sin\varphi_{max}\, f_c/E}{(1-\sin\varphi_{max})\,(f_c/E - \varepsilon_{cp}^p)},
$$

e.g. $a_{min} \approx 1.9$ for $E = 25$ GPa, $f_c = 40$ MPa, $\varphi_{max} = 37°$ and $\varepsilon_{cp}^p = -0.001$.

Typical values for shotcrete and concrete after 28 days are given by Schädlich & Schweiger (2014)[@schaedlich2014shotcrete] and in the PLAXIS manual[@plaxis2019mm]: $\varphi_{max} = 35$ to $43°$, $\psi = 0$ to $10°$, $f_{c0n} = 0.10$ to $0.25$, $f_{cfn} = f_{cun} = 0.1$, $a = 16$ to $20$, $f_t/f_c \approx 0.1$, $f_{tun} = 0$, $G_t = 0.05$ to $0.15$ kN/m, $G_c = 30$ to $70$ kN/m.

---

## Behaviour

* **Elasticity:** linear isotropic; unloading and reloading are elastic with the initial stiffness (no stiffness degradation, plastic strains are permanent).
* **Compression:** the Mohr-Coulomb yield surface starts at $f_{c0n} f_c$ in uniaxial compression and is mobilised quadratically up to $f_c$ at the plastic peak strain; afterwards the strength softens linearly to $f_{cfn} f_c$ (plastic strain range from $G_c$ and $L_{eq}$), then linearly to $f_{cun} f_c$ with the plastic softening modulus $-E/2$, and stays at the residual strength. The intermediate principal stress has no influence (Mohr-Coulomb); the biaxial compressive strength equals the uniaxial one.
* **Tension:** linear elastic up to $f_t$, then linear softening to $f_{tun} f_t$ over the plastic strain $\varepsilon_{tu}^p = 2 G_t / ((1+f_{tun}) f_t L_{eq})$. The tensile strength is common to all directions: after a crack has formed, the tensile strength is reduced in every direction (isotropic softening). In compression, a crack transmits stresses again without a closure condition.
* **Interaction:** the tension cut-off is limited to the apex of the (softened) Mohr-Coulomb envelope; after compression softening the tensile strength decreases accordingly.

---

## Optional parameters

```numgeo
*Optional mechanical parameter
viscosity, <value>
```

* `viscosity`: relaxation time $\mu$ (time) of the [viscous regularisation](../../../theory/constitutive-models/mechanical-models/concrete.md#viscous-regularisation). Default: 0 (rate-independent model).

The regularisation is a numerical aid: the stress lags behind the rate-independent stress by the overstress $Q$, which relaxes with $\mu$. It lets analyses pass softening in which the elements with quadratic interpolation stop. It is not needed with linear elements. Choose $\mu$ of the order of the time increment and small against the duration of the softening, and check the results with a second value:

* the dissipated energy increases with $\mu$ and with the rate of softening; for $\mu = 0.001$ s in the [benchmark](../../../benchmark/constitutive-models/concrete.md#viscous-regularisation) linear elements dissipate 1.03 to 1.16 $G_t$;
* with quadratic elements the crack still localises inside the elements: the energy lies between 0.81 and 1.16 $G_t$ and changes with the time increment;
* the viscosity acts in the time of the analysis, so the result of a static step depends on its time scale.

---

## Equivalent length and mesh

The softening laws are regularised with the equivalent length $L_{eq}$ of the element: $L_{eq} = \sqrt{A}$ for quadrilaterals and $L_{eq} = \sqrt{2A}$ for triangles (plane strain and axisymmetric; $A$ is the area in the $r$-$z$ plane), $L_{eq} = V^{1/3}$ for hexahedra and $L_{eq} = (6V)^{1/3}$ for tetrahedra, computed from the initial coordinates. The dissipated energy per crack area equals $G_t$ (and $G_c$ for the softening part controlled by it) when the crack runs through a band of one element (or one cell of a subdivided mesh) width and the element size normal to the crack is close to $L_{eq}$. Hence:

* use elements with an aspect ratio close to one in regions where cracks are expected; for elongated elements the dissipated energy scales with (element size normal to the crack)/$L_{eq}$;
* prefer quadrilaterals and hexahedra with linear interpolation (`u4-solid`, `u4-solid-ax`, `u8-solid-3d`) in zones of cracking. The factors 2 and 6 in $L_{eq}$ of triangles and tetrahedra are the number of elements per square and cube: a mesh of squares split into two triangles or of cubes split into six tetrahedra dissipates $G_t$ when all elements of the cell soften. With quadratic elements the softening can localise inside an element: `u10-solid-3d` bars stop after the peak, and a single quadratic element whose integration points all soften can stop near the end of the softening ([benchmark, element types](../../../benchmark/constitutive-models/concrete.md#element-types));
* a crack along a plane of symmetry of the model dissipates the energy of half a crack band: a crack in the symmetry plane of a half model corresponds to a band of two elements in the full model (use $G_t/2$ there if the post-peak response matters);
* $L_{eq}$ is written to the state variable `l-eq` of every integration point and can be checked in the output.

!!! warning "Snap-back limit"
    The softening laws are only admissible on the integration-point level if the plastic softening modulus is smaller in magnitude than the elastic stiffness of the active yield planes ($E$ in uniaxial stress, the bulk modulus $K$ for cracking in all three directions). This limits the element size:

    $$
    L_{eq} < \frac{2\,\min(E, K)\,G_t}{(1-f_{tun}^2)\,f_t^2} \quad \text{(tension)}, \qquad
    L_{eq} < \frac{2\,E\,G_c}{(1-f_{cfn}^2)\,f_c^2} \quad \text{(compression)}, \qquad K = \frac{E}{3(1-2\nu)}.
    $$

    The analysis stops with an error message naming the element, its $L_{eq}$ and the limit if an element violates one of the limits (e.g. 0.33 m in tension for $E = 25$ GPa, $\nu = 0.2$, $f_t = 2.5$ MPa, $G_t = 0.075$ kN/m). A softening region that is large compared with the limit can still show a snap-back of the global load-displacement curve under displacement control; the analysis then stops at the snap-back point.

The model can be assigned to continuum elements only (2D, axisymmetric and 3D solid elements of all interpolation orders); beam, truss and shell elements have no equivalent length.

---

## Numerical aspects

* The material Jacobian is the derivative of the stress return (finite differences with the active yield planes fixed); it gives quadratic convergence of the equilibrium iteration in hardening and softening. Where the active planes have reached their residual strength and at the hydrostatic tension apex the elastic stiffness is returned (as for the Mohr-Coulomb-2 model), so that fully cracked or crushed regions do not make the global stiffness singular. On an edge of the yield surfaces (two equal principal stresses, e.g. uniaxial compression) the Jacobian is elastic in the two deviatoric modes of the plane of the equal principal stresses, in which the consistent tangent has no stiffness.
* In softening the global stiffness matrix can become indefinite; direct solvers are recommended.
* If no admissible stress return is found, the model requests a cutback of the time increment.
* The model is not reducible in strength reduction analyses (`*Reducible strength` is not accepted).
* `*Model change, material` from another material (e.g. linear elastic or Bingham) to Concrete keeps the stress; the state variables of the Concrete model start at zero.

---

## State variables

| Variable | Position in `statev` | Description |
|---|:---:|---|
| `eps-pl-c` | 1 | $\kappa_c$: accumulated minor principal plastic strain of the Mohr-Coulomb planes ($\ge 0$) |
| `eps-pl-t` | 2 | $\kappa_t$: accumulated plastic strain of the Rankine planes ($\ge 0$) |
| `h-c` | 3 | $H_c = \kappa_c / \lvert\varepsilon_{cp}^p(p)\rvert$; $H_c < 1$ hardening, $H_c = 1$ peak, $H_c > 1$ softening |
| `h-t` | 4 | $H_t = \kappa_t/\varepsilon_{tu}^p$; 0 uncracked, $0 < H_t < 1$ softening crack, $H_t \ge 1$ residual tensile strength |
| `f-cy` | 5 | Current compressive yield stress $f_{cy}$ (F/A) |
| `f-ty` | 6 | Current tensile strength $f_{ty}$ (F/A) |
| `l-eq` | 7 | Equivalent length of the element $L_{eq}$ (L) |
| `yield-mode` | 8 | Active planes of the last increment: 0 elastic; 1 Mohr-Coulomb, 2 Rankine, 3 both (regular, $\sigma_1 > \sigma_2 > \sigma_3$); 4, 5, 6 the same on the triaxial compression edge ($\sigma_1 = \sigma_2$); 7 Mohr-Coulomb and 9 Mohr-Coulomb with Rankine on the triaxial extension edge ($\sigma_2 = \sigma_3$); 10 hydrostatic tension apex |
| `q11`, `q22`, `q33`, `q12`, `q13`, `q23` | 9 to 14 | Overstress $Q$ of the viscous regularisation (F/A), 0 without it |

The state variables can be requested by name in [element and integration-point output](../../output/field.md#element-output).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/concrete.md)

-   :material-check-decagram:{ .lg .middle } __Benchmarks__

    ---

    [:octicons-arrow-right-24: Verification](../../../benchmark/constitutive-models/concrete.md)

</div>
