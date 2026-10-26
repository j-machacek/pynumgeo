# Fluid interaction

```numgeo
*Fluid interaction, Name=<name>, Mechanical=<>, [no separation]
<Normal contact model properties>
```
This option defines a fluid interaction for contact analyses with elements having a water displacement degree of freedom, e.g. `U8U8` elements. The command is followed by two mandatory keywords and one optional keyword:

- `Name=<>` of the (solid) interaction to which this fluid interaction belongs. The interaction has to be defined beforehand. This parameter is mandatory. Currently, a surface interaction for the fluid alone is not allowed.

- `Mechanical = <>`Set this parameter equal to the mechanical model chose to describe the contact behaviour of the fluid. The following mechanical models are available:

    |Model     |Contact tension possible         | Over-closure relation   
    |--------- |-------------------------------- | ----------------------- --
    |Penalty   |no, yes with [no separation]     | linear                  

    The definition of the penalty factor in case the penalty contact model is chosen, however, is not mandatory. If no value is given, the penalty factor will be calculated based on the bulk modulus of the fluid automatically.

- The optional `[no separation]` keyword allows for inseparable contact conditions for the fluid phase. Therefore, tension contact conditions are possible. Note that the contact points have to come into contact once before the no separation conditions comes into effect.

<NOT NECESSARY, OR??: The same properties as for the solid interaction given in Section Interaction have to be defined> 