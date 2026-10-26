# Step
```numgeo 
*Step, Name = <step name>, inc = <max inc>, [nlgeom, no cut back, maxiter, miniter, scale factor =< >]
<*Procedure>
.
.
.
*End Step
```

In `numgeo` the problem history is divided into separated steps (this concept is being adopted from Abaqus). A step represents any convenient phase of the history, e.g. a static analysis of a load change from one magnitude to another or a transient dynamic analysis of vibratory pile driving.

-   
    ```numgeo 
    Name = <step name>
    ```
    Set this parameter equal to the name of the step. This parameter is mandatory.

-   
```numgeo
inc = <max inc>
```

    This optional keyword is used to define the upper limit to the number of increments in an analysis. The analysis will stop if this maximum is exceeded before the complete solution for the step has been obtained.

-   
```numgeo 
nlgeom
``` 

    Optional keyword to consider non-linear geometrics. It is not available for u-T solid elements. The current configuration is used for the determination of all quantities and integration is carried out in the deformed state. Note that the Zaremba-Jaumann stress rate is used.

    Using this options has important consequences for analyses with interactions. Not using `nlgeom` will assume that there is a limited number of possible nodes that can come into contact. If
    large relative movements of a contact pair take place, this might result in inferior convergence. The user is informed in this case and it is recommend to use  `nlgeom`. However, **numgeo** will check for all contact combinations in this case resulting in much longer computational times. Therefore,  `nlgeom` has to be used with care.

-   
```numgeo 
no cut back
``` 

    Optional keyword to restrict the time increment to be reduced in case of bad or no convergence. This option is not permitted for u-T solid elements, which require converged mechanical and thermal fields. Note that the solution is accepted after the maximum number of allowed iterations, independent of the error.

-   
```numgeo 
maxiter
``` 

    Optional keyword to set the maximum number of iterations before the iteration process breaks and a new try with adjusted time increment is started. The default value is 24.

-   
```numgeo 
miniter
``` 

    Optional keyword to set the minimum number of iterations before convergence is allowed to be achieved and the next increment starts. The default value is 1.

-   
```numgeo 
scale factor =< >
``` 

    Optional keyword to scale the critical time increment in [explicit dynamic analyses](./explicit-dynamic.md). The default value is 1.

-   
```numgeo 
<*Procedure>
``` 

    For each step you choose an analysis procedure. This choice defines the type of analysis to be performed during the step: static stress analysis, transient analysis, etc. The available analysis procedures are listed below and are described in the sections that follow. Only one procedure is allowed per step. Availability depends on the selected element formulation. The u-T solid elements support `Static` and `Transient` procedures.

    |Procedure    | Description                                                                                       
    |-------------| ------------------------------------------------------------------------------------------------- --
    |[`Geostatic`](geostatic.md)  | Verify equilibrium of initial geostatic stress field with applied loads and boundary conditions   
    |[`Static`](./static.md)     | Steady-state mechanical, flow or heat-conduction analysis; inertia effects are neglected
    |[`Transient`](./transient.md)  | Transient flow or heat-conduction analysis; inertia effects are neglected
    |[`Dynamic`](./dynamic.md)    | Is used when linear and nonlinear dynamic response is being studied                            
    |[`Reduction`](./reduction.md)  | Strength reduction analysis, inertia effects are neglected                            

-   
```numgeo 
*End Step
```  
    Is used to end a step (mandatory)
