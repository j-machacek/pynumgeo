# Bingham

Elasto-viscoplastic model for materials with a yield stress which flow like a viscous fluid once the yield stress is exceeded (Bingham fluids): linear elastic below the yield stress, Bingham flow above it (shear stress = yield stress + plastic viscosity $\times$ shear rate). At constant strain the shear stress relaxes to the yield stress; the volumetric response is linear elastic. The formulation is described in the [theory manual](../../../theory/constitutive-models/mechanical-models/bingham.md).

## Input syntax

```numgeo
*Mechanical = Bingham
E (F/A), nu (-), tau_y (F/A), eta (F/A x time)
```

### Material parameters

| Index | Symbol | Unit | Description |
| :---: | :---: | :---: | :--- |
| 1 | $E$ | F/A | Young's modulus, $E > 0$ |
| 2 | $\nu$ | - | Poisson's ratio, $-1 < \nu < 0.5$ |
| 3 | $\tau_y$ | F/A | Yield stress in shear (Bingham yield stress), $\tau_y \ge 0$ |
| 4 | $\eta$ | F/A $\cdot$ time | Plastic viscosity, $\eta \ge 0$. $\eta = 0$: rate-independent von Mises plasticity with the yield stress $\tau_y$ |

$\tau_y = \eta = 0$ leaves no deviatoric stiffness and is not admissible. The yield stress refers to the equivalent shear stress $\sqrt{J_2}$, which equals the shear stress in simple shear; in steady simple shear the model gives $\tau = \tau_y + \eta\,\dot\gamma$. The model is formulated for small strains and is available for 2D, axisymmetric and 3D solid elements.

!!! warning "Time scale"
    The viscous response is evaluated with the time increment of the step. The step time therefore has to be the physical time of the process. For $\eta > 0$ and a time increment of zero the response is elastic; for time increments much larger than the relaxation time $\eta / G$ the shear stress relaxes to $\tau_y$ within the increment.

!!! warning "Static analyses with flowing material"
    In the direction of the flow the material Jacobian is $2G/(1 + G\Delta t/\eta) \approx 2\eta/\Delta t$: with a small viscosity a flowing region has practically no shear stiffness, and the equilibrium iteration of a static analysis with a large flowing region can stall. A larger viscosity regularises the flow; the viscous stress $\eta\,\dot\gamma$ then has to be small compared with the stresses of interest. Large flow distorts the mesh; strongly distorted elements end the analysis.
    Formulations that take a shear modulus from the material Jacobian (the stabilisation of the u-J elements, contact penalty factors derived from the material stiffness) get a vanishing modulus from flowing material; use constant penalty factors in contact with it.

## State variables

| Variable | Position in `statev` | Description |
|---|:---:|---|
| `gamma_vp` | 1 | Accumulated viscoplastic shear strain $\gamma^{vp}$ |
| `vp_flow` | 2 | 1: viscoplastic flow in the last increment, 0: elastic |

The state variables can be requested by name in [element and integration-point output](../../output/field.md#element-output).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/bingham.md)

</div>
