# Initial conditions, Type=void ratio 
```numgeo 
*Initial conditions, Type=void ratio, default 
<element set>, <ic parameter 1>, ..., <ic parameter n>
```
Specify the initial values of the void ratio at the integration points
of a porous medium element. Use one of the following `options`:

-   `Default`
    Use this option to assign a specific initial void ratio `e0` to all
    members of a given element set. The command line takes the following
    form:

    `*Initial Conditions, Type = void ratio, default`  
    `<element set name>, e0`

-   `Constitutive model`
    Use this option to use the void ratio defined for the constitutive model (if it has the void ratio as state variable). In this case it is required to define also the [Initial conditions, Type=state variables](./state-variables.md)

    `*Initial Conditions, Type = void ratio, constitutive model`  

Note that the initial void ratio defined using the above keyword is not
passed to the mechanical model. The reason for this is, that some (more
advanced) constitutive models sometimes require more complicated
approaches to initialize the void ratio (such as the void ratio
following the Bauer's equation in the hypoplastic model). To initialize
the void ratio in the mechanical model, use the
`*Initial state variables` keyword.