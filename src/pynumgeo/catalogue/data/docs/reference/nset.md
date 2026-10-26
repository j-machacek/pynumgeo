# Nset - Node set definition

```numgeo 
*Nset, name = <node set name> [, generate] 
<subsequent lines> 
``` 


This option assigns nodes to a node set and makes this set accessible by using its name. The sub-keyword ``name`` is mandatory, whereas ``generate`` is optional. The entries to the ``<subsequent lines>`` depend on the occurrence of ``generate``:

* If ``generate`` is omitted, the ``<subsequent lines>`` take the following form: 
	
    ```numgeo
    <node i>, ..., <node n> 
    ...
    ```
    Enter a list of nodes ``<node i>v to be assigned to the set. Up to 16 entries per line are allowed. Repeat this line as often as necessary.
	
* If ``generate`` is active, the ``<subsequent lines>`` takes the following form:
	
    ```numgeo
    <first node>, <last node>, <increment>
    ```
	
    where ``<first node>`` and ``<last node>`` are the first and the last node in the set to be generated. ``<increment>`` is the increment in node numbers between the nodes in the set. All parameters are mandatory.


Note that only previously defined nodes can be assigned to a node set.

Node sets can also be defined by their geometrical position rather than their label. This is done using:

* For individual nodes by:
    ```numgeo
    *Nset, find, nset = <node set name> 
    x1,y1,z1
    ```

    The subsequent line is the coordinate for which the closest existing node is searched. Note that always three coordinates (x1,y1,z1) have to be given. Currently, this keyword only supports the generation of node sets consisting of one node. 

* For multiple nodes found in a rectangle (2D) or hexaeder (3D) by:

    ```numgeo 
    *Nset, find, nset = <node set name>, bounding box
    x1,y1,z1,x2,y2,z2
    ```

    Six coordinates (x1,y1,z1,x2,y2,z2) defining two corners of a volume have to be given. All nodes found within the volume are added to the node set. 

* For multiple nodes found in a circle (2D) or cylinder (3D) by:

    ```numgeo 
    *Nset, find, nset = <node set name>, cylinder
    b1,b2, b3, r[, a1,a2, a3, h]
    ```
    For 2D only the base coordinates and the radius have to be given (b1,b2, b3, r). For 3D the center axis  (a1,a2, a3)  and the height (h) have to the added. All nodes found within the area/volume are added to the node set. The 3D definition is illustrated below. 
    
    <p align="center">
      <img src="./assets/3d_cylinder_illustration.png" width=90%/><br>
      <em> Definition of a node set by means of *nset, find, cylinder in 3D </em>
    </p>