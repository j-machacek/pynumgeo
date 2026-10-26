# Amplitude

```numgeo
*Amplitude, Name = <amplitude name> , Type = <amplitude type>
<amplitude parameter 1>, ..., <amplitude parameter n>
```

This option enables the user to define amplitudes for later use (e.g.
loading or boundary conditions).

-   `Name=<amplitude name>`

    The name of the amplitude which will be used for later assignment to loads and boundary conditions.

-   `Type = <amplitude type>`

    Set this keyword equal to the amplitude type to be used. The subsequent lines `<amplitude parameter 1>, ... , <amplitude parameter n>` depend on the type chosen. This keyword is mandatory. The following amplitude types are available:

    -   `ramp`
        Linear increasing amplitude with variable starting ($\sqcup_0$) and ending ($\sqcup_1$) time. The subsequent lines take the
        following form:  

        `t0, v0, t1, v1`  

    -   `periodic`
        Amplitude as a Fourier series of `N` number of terms:
      
        $f(t) = \begin{cases}
        A_0 + \sum_i^N \Big( A_i \cos i \omega (t - t_0) + B_i \sin i \omega (t - t_0) \Big) & \text{~for: }~ t \geq t_0 \\
        A_0 & \text{~for: }~ t < t_0 
        \end{cases}$  
      
        The subsequent lines take the following form:  

        `N, A0, t0, omega` 
        `A1, B1`  
        `...`  
        `AN, BN`  

    -   `rising_cosine`
        Periodic function with increasing amplitude of the following form:  
      
        $f(t) = \begin{cases}
        			\frac{A_1}{t_1} \cdot t \cdot \cos(\omega t) & \text{~for: }~ t \leq t_1 \\
        			A_1 \cdot \cos(\omega t) & \text{~for: }~ t > t_1 
        			\end{cases}$  
      
        The subsequent line takes the following form:  

        `t1, \omega, A1`

    -   `rising_sine`
        Periodic function with increasing amplitude of the following form:  

        $f(t) = \begin{cases}
        			\frac{A_1}{t_1} \cdot t \cdot \sin(\omega t) & \text{~for: }~ t \leq t_1 \\
        			A_1 \cdot \sin(\omega t) & \text{~for: }~ t > t_1 
        			\end{cases}$  

        The subsequent line takes the following form:  
        `t1, `$\omega$`, A1`

    -   `equally_spaced`
        Choose the equally spaced definition method to give a list of
        amplitude values `vi` at fixed time intervals `dx` beginning at
        a specified value of time. If needed, `numgeo` interpolates
        linearly between these values. The subsequent lines take the
        following form:  
        
        `dx`  
        `v1, v2, ..., v8,`  
        `v9, ...`  

    -   `tabular`
        Choose the tabular definition to define the amplitude curve as a
        table of values at convenient points (e.g. `t1` = 0 s, `v1` = 0,
        `t2` = 1 s, `v2` = 2) on the time scale. If needed, `numgeo`
        interpolates linearly between these values. The subsequent lines
        take the following form:    
        `t1, v1`  
        `t2, v2`  
        `...`  

    -   `user`
        The amplitude is defined in a user-defined file described [here](user/index.md). The user may specify as many
        amplitude parameters in the input file as needed in the user
        file

    -   `lab-cyclic-stress-strain-control`
        An amplitude specially designed for cyclic triaxial tests. For a
        defined element set `<elset>` a signal is generated with
        constant rate `<rate>`. The direction of the signal is reversed
        when target stress `<stress1>` or `<stress2>` is reached in the
        element of `<elset>`. The procedure is continued until `<N>`
        load reversals are performed. This amplitude is best combined
        with a displacement-controlled simulation. The command takes the
        following form:  
        `*Amplitude, name = ..., Type = lab-cyclic-stress-strain-control`  
        `<elset>, <stress component>, <stress1>, <stress2>, <rate>, <N>`
        The following stress components are available:

        -   `s11`: stress in $x_1$ direction, i.e. $\sigma_{11}$

        -   `s22`: stress in $x_2$ direction, i.e. $\sigma_{22}$

        -   `s33`: stress in $x_3$ direction, i.e. $\sigma_{33}$

        -   `s11-s22`: "triaxial" deviatoric stress, i.e.
            $\sigma_{11} - \sigma_{22}$

    -  `lab-triaxial-constant-pressure`
        An amplitude specially designed for axially loaded triaxial
        tests with constant mean effective stress (`<target pressure>`,
        $p=\sigma_{ii}/3$). For a defined element set `<elset>` an
        updated horizontal stress $\sigma_{11}$ is calculated that
        enforces $\dot{p}=0$:    
        $\sigma_{11} = \dfrac{2p^{target}-\sigma_{22,0}}{2}$

        Example:  
        `*Amplitude, name = updated-s11, Type = lab-triaxial-constant-pressure`  
        `<elset>, <target pressure>`  
        Best combined with a distributed surface load, e.g.  
        `*DSload, name = ..., amplitude = updated-s11`  
        `<surface name>, P, 1`
