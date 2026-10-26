#High-Cycle Accumulation (HCA) model for sand 

The High-Cycle Accumulation (HCA) model for sand as proposed by Niemunis et al. (2005)[@NiemunisWichtmann05_model]. The current implementation allows to link the HCA model to:

* [Hypoplasticity + Intergranular Strain](./hypoplasticity_igs.md)
* [Hypoplasticity + ISA model](./hypoplasticity_isa.md)
* [Sanisand](./sanisand.md#sanisand)
* [Sanisand-2](./sanisand.md#sanisand-2)
* [Linear Elasticity](./linear_elasticity.md)

These will be used in the low-cycle phase of the HCA model. 

Depending on the choice of "low-cycle" model, the input commands take the following form:

* Hypoplasticity + Intergranular Strain
    ```numgeo
    *Mechanical = HCA_Hypoplasticity
    phi (rad), nu (-), h_s (F/A), n (-), e_d0 (-), e_c0 (-), f_ei0 (-), alpha (-)
    beta (-), m_T (-), m_R (-), R (-), beta_R (-), chi (-), K^w (F/A)
    C_N1 (-), C_N2 (-), C_N3 (-), C_ampl (-), C_e (-), 0, C_p (-), 0
    C_Y (-), C_Pi1 (-), C_Pi2 (-), C_Pi3 (-), p_atm (-), e_ref (-), epsilon^ampl_ref (-), A (-)
    a (-), n (-), nu (-), phi_c (rad)
    ```
* Hypoplasticity + ISA model
    ```numgeo
    *Mechanical = HCA-HYPO-ISA
    phi (rad), h_s (F/A), n (-), e_d0 (-), e_c0 (-), e_i0 (-), alpha (-), beta (-) 
    m_R (-), R (-), beta_h0 (-), chi^0 (-), chi^max (-), epsilon^acc (-), c^z (-), beta_hmax (-)
    C_N1 (-), C_N2 (-), C_N3 (-), C_ampl (-), C_e (-), 0, C_p (-), 0
    C_Y (-), C_Pi1 (-), C_Pi2 (-), C_Pi3 (-), p_atm (-), e_ref (-), epsilon^ampl_ref (-), A (-)
    a (-), n (-), nu (-), phi_c (rad)
    ```
* Sanisand
    ```numgeo
    *Mechanical = HCA_Sanisand
    p_atm (F/A), e_0 (-), lambda_c (-), xi (-), M_c (-), M_e (-), m (-), G_0 (-)
    nu (-), h_0 (-), c_h (-), n_b(-), A_0 (-), n^d (-), z_max (-), c_z (-)
    C_N1 (-), C_N2 (-), C_N3 (-), C_ampl (-), C_e (-), 0, C_p (-), 0
    C_Y (-), C_Pi1 (-), C_Pi2 (-), C_Pi3 (-), p_atm (F/A), e_ref (-), epsilon^ampl_ref (-), A (-)
    a (-), n (-), nu (-), phi_c (rad)
    ```
* Sanisand-2
    ```numgeo
    *Mechanical = HCA-Sanisand-2
    p_atm (F/A), e_0 (-), lambda_c (-), xi (-), M_c (-), M_e (-), m (-), G_0 (-)
    nu (-), h_0 (-), c_h (-), n_b(-), A_0 (-), n^d (-), z_max (-), c_z (-)
    C_N1 (-), C_N2 (-), C_N3 (-), C_ampl (-), C_e (-), 0, C_p (-), 0
    C_Y (-), C_Pi1 (-), C_Pi2 (-), C_Pi3 (-), p_atm (F/A), e_ref (-), epsilon^ampl_ref (-), A (-)
    a (-), n (-), nu (-), phi_c (rad)
    ```
* Linear Elasticity
    ```numgeo 
    *Mechanical = HCA_Linear_elasticity
    E (F/A), nu (-)
    C_N1 (-), C_N2 (-), C_N3 (-), C_ampl (-), C_e (-), 0, C_p (-), 0
    C_Y (-), C_Pi1 (-), C_Pi2 (-), C_Pi3 (-), p_atm (F/A), e_ref (-), epsilon^ampl_ref (-), A (-)
    a (-), n (-), nu (-), phi_c (rad)
    ```

The material parameters of the "low-cycle" model are described in the corresponding sections of the Reference Manual ([Hypoplasticity + Intergranular Strain](./hypoplasticity_igs.md), [Hypoplasticity + ISA model](./hypoplasticity_isa.md), [Sanisand](./sanisand.md#sanisand), [Sanisand-2](./sanisand.md#sanisand-2), and [Linear Elasticity](./linear_elasticity.md)). The parameters of the HCA model are given below.

- $C_{N1}$, $C_{N2}$ and $C_{N3}$ define the accumulation rate with respect to the number of cycles.

- $C_{\text{ampl}}$ takes into account the influence of the strain amplitude on the accumulation rate. It can be estimated following Wichtmann et al. (2016)[@wichtmann2016soil] using $C_{\text{ampl}} = 1.7$.

- $C_{e}$ takes into account the influence of the void ratio on the accumulation rate. It can be estimated following Wichtmann et al. (2016)[@wichtmann2016soil] using 

    $$C_e = 0.95\cdot e_{\text{min}}$$
    
    , where $e_{\text{min}}$ is the minimum void ratio of the considered material.

- $C_{p}$ takes into account the influence of the mean effective stress on the accumulation rate. It can be estimated following Wichtmann et al. (2016)[@wichtmann2016soil] using 

    $$C_p = 0.41\cdot [1-0.34~(d_{50} ~\text{(mm)}-0.6)]$$ 
    
    where $d_{50}$ is the mean grain size of the considered material.

- $C_{Y}$ takes into account the influence of the normalised stress ratio on the accumulation rate. It can be estimated following Wichtmann et al. (2016)[@wichtmann2016soil] using 

    $$C_Y = 2.60\cdot [1+0.12~\text{ln}(d_{50} ~\text{(mm)}/0.6)].$$

- $C_{Pi1}$, $C_{Pi2}$ and $C_{Pi3}$ take into account polarization changes. They are currently not used, i.e. can be chosen arbitrarily.

- $p_{atm}$ (F/A) is the atmospheric pressure, usually given by 100 kPa.

- $e_{\text{ref}}$ is the reference void ratio usually chosen identical to the maximum void ratio.

- $\varepsilon^\text{ampl}_{\text{ref}}$ is reference strain amplitude usually chosen to $10^{-4}$

- $A$, $a$, $n$ and $\nu$ are the parameters defining the elastic stiffness of the model. They are usually chosen to $A=1209$, $a=1.63$, $n=0.5$, $\nu = 0.32$ (Wichtmann et al., 2016)[@wichtmann2016soil].

- $\varphi_c$ is the friction angle used for the calculation of the flow direction and plastic strains (adopting the Matsuoka-Nakai failure surface with a 30 % higher value of $\varphi_c$). It is usually identical to the friction angle (but not in all cases).

## Optional Parameters 

```numgeo 
*Optional mechanical parameter
<property 1>, <value 1>...
<property 2>, ...
``` 

A list of currently supported optional parameters is given below:

-   `scale_gA`: A scaling factor
    ($0 \leq c^{gA} \leq 1$) for the cyclic history variable $g^A$. At
    the beginning of each (new) hca phase, the cyclic history variable
    $g^A$ is computed as $g^A=c^{gA} \cdot g^A_0$, where $g^A_0$ is the
    cyclic history variable at the end of the last HCA phase. By
    choosing $c^{gA}=0$, $g^A$ is reset to zero. The default value is
    $c^{gA}=1$ (no scaling, a complete transfer of cyclic history to the
    new HCA phase).

-   `dstran_rec`: Required distance between two
    strain points during the recording step in which case a new strain
    point is saved. This values seldom has to be changed, except in
    cases where the strain path consists of values which are either much
    lower or larger than the default value of $8\cdot 10^{-5}$.

-   `cos_rec`: Required cosine between two strain
    points during the recording step in which case a new strain point is
    saved. The default value is 0.83969.
-   `proj_angle`: Multiplicator for `phi_c` in the calculation of plastic strain using the Matsuoka-Nakai model. This multiplicator does only affect the bounding surface of the Matsuoka-Nakai model. The default value is 1.3. 

-   `scale_fampl_max`: The maximum possible value
    of $f_{ampl}$ is calculated by
    $10^{\text{scale_fampl_max}\cdot C_{ampl}}$ instead of
    $10^{C_{ampl}}$. The default value is 1. 

- `m_factor`: Determines how the critical stress ratio $M$ is calculated in the flow rule of the HCA model. If `m_factor`=0, a stress-dependent non-constant value of $M$ will be calculated. For any other value of `m_factor`, the critical stress ratio $M$ for compression is used, which is the default case. 
  
- `simple_eps_ampl`: By default, the successive  projection of the recorded strain path is used to calculated the strain amplitude[@NiemunisWichtmann05_model]. If a definition based on the maximum euclidean distance is to be used, set `simple_eps_ampl`=1. 

-   `ga_definition`: By default, the cyclic history state variable is calculated using
 
    $$
    g^A = f_{\text{ampl}}C_{N1} \ln(1+C_{N2}N)
    $$

    If the definition derived in [@staubach2021a] is supposed to be used, set `ga_definition`=1. Only in case the adaptive strain amplitude definition (see below) or update cycles are used, this influences the results. The equation used for $g^A$ is:
  
    $$
    g^A\bigg\vert_{N=N_0}^{N=N} =\int_{N_0}^{N} \dot{f}_N f_{\text{ampl}}dN\\
     =  \ln\frac{1+C_{N2}N}{1+C_{N2}N_0} C_{N1}  f_{\text{ampl}}
    $$

   where $N_0$ is the number of cycles at which the strain amplitude changed (automatically calculated in the code and available as output, see end of this page).

## State variables {#state-variables-4 .unnumbered}

The state variables are initialized according to the linked conventional
constitutive models.   

If the strain amplitude is to be given by a `*initial conditions, type = state variables` statement, it is possible either by using
```numgeo 
*initial conditions, type = state variables, default
<elset>, strain_ampl, <value>
``` 
or by using a [user routine](../../user/initial-statev.md):
```numgeo
*initial conditions, type = state variables, user
<elset>
``` 
In the user file, the `statev(100)` corresponds to the strain amplitude of the HCA model. 

## Additional definitions 

Additionally, the name of the steps used for the low-cycle (also
referred to as implicit) phase, the name of the step used for the
recording of the strain and subsequent calculation of the strain
amplitude and the high-cycle (also referred to as explicit) steps have
to be defined. This is done by using

```numgeo
*Implicit hca steps
<implicit step 1>, <implicit step 2>, <implicit step 3>
*Recording hca steps
<recording step 1>, <recording step 2>
*Explicit hca steps
<HCA step 1>, <HCA step 2> 
```

where the names of the respective steps have to be given. Lastly, the
period of the individual cycles has to be defined by:

```numgeo
*HCA cycle time
<period HCA step 1>, <period HCA step 2>
```

Typically, the period is 1 for static analysis. Only for transient
analyses the period matters.


Optionally, during the recording step, one may define only a certain
time window for the recording of the strain path. This is defined by:

```numgeo
*HCA recording time
`<start time 1>, <end time 1>, <start time 2>, <end time 2>
```

The HCA calculations can be performed using an adaptive strain amplitude
definition by using

```numgeo
*Adaptive strain ampl, <time =>, <frequency =>`
```
either `<time = value 1, value 2, value 3, ...>` or
`<frequency = value>` has to be given. `time` defines the times at which
the strain amplitude is updated during the HCA steps. `frequency`
($\geq 1$) defines the frequency in terms of increments at which the
strain amplitude is updated during the HCA steps. It is strongly
recommended to use the `*Non-local` (see [here](../../non-local.md)) method with the same time/frequency
specifications during the HCA step and specifying `statev=100` to smooth
the field of updated strain amplitude.

You may define a minimum strain amplitude by using
```numgeo
*Minimum eps ampl
<Value of minimum strain amplitude>
```
The function $f_{\text{ampl}}$ is zero for values below the specified
value.

You may define a maximum strain amplitude by using
```numgeo
*Maximum eps ampl
<Value of maximum strain amplitude>
```

The function $f_{\text{ampl}}$ is constant for values above the
specified value.

## Additional output variables 

The output variables for the Hypoplasticity + Intergranular Strain (see [here](./hypoplasticity_igs.md)), the Sanisand (see [here](./sanisand.md))  are available.

The following additional output variables are available in the `*Output`
command (see [here](../../output/field.md)):

- Strain amplitude (only during the high-cycle step): `strain_ampl`

- Accumulated strain rate: `strain_acc`

- Cyclic history variable $g^A$: `cyclic_history`

- Factor $f_{\text{ampl}}$: `fampl`

- Factor $f_{\text{e}}$: `fe`

- Factor $f_{\text{p}}$: `fp`

- Factor $f_{\text{Y}}$: `fY`

- Number of recorded strain points during the recording step: `Nrec_points`

- Number of cycles the strain amplitude was updated the last time (only relevant if `*Adaptive strain ampl` is used): `N0`

- Cyclic history variable $g^A$ the strain amplitude was updated the last time (only relevant if `*Adaptive strain ampl` is used): `cyclic_history0`

---

## References
