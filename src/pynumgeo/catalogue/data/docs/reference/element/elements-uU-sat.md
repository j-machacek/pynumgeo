# Two-phase saturated porous elements with water displacement dof (u-U elements) 

<p align="center">
  <img src="./assets/elements-uU-sat.jpg" width=55%/><br>
</p>

Similar to the u-p elements, these elements are implemented for simulating the response of a two-phase solid-fluid fully coupled material, based on Biot's theory of porous medium:


* The porous medium is composed of one solid phase (e.g. soil skeleton) and one pore-fluid (e.g. water) and is assumed to be always saturated. 
* Each node has 4 (6 in 3D) degrees of freedom:
    
    * solid displacements $u_1$ and $u_2$ (and $u_3$ in 3D)
    * water displacements $w_1$ and $w_2$ (and $w_3$ in 3D)
    
* The prescribed densities are the density of the solid grains $\rho^s$ and the pore fluid $\rho^w$. The density of the continuum $\rho$ is calculated based on the assigned porosity $n$ (or void ratio): 

  $$
  \rho = (1-n) \cdot \rho^s + n \cdot \rho^w
  $$

## 2D Elements

**Element label** | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
	---|---|---|---|---|---|---                    
``u4u4``          | 2D            | rectangle      | 4              | linear                    | 4             | (1)          
``u4u4-red``          | 2D            | rectangle      | 4              | linear                    | 1             |  (2)          
``u8u8``          | 2D            | rectangle      | 8              | quadratic                    | 9             | (1)          
``u8u8-red``          | 2D            | rectangle      | 8              | quadratic                    | 1             |  (2)      

## Axisymmetric Elements

**Element label** | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
	---|---|---|---|---|---|---                       
``u4u4-ax``          | axisym            | rectangle      | 4              | linear                    | 4             | (1)          
``u4u4-ax-red``          | axisym            | rectangle      | 4              | linear                    | 1             |  (2)          
``u8u8-ax``          | axisym            | rectangle      | 8              | quadratic                    | 9             | (1)          
``u8u8-ax-red``          | axisym            | rectangle      | 8              | quadratic                    | 1             |  (2)     

## 3D Elements

**Element label** | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
	---|---|---|---|---|---|---                             
``u8u8-3d``       | 3D            | brick      | 8              | linear                    | 8             | (1)    
``u8u8-3d-red``       | 3D            | brick      | 8             | linear                    | 1             | (2)    
``u20u20``     | 3D            | brick      | 20            | quadratic                    | 27            | (1), (3)         

## Remarks
    
\*   |  **nIP** = number of integration points
---|---
(1) | Due to the full integration, the element will behave badly for isochoric material behavior. This shortcoming is more pronounced for linear interpolated elements and less pronounced for quadratic interpolated ones.
(2) | Reduced integration: This element does not suffer from the same locking issues as fully integrated elements. However, due to the rank deficiency of the element stiffness matrix, hourglass stiffness has to be applied to prevent spurious zero-energy modes. For more information, see [*Material](../material/index.md), [*Hourglass](../material/hourglass.md), and the Theory Manual.
(3) | 3D-serendipity elements such as the element are not suitable for contact analysis. The option ``bi-quadratic``, however, can not be used for ``u20u20`` elements!

For u-U elements it is strongly recommended to use reduced integration.

Notice that these elements require the definition of a two-phase material (``*Material,..., Phases=2``), as described in [*Material](../material/index.md).

---
