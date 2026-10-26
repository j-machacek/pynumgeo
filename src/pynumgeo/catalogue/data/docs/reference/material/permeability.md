# Permeability

```numgeo 
*Permeability [= model] [, specific weight = <unit weight of the pore water>]
<subsequent line(s)>
``` 

This keyword is used to prescribe the intrinsic permeability
$\bar{K}^s_{ij}$ (length²), equal for all pore-fluids of the material and not to
be confused with the hydraulic conductivity. The corresponding
hydraulic conductivity $k^\beta_{ij}$ (length/time) of the saturated (or dry) material
can be calculated as follows:

$k^\beta_{ij} = \bar{K}^s_{ij} \cdot \frac{\gamma^\beta}{\eta^\beta}$

therein $\gamma^\beta$ is the specific weight and $\eta^\beta$ the
dynamic viscosity (`*Dynamic viscosity`) of the fluid phase $\beta$ occupying the pore space.
Notice that the influence of the gravity (or generally spoken the
influence of body-forces) on the permeability is handled inside the
finite element. The following models are available in `numgeo`:

| Model | Input | Dependence on the void ratio $e$ |
|---|---|---|
| `*Permeability` | intrinsic permeability | constant, anisotropic |
| `*Permeability = isotropic` | intrinsic permeability | constant |
| `*Permeability = Kozeny-Carman` | intrinsic permeability | $\propto e^3/(1+e)$ |
| `*Permeability = Carrier` | hydraulic conductivity of the pore water | $k = c_k\, e^{d_k}/(1+e)$ |
| `*Permeability = Somogyi` | hydraulic conductivity of the pore water | $k = C\, e^{D}$ |
| `*Permeability = Tabular` | hydraulic conductivity of the pore water | table $k(e)$ |

## Constant permeability

-   `*Permeability`: the default permeability
    model assumes a constant anisotropic permeability of the material. 3
    parameters ($\bar{K}^s_{xx}, \bar{K}^s_{yy}, \bar{K}^s_{zz}$) are
    required in the `<subsequent line>` following the keyword:

    `*Permeability`  
    $\bar{K}^s_{xx}, \bar{K}^s_{yy}, \bar{K}^s_{zz}$

-   `*Permeability = isotropic`: assumes an
    isotropic permeability tensor ($\bar{K}^s_{ii}=K$) is assumed and
    only one parameter is required in the `<subsequent line>`:

    `*Permeability = isotropic`  
    $K$` `

## Kozeny-Carman

`*Permeability = Kozeny-Carman`: use a
Kozeny/Carman type constitutive model [@kozeny1927; @carman1939] to
prescribe the intrinsic permeability as a function of the porosity $n$ or of the void ratio $e = n/(1-n)$:

$\bar{K}^s(n) = \frac{1}{c} \frac{n^3}{(1-n)^2} d_{e}^2 = \frac{d_{e}^2}{c} \frac{e^3}{1+e}.$

This constitutive model requires two parameters: the fitting parameter $c$ (-) and the effective grain size $d_e$ (length).
The result is an intrinsic permeability (length²); the hydraulic conductivity of the pore water is
$k = \bar{K}^s \gamma^w/\eta^w$. For more information on the constitutive
model, the reader is referred to the [Theory Manual](../../theory/constitutive-models/permeability-models/kozeny-carman.md).

`*Permeability = Kozeny-Carman`    
$c$`, `$d_e$` `

## Hydraulic conductivity as a function of the void ratio

The options `Carrier`, `Somogyi` and `Tabular` take the **hydraulic conductivity** $k(e)$ of the pore water as a function of
the void ratio, in the form used by programs for the large-strain consolidation of slurries and tailings (MinTaCo,
FSConsol). numgeo converts it once, when the material is read, into the intrinsic permeability

$\bar{K}^s(e) = k(e)\,\frac{\eta^w}{\gamma^w}$

with the dynamic viscosity $\eta^w$ of the pore water (first value of `*Dynamic viscosity`, required) and the
unit weight of the pore water $\gamma^w$ given with the option `specific weight` (required, no default value). All
elements with pore water pressure then use $\bar{K}^s(e)$ like any other permeability. Units:

