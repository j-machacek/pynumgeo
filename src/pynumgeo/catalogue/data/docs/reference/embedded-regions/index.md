# Embedded regions

```text
*Embedded region, <method>
```

Embedded regions couple guest elements to a continuum host without requiring a conforming mesh.

- [**absorbed**](absorbed.md): perfect kinematic following. Guest degrees of freedom are prescribed from the host interpolation, and the guest elements do not contribute mechanical stiffness.
- [**interaction**](interaction.md): line coupling for trusses or beams. Distributed axial and lateral interface springs are integrated along the guest centreline. The guest elements are bars (`section=bar`, default: anchors, nails and very slender inclusions) or, in two-dimensional models, sheets (`section=sheet`: geotextiles and geogrids).

The option `section` states what the guest elements represent:

| Method | `section` | Guest elements | Model | The guest elements are |
|---|---|---|---|---|
| [`interaction`](interaction.md#bars-sectionbar) | `bar` (default) | truss, beam | 2D, 3D | a bar surrounded by soil: anchor, nail, micro pile |
| [`interaction`](interaction.md#geosynthetic-layers-sectionsheet) | `sheet` | truss, beam | 2D | a layer with soil on its two faces: geotextile, geogrid |

The [Theory Manual](../../theory/embedded-regions/index.md) describes the common host search and the mechanical assumptions of each method.
