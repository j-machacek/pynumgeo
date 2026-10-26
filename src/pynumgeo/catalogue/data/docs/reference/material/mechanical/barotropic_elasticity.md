# Barotropic elasticity: 

This elastic constitutive model accounts for the barotropy (dependence on the mean effective stress) and pyknotropy (dependence on the void ratio) of a material.

## Input syntax

```numgeo 
*Mechanical = Barotropic_Elasticity
E^{ref} (F/A), nu (-), n (-), p^{ref} (F/A)
``` 

### Material parameters

The material parameters for `Barotropic_Elasticity` are:

| Index | Symbol | Unit | Description |
| :---: | :---: | :---: | :--- |
| 1 | $E^{ref}$ | F/A | Reference Young’s modulus. |
| 2 | $\nu$ | - | Poisson’s ratio. |
| 3 | $n$ | - | Barotropic exponent in $f_p=(p/p^{ref})^n$. |
| 4 | $p^{ref}$ | F/A | Reference pressure (internally enforced as $p^{ref}\ge 1$). |

## State variables

* `Void_Ratio`: Void ratio
* `fp`: Barotropy function (output only)
* `fe`: Pyknotropy function (output only)

The void ratio can be initialized in two different ways:

* Using the `*Initial conditions, type = state variables` command in the input file, e.g.

```numgeo 
*Initial conditions, type = state variables
element_set_name, void_ratio, <value>
```

* Using the interface for user-defined initial state variables. In this approach, the vector holding the state variables is filled directly in a fortran subroutine as described in Section User defined state variables. The position of the state variables in the associated vector are as follows: 

* *statev(1)* = $e$

If the void ratio is not initialised ($e \le 10^{-3}$), the pyknotropy dependency is deactivated ($f_e = 1$).

---

<div class="grid cards" markdown>

-   :material-update:{ .lg .middle } __Theory manual__

    ---

    [:octicons-arrow-right-24: The theory behind it](../../../theory/constitutive-models/mechanical-models/barotropic-elasticity.md)

</div>