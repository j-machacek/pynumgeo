# Absorbed embedded region
```numgeo
*Embedded region, absorbed
<embedded element set>, <embedded node set>, <host element set>
```

Use this option to embed elements from `<embedded element set>` into elements from `<host element set>` such that the embedded elements do **not contribute** to the global stiffness matrix.

The degrees of freedom of the embedded nodes are **fully constrained** using interpolation based on the shape functions of the host elements. As a result, the embedded nodes follow the displacement field of their respective host element location without adding any mechanical resistance.

This approach is suitable for:

- Visualising structural components or inclusions that follow host deformation.
- Embedding markers, inactive reinforcements, or post-processing features.

Details on the implementation are provided in the [Theory Manual](../../theory/embedded-regions/absorbed.md).

!!! note " "
    Only nodes that are geometrically located within the volume or on the surface of host elements are embedded. Nodes located outside the host elements are treated normally: they remain active in the global system and can be subjected to loads and boundary conditions.

!!! warning " "
    Nodes embedded using the `absorbed` method do not contribute to the global system of equations. Their stiffness and internal forces are excluded from assembly. Ensure that this behaviour is appropriate for your modelling intent.

-------

## Syntax

```numgeo
*Embedded region, absorbed
<embedded element set>, <embedded node set>, <host element set>
```

- `<embedded element set>`: Name of the element set to be embedded.
- `<embedded node set>`: Name of the node set whose degrees of freedom are to be constrained.
- `<host element set>`: Name of the host element set into which the embedded elements are placed.

-------

## Example

```numgeo
*Embedded region, absorbed
inclinometer_elements, inclinometer_nodes, soil
```

This command embeds elements in the `inclinometer_elements` set into the `soil` host set. The nodes from `inclinometer_nodes` will follow the deformation of the host elements. The embedded inclinometer will not influence the stiffness or stress field of the system.
