# Damping

```numgeo
*Material, ...
*Damping
alpha_R, beta_R
```

The `*Damping` sub-keyword defines Rayleigh damping for the material. The first value is the mass-proportional coefficient $\alpha_R$ in s⁻¹; the second is the stiffness-proportional coefficient $\beta_R$ in s. For a linear mechanical system,

$$
\begin{aligned}
\boldsymbol C&=\alpha_R\boldsymbol M+\beta_R\boldsymbol K,\\
\zeta(\omega)&=\frac{1}{2}\left(\frac{\alpha_R}{\omega}+\beta_R\omega\right),\\
\omega&=2\pi f.
\end{aligned}
$$

Here $\boldsymbol M$, $\boldsymbol K$ and $\boldsymbol C$ are the mass, stiffness and damping matrices, $f$ is frequency in Hz and $\zeta$ is the fraction of critical damping. The coefficients are constants; the damping ratio varies with frequency.

---

## Calibration at two frequencies

For an equal target damping ratio $\zeta_0$ at two positive frequencies $\omega_1<\omega_2$,

$$
\begin{aligned}
\alpha_R&=2\zeta_0\frac{\omega_1\omega_2}{\omega_1+\omega_2},\\
\beta_R&=\frac{2\zeta_0}{\omega_1+\omega_2}.
\end{aligned}
$$

For an earthquake-loaded soil layer, determine a relevant loading frequency from the input spectrum and estimate the fundamental frequency of the layer. For a homogeneous layer over a rigid base with a free surface, the latter is $f_s\approx V_s/(4H)$. Use these frequencies to establish the calibration interval; either can be the lower frequency. The choice must account for both the excitation and the soil response. Inspect the resulting damping over the other frequencies contributing to the required output.

Rayleigh damping equals the target at the two selected frequencies; it falls below the target between them and increases outside this range. The minimum occurs at $\omega=\sqrt{\alpha_R/\beta_R}$ and is $\zeta_{\min}=\sqrt{\alpha_R\beta_R}$ when both coefficients are positive.

For 3% damping, use $\zeta_0=0.03$. The earthquake benchmark uses a loading-spectrum peak at 1.505445 Hz and the 1 Hz fundamental frequency of a 50 m layer, giving:

```numgeo
*Damping
0.22652240560274, 0.0038114170212188
```

The [earthquake benchmark](../../benchmark/dynamics/rayleigh-damping.md) derives these values from the input record and layer properties, demonstrates the input, and checks damping and complete response histories with separate time and mesh refinement. Choosing calibration frequencies does not replace the higher-frequency resolution checks needed to select the element size and time increment.

---

## Calibration at one frequency

With **mass-proportional damping only**, choose $\alpha_R=2\zeta_0\omega_0$ and $\beta_R=0$. With **stiffness-proportional damping only**, choose $\alpha_R=0$ and $\beta_R=2\zeta_0/\omega_0$.

These are alternative single-term choices. Entering both nonzero values together would give $2\zeta_0$ at $\omega_0$, twice the intended damping ratio.

---

## Relation to time integration

The Rayleigh coefficients define viscous damping and are distinct from the parameters of the [dynamic time integrator](../step/dynamic.md). In particular, the HHT parameter $\alpha_{\mathrm{HHT}}$ is not the mass-proportional coefficient $\alpha_R$.

The calibration above assumes a linear system with fixed mass and stiffness. If stiffness changes during a nonlinear analysis, the modal frequencies and damping ratios need to be reassessed. The earthquake benchmark uses linear elasticity and `*HHT=0` to examine Rayleigh damping without algorithmic damping of the undamped modes.