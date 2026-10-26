# Hourglass stiffness:

```numgeo 
*Material, ...
*Hourglass, <Method> = c^HG [, c^fHG]
``` 

Use this command to control the applied artificial stiffness (so called
"Hourglass stiffness") constraining (spurious) hourglass modes
propagating in linear interpolated and reduced integrated elements.
Excitation of these modes may lead to severe mesh distortion, with no
stresses resisting the deformation. In `numgeo` this is done by
modifying the element stiffness matrix $K^e_{IiJj}$ by adding a small
artificial (hourglass) stiffness $K^{HG}_{IiJj}$ to the element that
acts to constrain the hourglass mode [@Belytschko1993; @Belytschko2013]:


$K^e_{IiJj}  = K^{e,1Pt}_{IiJj} + \kappa^{HG} \text{d}\Omega^e \sum^{\alpha} \gamma_{\alpha I} \gamma_{\alpha J} \delta_{ij}$
    

where $K^{e,1Pt}_{IiJj}$ is the conventional element stiffness matrix
evaluated at one integration point (located in the centre of the
element). $\kappa^{HG} > 0$ is a numerical parameter that controls the
stiffness of the hourglass resistance and can be chosen arbitrarily.
However, its magnitude has to be selected such that the parameter avoid
hour-glassing but at the same time does not influence the solution of
the problem. Since the parameter $\kappa^{HG}$ is not a true material
constant, it must be normalized to provide approximately the same degree
of stabilization for any geometry and material properties
[@Belytschko1993]. In `numgeo` two methods for the calculation of
$\kappa^{HG}$ are implemented, namely the `Stiffness` version and the
`Scaling` version:

-   `Method = Stiffness`: For the stiffness
    method, `numgeo` requires the user to prescribe directly the
    stiffness which should be applied prevent hourglass modes:

    $\kappa^{HG} = c^{HG} \frac{\partial N_I}{\partial x_i} \frac{\partial N_I}{\partial x_i}$

    The user should provide `numgeo` with a meaningful value for
    $c^{HG}$, which now represents a stiffness. The choice of $c^{HG}$
    however is not trivial, especially if nonlinear (inelastic)
    materials are modelled.
  
    Example single-phase material:
    `*Hourglass, Stiffness = 1000.`
  
    Example two-phase material:
    `*Hourglass, Stiffness = 1000., 10.`

-   `Method = Scaling` (single-phase material):
    For the scaling method an incremental shear modulus $G^\Delta_{el}$
    of an equivalent linear elastic material is computed based on the
    deviatoric parts of the current stress and strain increments
    $\Delta \sigma_{ij}^* = \Delta \sigma_{ij} - \Delta \sigma_{ii}/3$
    and
    $\Delta \varepsilon_{ij}^* = \Delta \varepsilon_{ij} - \Delta \varepsilon_{ii}/3$,
    respectively:

    $G^\Delta_{el} = \frac{1}{2} \sqrt{ \dfrac{ \frac{1}{2} \sum_{i=1}^3 \sum_{j=1}^3 \Delta \sigma_{ij}^* \Delta \sigma_{ij}^* }{ \frac{1}{2} \sum_{i=1}^3 \sum_{j=1}^3 \Delta\varepsilon_{ij}^* \Delta \varepsilon_{ij}^*}} = \frac{1}{2} \sqrt{ \dfrac{\sum_{i=1}^3 \sum_{j=1}^3 \Delta \sigma_{ij}^* \Delta \sigma_{ij}^* }{\sum_{i=1}^3 \sum_{j=1}^3 \Delta \varepsilon_{ij}^* \Delta \varepsilon_{ij}^*}}$

    The hourglass stiffness $\kappa^{HG}$ is then computed based on the
    following equation:
  - 
    $
        	  \kappa^{HG} = c^{HG} G^\Delta_{el} \frac{\partial N_I}{\partial x_i} \frac{\partial N_I}{\partial x_i}$

    $c^{HG}$ takes here the role of a dimensionless scaling factor for
    the hourglass stiffness. The user has to provide `numgeo` with a
    value for $c^{HG}$.


    Example single-phase material:
    `*Hourglass, Scaling = 0.1`

-   `Method = Scaling` (two-phase material): For a
    two-phase material, an additional hourglass scaling parameter
    $c^{f,HG}$ has to be given by the user. Contrary to the scaling
    parameter associated with the solid phase $c^{HG}$, the scaling
    factor $c^{f,HG}$ is associated with the fluid phase. The fluid
    hourglass stiffness $\kappa^{f,HG}$ is computed based on the bulk
    modulus of the fluid phase $K^f$:

    $\kappa^{f,HG} = c^{f,HG} K^f \frac{\partial N_I}{\partial x_i} \frac{\partial N_I}{\partial x_i}$

    The user has to provide `numgeo` with a value for $c^{f,HG}$.
  
    Example two-phase material:
    `*Hourglass, Scaling = 0.1, 0.01`

If the keyword is not given for a material, no hourglass stiffness is applied to its elements. Elements
with reduced integration then have no resistance against hourglass modes.
