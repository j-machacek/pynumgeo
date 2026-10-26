# Single phase elements

<p align="center">
  <img src="./assets/elements-u-solid.jpg" width=80%/><br>
</p>

The single phase solid elements (denoted by the extension ``solid``) are general purpose elements implemented for simulating the response of a solid material. In addition, a set of porous elements (without ``solid``) exists. These elements account for the porosity of a material on the element level, i.e. the density of the material is a function of void ratio and may change during the simulation due to compaction or expansion. The displacements of the solid are discretised at each node. For the practical application this means that:

* **Solid elements** interpret the assigned density as the density of the continuum (for the geotechnical engineer this means, that e.g. the dry density has to be prescribed). The density remains constant throughout the simulation.
* **Porous elements** on the other hand interpret the prescribed density as the density of the solid grains $\rho^s$. The density of the continuum $\rho$ is calculated based on the assigned porosity $n$ (or void ratio) and $\rho^s$:

    $$
    \rho = (1-n) \cdot \rho^s
    $$

    It is obvious that although $\rho^s$ remains constant during the simulation, $\rho$ changes according to volume changes.


## 2D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** | **Remarks**|
|---|---|---|---|---|---|---|
|``u6`` / ``u6-solid``          | 2D            | triangle       | 6              | quadratic      | 3             | (1)
|``u4`` / ``u4-solid``           | 2D            | rectangle      | 4              | linear         | 4             | (1) |              
|``u4-solid-red``               | 2D            | rectangle      | 4              | linear         | 1             | (2)  |             
|``u8`` / ``u8-solid``          | 2D            | rectangle      | 8              | quadratic      | 9             | (1) |              

## Axisymmetric Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** | **Remarks**|
|---|---|---|---|---|---|---|
|``u4-ax`` / ``u4-solid-ax``     | axisym.            | rectangle      | 4              | linear         | 4             | (1)        |       
|``u6-ax`` / ``u6-solid-ax``     | axisym.       | triangle       | 6              | quadratic      | 3             | (1)  |             
|``u8-ax`` / ``u8-solid-ax``     | axisym.       | rectangle      | 8              | quadratic      | 9             | (1)  |             

## 3D Elements

|**Element label** | **Dim.** | **Shape** | **Nodes** | **Order** |**nIP\*** | **Remarks**|
|---|---|---|---|---|---|---|
|``u4-solid-3D``                 | 3D            | tetrahedron    | 4              | linear         | 1             | (1) |    
|``u8-3D`` / ``u8-solid-3D``     | 3D            | brick          | 8              | linear         | 8             | (1) |              
|``u8-solid-3D-red``             | 3D            | brick          | 8              | linear         | 1             | (2) |    
|``u10-solid-3D``                | 3D            | tetrahedron    | 10             | linear         | 4             | (1) |        
|``u20`` / ``u20-solid``         | 3D            | brick          | 20             | quadratic      | 27            | (1), (3)     |     
|``u20-red`` / ``u20-solid-red`` | 3D            | brick          | 20             | quadratic      | 8             | (3)  |             
|``u27`` / ``u27-solid``         | 3D            | brick          | 27             | quadratic      | 27            | (1)    |           

## Remarks
  
\*   |  **nIP** = number of integration points
---|---
(1)   |   Due to the full integration, the element will behave badly for isochoric material behaviour. This shortcoming is more pronounced for linear interpolated elements and less pronounced for quadratic interpolated ones.
(2)   |   Reduced integration: This element does not suffer from the same locking issues as fully integrated elements. However, due to the rank deficiency of the element stiffness matrix, hourglass stiffness has to be applied to prevent spurious zero-energy modes. For more information, see [*Material](../material/index.md) and the Theory Manual.
(3)   |   3D-serendipity elements such as the element are not suitable for contact analyses. The option ``bi-quadratic`` can be used to automatically transform ``u20`` into ``u27`` elements

---
