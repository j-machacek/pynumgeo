# Two-phase porous solid elements with water displacement and pore water pressure dof (u-p-U elements) 

<p align="center">
  <img src="./assets/elements-upU-sat.jpg" width=55%/><br>
</p>

Similar to the u-p elements, these elements are implemented for simulating the response of a two-phase solid-fluid fully coupled material, based on Biot's theory of porous medium:

* The porous medium is composed of one solid phase (e.g. soil skeleton) and one pore-fluid (e.g. water) and is assumed to be always saturated. 
* Each node has 5 (7 in 3D) degrees of freedom:
    
    - solid displacements $u_1$ and $u_2$ (and $u_3$ in 3D)
    - pore-fluid pressure $p^w$
    - water displacements $w_1$ and $w_2$ (and $w_3$ in 3D)
    
* The prescribed densities are the density of the solid grains $\rho^s$ and the pore fluid $\rho^w$. The density of the continuum $\rho$ is calculated based on the assigned porosity $n$ (or void ratio)

  $$
  \rho = (1-n) \cdot \rho^s + n \cdot \rho^w
  $$ 

## 2D Elements

**Element label**   | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
---|---|---|---|---|---|---                                     
``u6p3u6-sat``        | 2D            | triangle       | 6              | quadratic                    | 3             | (1), (2)          
``u8p4u8-sat``        | 2D            | rectangle      | 8              | quadratic                    | 9             | (1), (2)          
``u8p4u8-sat-red``    | 2D            | rectangle      | 8              | quadratic                    | 4             | (2), (3)          

## Axisymmetric Elements

**Element label**   | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
---|---|---|---|---|---|---                                 
``u6p3u6-sat-ax``     | axisym.       | triangle       | 6              | quadratic                    | 3             | (1), (2)          
``u8p4u8-sat-ax``     | axisym.       | rectangle      | 8              | quadratic                    | 9             | (1), (2)          
``u8p4u8-sat-ax-red`` | axisym.       | rectangle      | 8              | quadratic                    | 4             | (2), (3)          
  
## 3D Elements

**Element label**   | **Dim.** | **Shape** | **Nodes** | **Interpolation Order** | **nIP*** | **Remarks**  
---|---|---|---|---|---|---                                     
``u20p8u20-sat``       | 3D            | brick      | 20             | quadratic                    | 27            | (1), (2), (4)     
``u20p8u20-sat-red``   | 3D            | brick      | 20             | quadratic                    | 8             | (2), (3), (4)         
``u27p8u27-sat``       | 3D            | brick      | 27             | quadratic                    | 27            | (1), (2)          

## Remarks

\*   |  **nIP** = number of integration points
---|---
(1) | Due to the full integration, the element will behave badly for isochoric material behavior. This shortcoming is more pronounced for linear interpolated elements and less pronounced for quadratic interpolated ones.
(2) | Taylor-Hood formulation: The solid and water displacements are interpolated using quadratic shape functions, whereas the pore-fluid pressure $p^w$ is interpolated using linear shape functions. 
(3) | Reduced integration: This element does not suffer from the same locking issues as fully integrated elements. 
(4) | 3D-serendipity elements such as the element are not suitable for contact analysis. The option ``bi-quadratic`` can be used  automatically transform  ``u20p8u20`` to  ``u27p8u27`` elements.

Notice that these elements require the definition of a two-phase material (``*Material,..., Phases=2``), as described in [*Material](../material/index.md).

---
