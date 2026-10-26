# Node

```numgeo
*Node
<node label>, <coordinate 1>, <coordinate 2> (, <coordinate 3>)
...
```

This option allows nodes and their coordinates to be defined. The meaning of the sub-keywords is as follows:

* ``node label``: Node number, integer
* ``coordinate i``: Coordinates defining the node. The third coordinate is only required for 3D models.

Consider the following example of four nodes $n_i$ in a two dimensional domain:

<p align="center">
  <img src="./assets/nodes.png" width=30%/><br>
  <em> Definition of nodes </em>
</p>

with the corresponding node definition:

```numgeo
*Node
1, 1.0, 2.0
2, 2.0, 5.0
3, 3.0, 1.0
4, 5.0, 2.5
```