| Quantity | Unit | Example (kN, m, s) | Example (kN, m, days) |
|---|---|---|---|
| hydraulic conductivity $k$, coefficients $c_k$, $C$ | (length/time) of the analysis | (m/s) | (m/day) |
| dynamic viscosity $\eta^w$ | (stress·time) | 1.0e-6 (kPa·s) | 1.157e-11 (kPa·day) |
| `specific weight` $\gamma^w$ | (force/length³) | 9.81 (kN/m³) | 9.81 (kN/m³) |

!!! warning "Consistent unit weight of the pore water"

    The gravity is defined per step and per element set with [`*Body force`](../boundary-conditions/body-force.md); it can be ramped from zero or be absent. It is therefore not used for the conversion, and numgeo cannot check the `specific weight` against it. Use $\gamma^w = \rho^w g$ of the model (density of the pore water times the gravity of the body force); otherwise the effective hydraulic conductivity of the analysis differs from the input by the factor $\rho^w g/\gamma^w$.

### Carrier

```numgeo 
*Permeability = Carrier, specific weight = <gamma_w>
c_k, d_k
``` 

$k(e) = c_k\,\frac{e^{d_k}}{1+e}$

The power law used by MinTaCo (Eq. 2 in [@helinski2007]), after the power functions of Carrier et al. [@carrier1983].
Parameters: $c_k > 0$ (length/time), $d_k > 0$ (-).

### Somogyi

```numgeo 
*Permeability = Somogyi, specific weight = <gamma_w>
C, D
``` 

$k(e) = C\,e^{D}$

The power law of Somogyi [@somogyi1980], used by FSConsol [@agapito2015]. Parameters: $C > 0$ (length/time),
$D > 0$ (-). Example, phosphatic clay of the benchmark of Townsend & McVay [@townsend1990] in kN, m and s:

```numgeo 
*Permeability = Somogyi, specific weight = 9.81
2.931e-12, 4.65
``` 

### Tabular

```numgeo 
*Permeability = Tabular, specific weight = <gamma_w>
e_1, k_1
e_2, k_2
...
``` 

One data line per point (void ratio $e_i$ (-), hydraulic conductivity $k_i$ (length/time)), at least two points,
$e_i \geq 0$ in strictly increasing order and $k_i > 0$. Between the points $\ln k$ is interpolated linearly in $e$
(log-linear interpolation). Beyond the ends of the table the hydraulic conductivity is held at the value of the first or
the last point (no extrapolation); numgeo then writes one warning per analysis.

### Validation of the input

numgeo stops with an error message if the option `specific weight` is missing or not positive, if a coefficient or an
exponent of `Carrier` or `Somogyi` is not positive, if the table does not fulfil the conditions above, if
`*Dynamic viscosity` is missing, and if one of the three options is combined with `*Swelling` with
$n_0 > 0$: the swelling elements multiply the permeability with their own Kozeny/Carman factor of the porosity, so that
the dependence on the porosity would be accounted for twice.

## Notes on the void-ratio dependent models

* The [Theory Manual](../../theory/constitutive-models/permeability-models/index.md) shows how the parameters of the
  models change the permeability.
* The permeability is evaluated with the void ratio of the integration point at the start of the increment and is kept
  constant during the increment (also for `Kozeny-Carman`); the element matrix contains no derivative with respect to
  the void ratio. The error of this lag is of first order in the time increment: limit the maximum time increment where
  the void ratio changes quickly, e.g. at the beginning of the self-weight consolidation of a slurry.
* The void ratio is defined with [`*Initial conditions, type=void ratio`](../initial-conditions/void-ratio.md); define it
  for all elements of materials with a void-ratio dependent permeability. It is updated with
  $e = e_0 + (1+e_0)\,\mathrm{tr}\,\Delta\boldsymbol{\varepsilon}$ in every increment, also with `nlgeom` (first-order
  approximation of the volume change of the increment).
* In partially saturated elements the relative permeability multiplies $\bar{K}^s(e)$.

See the benchmark [Void-ratio dependent permeability](../../benchmark/two-phase-flow/permeability-void-ratio.md) and the
tutorials [Seepage through layers of different void ratio](../../tutorial/flow/layered-seepage.md) and
[Self-weight consolidation of a slurry](../../tutorial/flow/slurry-consolidation.md).
