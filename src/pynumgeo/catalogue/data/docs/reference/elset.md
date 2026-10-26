# Elset - Element set definition

```numgeo 
*Elset, name = <element set name> [, generate]
<subsequent lines> 
``` 

This option assigns elements to an element set and makes this set accessible by using its name. The sub-keyword ``name`` is mandatory, whereas ``generate`` is optional. The entries to the ``<subsequent lines>`` depend on the occurrence of ``generate``:

* If ``generate`` is omitted, the ``<subsequent lines>`` take the following form: 
	
	```numgeo 
    <element label i>, ..., <element label n> 
	...
    ```

	Enter a list of elements ``<element label i>`` to be assigned to the set. Up to 16 entries per line are allowed. Repeat this line as often as necessary.
	
* If ``generate`` is active, the subsequent line takes the following form:
	
	```numgeo
    <first element>, <last element>, <increment>
    ```
	
	where ``<first element\>`` and ``<last element>`` are the first and the last node in the set to be generated. ``<increment>`` is the increment in element numbers between the elements in the set. All parameters are mandatory.


Note that only previously defined elements can be assigned to an element set.

Element sets can also be defined by their geometrical position rather than their label. This is done using:

```numgeo 
*Elset, find, elset = <element set name>, [bounding box] 
<subsequent line> 
```

The subsequent line is the coordinate for which the closest existing node is searched if  ``[bounding box]`` is not used. Note that always three coordinates (x,y,z) have to be given if  ``[bounding box]`` is not used. If  ``[bounding box]`` is used, six coordinates (x1,y1,z1,x2,y2,z2) defining two corners of a volume have to be given. All elements for which all nodes are within the volume are added to the element set. 
