# Material

```numgeo 
*Material, Name = <material name>, Phases = <number of active phases> 
*Density  
<material density 1>, ..., <material density n> 
*Mechanical = <mechanical model>  
<parameter 1>, ... , <parameter n> 
*Hydraulic = <hydraulic model> [, Swr = <residual water saturation>]    
<parameter 1>, ... , <parameter n> 
*Permeability [= isotropic]
<subsequent line>
*Thermal conductivity
<thermal conductivity>
*Specific heat
<specific heat at fixed strain>
*Thermal stabilisation
<stabilisation factor>
*Thermal capacity
<capacity type>
*Hourglass, <method>  
``` 

The `*Material` keyword is used to indicate the start of a material definition. 

*   
    ```numgeo 
    Name = <material name>
    ``` 
    
    Set this parameter equal to the name of the material set to which the properties are defined. This parameter is mandatory.

*   
```numgeo 
Phases = <number of active phases>
``` 
    
    Set this parameter equal to the number of phases (e.g. solid, water and/or air) active in the current material. Note that the number of active phases affects some of the subsequent commands. This parameter is mandatory.

The required sub-keywords depend on the selected element and material model. The principal definitions are:

| Property | Keyword | Section |
|---|---|---|
| Material density | `*Density` | [Density](density.md) |
| Stress-strain response | `*Mechanical` | [Mechanical constitutive models](mechanical/index.md) |
| Retention behaviour | `*Hydraulic` | [Hydraulic constitutive models](hydraulic/index.md) |
| Hydraulic conductivity | `*Permeability` | [Permeability](permeability.md) |
| Thermal conductivity | `*Thermal conductivity` | [Thermal conductivity](thermal-conductivity.md) |
| Specific heat at fixed strain | `*Specific heat` | [Specific heat](specific-heat.md) |
| Temperature-projection factor | `*Thermal stabilisation` | [Thermal stabilisation](thermal-stabilisation.md) |
| Temperature capacity matrix | `*Thermal capacity` | [Thermal capacity](thermal-capacity.md) |

For [u-T solid elements](../element/elements-ut.md), use one material phase and define density, thermal conductivity and specific heat. The latter two properties are required for every u-T element. Select [Thermal elasticity](mechanical/thermal_elasticity.md) for isotropic thermoelastic coupling; its data line contains $E,\nu,\alpha,T_{\rm ref}$. For temperature-independent mechanics, select `Linear_Elasticity` with its usual two parameters or another compatible mechanical model. Conductivity and specific heat do not change the constitutive law.

Further material and section properties are described in the following sections.
