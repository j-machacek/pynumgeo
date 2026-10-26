# Bishop effective stress

```numgeo 
*Material, ...
*Bishop effective stress = <model>
<parameter 1>, ... , <parameter n>
``` 

In simulations with variable saturation, the total stress $\sigma_{ij}$ is decomposed into the effective stress $\sigma_{ij}'$ and the neutral stress following Bishops definition of effective stress:

$$
\begin{equation}
    \sigma_{ij}' = \sigma_{ij} - p^a 1_{ij} + \chi (p^a-p^w) 1_{ij}
\end{equation}
$$

Where $\chi$ is an averaging parameter introduced by Bishop \cite{}. In recent years, the most commonly used assumption for this parameter is to assume $\chi=S$, with $S$ being the degree of saturation. Recalling,that in coupled simulation of unsaturated soils (or in multi-phase TPM in general) the degree of saturation $S$ is often linked to the suction $s=p^a-p^w$ using a constitutive model, i.e. the soil water retention curve. Especially for fine grained soils (such as clay) this relation can take values of several thousand kPa for the suction. It is thus obvious, that the choice of $\chi$ may have a significant influence on the calculated effective stress and that the simple assumption of $\chi=S$ may result in a significant overestimation of the contribution of the suction to the effective stress.

In numgeo we therefore offer different constitutive models for the calculation of $\chi$:

## Effective-Saturation

A simple relation between the Bishop averaging parameter and the effective degree of saturation is used: $\chi=S^e=(S-S^{wr})/(1-S)$. By using $S^e$, we account for the decreasing influence of the suction on the effective stress when the degree of saturation approaches its residual value $S^{wr}$. This is the default setting and is set even if no information about the Bishop effective stress model is provided in the input file by the user. The keyword takes the following form:

```
*Bishop effective stress = Effective-Saturation
```

## Saturation

A simple relation between the Bishop averaging parameter and the degree of saturation is used: $\chi=S^w$. Notice that the choice $\chi=S^w$ might lead to an unrealistically high contribution of the suction to the effective stress for high suction values. The keyword takes the following form:

```
*Bishop effective stress = Saturation
```
    
## Crude-Switch

A very crude switch between saturated and partially saturated states:

$$
\begin{equation}
    \chi = \begin{cases} 1 & \mbox{for}~ S^e = 1 \\ 0 & \mbox{else} \end{cases}
\end{equation}
$$

The keyword takes the following form:

```
*Bishop effective stress = Crude-Switch
```

Note that for $S^e < 1$, the constitutive model takes the net stress $\sigma^{net}_{ij}=\sigma^{tot}_{ij}-p^a 1_{ij}$ as input, while for $S^e = 1$, the Terzaghi effective stress $\sigma_{ij}'=\sigma^{tot}_{ij}-p^w 1_{ij}$ is used.
    
## Lu-Likos

Lu and Likos proposed to use the following power law for $\chi$ with cutoff:
    
$$
\begin{equation}
    \chi = \begin{cases} 0 & \mbox{for}~ S \leq S^{wr} \\ (S^e)^\kappa & \mbox{for}~ S^{wr} < S < 1 \\
    1 & \mbox{for}~ S = 1\end{cases}
\end{equation}
$$
    
Therein, $S$ is the total degree of saturation, $S^e$ is the effective degree of saturation and $S^{wr}$ is the residual degree of saturation. $\kappa$ is a fitting parameter. The keyword takes the following form:

```
*Bishop effective stress = Lu-Likos
kappa, S^{wr}
```

## Power function

A simple power function linking the Bishop effective stress variable $\chi$ to the effective degree of saturation $S^e$:
    
$$
\begin{equation}
    \chi = (S^e)^\kappa
\end{equation}
$$
    
Therein, $S^e$ is the effective degree of saturation and $\kappa$ is a fitting parameter. The keyword takes the following form:

```
*Bishop effective stress = Power-Saturation
kappa
```

!!! info "Modified Bishop’s effective stress (ZSoil)"

    By appropriate choice of $\kappa$ the modified Bishop’s effective stress principle proposed by Truty and used in the software [ZSoil](https://zsoil.com/zsoil-2023/zsoil-2023-new-features/). The modified effective saturation preserves monotonic and asymptotic behavior of the resulting apparent cohesion with increasing suction. This approach can be obtained in combination with the van Genuchten soil-water retention model and by setting

    $$
    \kappa = \dfrac{1}{n_{vG}m_{vG}}
    $$

    Where $n_{vG}$ is the [van Genuchten](./hydraulic/van-genuchten.md) fitting parameter and $m_{vG}=1-1/n_{vG}$.