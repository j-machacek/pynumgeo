# Initial conditions, Type=contact
```numgeo 
*Initial conditions, Type=contact
<interaction name>, <value of void ratio>, <values of the intergranular strain (up to six values)>
```
This command is used to initialize state variables of a constitutive
contact model, where `<interaction name>` is the name of the interaction for which the
initial variables is defined. `<value of void ratio>` is the value of
the initial void ratio assigned to this interaction. Currently, only the
`Hypoplastic` constitutive model requires a definition of the initial
state.