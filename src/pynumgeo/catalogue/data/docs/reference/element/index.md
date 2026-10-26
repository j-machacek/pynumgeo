# Elements

```numgeo
*Element, Type = <element type>, <bi-quadratic>
<element label>, <node 1>, ..., <node n>                          
...
``` 

With this option elements are defined. All sub-keywords except of ``bi-quadratic`` are mandatory. A brief compilation of available element types is also given, for more detailed information the reader is referred to the Theory manual. The sub-keywords are:


* ``Type``: Defines the kind of element which is being defined. The different element types available in numgeo are given in:
     * [Truss elements](./elements-u-truss.md)
     * [Beam elements](./elements-beam.md)
     * [Shell elements](./elements-shell.md)
     * [Solid and porous elements](./elements-u.md) for single-phase solid and porous elements
     * [Solid elements with temperature dof](./elements-ut.md) for coupled displacement-temperature analyses
     * [Two-phase porous solid elements with pore water pressure dof](./elements-up-sat.md) for two-phase porous elements following the u-p approach
     * [Two-phase porous solid elements with water displacement and pore water
      pressure dof](./elements-uU-sat.md) for two-phase porous elements following the u-U approach
     * [Two-phase porous solid elements with water displacement dof](./elements-upU-sat.md) for two-phase porous elements following the u-p-U approach
     * [Three-phase porous solid elements](./elements-up.md) for three-phase porous elements, "reduced formulation" following the u-p approach
     * [Three-phase porous solid elements](./elements-upp.md) for three-phase porous elements following the u-p-p approach

* ``bi-quadratic``: Transforms serendipity elements to full bi-quadratic elements. This keyword is optional.
* ``element label``: Element number
* ``<node 1>, ..., <node n>``: Node numbers forming the element.


Consider the following example of a linear quadrilateral element $e_1$ with four nodes $n_i$ in a two dimensional domain:

<p align="center">
  <img src="./assets/elements.png" width=30%/><br>
</p>

with the corresponding definition:
```numgeo
*Element, Type=u4-solid 
1, 3, 4, 2, 1
```
