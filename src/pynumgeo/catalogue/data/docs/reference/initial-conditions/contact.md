# Initial conditions, Type=contact
```numgeo 
*Initial conditions, Type=contact
<interaction name>, <value of void ratio> [, <six values of the intergranular strain>]
```
This command is used to initialize state variables of a constitutive
contact model, where `<interaction name>` is the name of the interaction for which the
initial variables is defined. `<value of void ratio>` is the value of
the initial void ratio assigned to this interaction. The intergranular strain is either omitted or given with all
six components. Currently, only the
`Hypoplastic` constitutive model requires a definition of the initial
state.