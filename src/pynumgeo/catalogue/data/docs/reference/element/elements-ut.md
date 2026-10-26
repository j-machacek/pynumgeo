# Solid elements with temperature dof (u-T elements)

These single-phase solid elements describe heat conduction and mechanical deformation with the primary unknowns:

* solid displacements $u_1$, $u_2$ (and $u_3$ in 3D);
* absolute temperature $T$, identified by the degree-of-freedom label `tt`.

The thermal field requires [conductivity](../material/thermal-conductivity.md), [specific heat](../material/specific-heat.md), [density](../material/density.md) and an [initial temperature](../initial-conditions/temperature.md). Prescribed temperatures are defined with [`*Boundary`](../boundary-conditions/boundary.md#temperature); heat supplies with [`*Cload`](../boundary-conditions/cload.md) and [`*Dload`](../boundary-conditions/dload.md#volume-heat-source).

<div class="grid cards" markdown>

- __Mixed elements__

    ---

    Quadratic displacement and linear temperature interpolation.

    [:octicons-arrow-right-24: Mixed elements](#mixed-elements)

- __Equal-order elements__

    ---

    Linear displacement and temperature interpolation, with an optional projection stabilisation.

    [:octicons-arrow-right-24: Equal-order elements](#equal-order-elements)

</div>

## Mixed elements

The independent temperatures are located at the corner nodes. Temperatures at the additional displacement nodes are interpolated from these corner values. The complete quadratic pairs are $P_2/P_1$ on simplices and $Q_2/Q_1$ on quadrilaterals and bricks; serendipity displacement elements are listed separately.

### 2D elements

| Element label | Shape | Displacement nodes | Independent temperature nodes | nIP | Displacement interpolation |
|---|---|---:|---:|---:|---|
| `u6t3-solid` | triangle | 6 | 3 | 3 | quadratic |
| `u8t4-solid` | quadrilateral | 8 | 4 | 9 | serendipity quadratic |
| `u9t4-solid` | quadrilateral | 9 | 4 | 9 | complete quadratic |

### 3D elements

| Element label | Shape | Displacement nodes | Independent temperature nodes | nIP | Displacement interpolation |
|---|---|---:|---:|---:|---|
| `u10t4-solid-3d` | tetrahedron | 10 | 4 | 4 | quadratic |
| `u20t8-solid` | brick | 20 | 8 | 27 | serendipity quadratic |
| `u27t8-solid` | brick | 27 | 8 | 27 | complete quadratic |

## Equal-order elements

All nodes have independent displacement and temperature unknowns. The variants with suffix `-stab` require an explicit [`*Thermal stabilisation`](../material/thermal-stabilisation.md) factor. The variants without that suffix omit the projection term.

### 2D elements

| Element label | Shape | Nodes | Order | nIP |
|---|---|---:|---|---:|
| `u3t3-solid`, `u3t3-solid-stab` | triangle | 3 | linear | 3 |
| `u4t4-solid`, `u4t4-solid-stab` | quadrilateral | 4 | linear | 4 |

### 3D elements

| Element label | Shape | Nodes | Order | nIP |
|---|---|---:|---|---:|
| `u4t4-solid-3d`, `u4t4-solid-3d-stab` | tetrahedron | 4 | linear | 4 |
| `u8t8-solid-3d`, `u8t8-solid-3d-stab` | brick | 8 | linear | 8 |

## Remarks

* nIP denotes the number of integration points. Reduced integration is not offered.
* Use the continuum-element node and face numbering. In each mixed-element connectivity record, the first nodes are the independent temperature nodes, in the number listed above. In the nine-node quadrilateral, node 9 is the centre after the four corner and four edge nodes.
* Prescribed `tt` values (`*Boundary`) and concentrated heat supplies (`*Cload`) are only allowed at the independent temperature nodes; numgeo stops with an error otherwise. A node must interpolate the temperature in all its u-T elements or in none of them.
* The serendipity mixed variants must not be confused with complete Taylor-Hood $Q_2/Q_1$ pairs. See the [theory](../../theory/elements/thermoelastic-solids.md) for stabilisation and its applicability.

Supported: 2D **plane strain**, 3D, backward-Euler `*Transient`, and `*Static`, with a single material phase and constant transport properties. [`Thermal_Elasticity`](../material/mechanical/thermal_elasticity.md) provides isotropic linear thermoelastic coupling. Temperature-independent models retain their normal mechanical response through the common material interface; their constitutive history and cutback requests are preserved, but both thermal coupling blocks are zero.

## Additional compatibility checks

Contacts, PFEM transfer, embedded regions, submodels, model change/reset/modify, phantom elasticity/viscosity, `*Line search`/`*Accelerator` and `*Equation`, flexible, Robin and user constraints of `TT` are rejected; use `FILMi` for thermal Robin conditions. A steady (`*Static`) analysis needs a prescribed `TT` or a film condition in every conductive region, see [`*Static`](../step/static.md).
