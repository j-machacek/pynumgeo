# Contact

To define the interaction between two or more bodies in numgeo

1. First define [the interaction](./interaction.md) type:

    ```numgeo
    *Interaction, Name=<name>, [user]
    *Normal, Mechanical=<>, [no separation], [stiffness_factor=<>], [non constant], [water-filled gap]
    <Normal contact model properties>
    *Friction, model=<friction model name>, [stiffness_factor=<>]
    <Properties of the friction model>
    ```

2. Use the defined interaction in a [contact pair](./contact-pair.md):

    ```numgeo
    *Contact pair, Interaction=<interaction name>, Discretisation=<Discretisation type> [,Adjust] [, Perturbation] [,General]
    <Slave Surface>, <Master Surface>
    ```

3. Optionally define special [contact options](./contact-options.md):

    ```numgeo
    *Contact options, Name=<interaction name>, [clearance=<normal contact distance>], [ Check Disp = <Fraction of contact length>], [ Check Dist = <Fraction of contact length>]
    ```

The sub-keywords following are given in the following Sections.
