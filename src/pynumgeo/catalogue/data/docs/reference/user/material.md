### User defined material model {#user_material}

This subroutine is used to extend `numgeo` with user-defined
constitutive material models, characterized by `*Mechanical = user`
command in the input file. The header and variable description is given
in the following. Notice, that `numgeo` searches for the file
`user_material.so` (Linux) or `user_material.dll` (Windows) in the current working directory.


### Linux 
```fortran
subroutine user_material(material_name, nchar, ielem ,igp ,istep ,iinc ,ntens ,nprops ,nstatev , &
                         strain ,dstrain ,coords ,time ,dtime ,props ,statev ,stress ,dds_dde) bind(c,name='user_material')
  use, intrinsic :: iso_c_binding
  implicit none
  character(c_char), intent(in) :: material_name (*)
  integer(c_int), intent(in) :: nchar
  integer(c_int), intent(in) :: ielem
  integer(c_int), intent(in) :: igp
  integer(c_int), intent(in) :: istep
  integer(c_int), intent(in) :: iinc
  integer(c_int), intent(in) :: ntens
  integer(c_int), intent(in) :: nprops
  integer(c_int), intent(in) :: nstatev
  real(c_double), dimension(ntens), intent(in) :: strain
  real(c_double), dimension(ntens), intent(in) :: dstrain
  real(c_double), dimension (3), intent(in) :: coords
  real(c_double), intent(in) :: time
  real(c_double), intent(in) :: dtime
  real(c_double), dimension(nprops), intent(in) :: props
  real(c_double), dimension(nstatev), intent(inout) :: statev 
  real(c_double), dimension(ntens), intent(inout) :: stress
  real(c_double), dimension(ntens ,ntens), intent(inout) :: dds_dde
  character(len=nchar) :: material_str
  
  real(c_double) :: E, nu, k1, k2, k3
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material_name(1:nchar), material_str)
  
  E = props(1)
  nu = props(2)
  
  dds_dde = 0.0d0
  
  k1 = nu * E / (1.0d0+nu) / (1.0d0-2.0d0*nu)
  k2 = E / 2.0d0 / (1.0d0+nu)
  k3 = k1 + 2.0d0 * k2
  
  dds_dde(1:3,1:3) = k1
  dds_dde(1,1) = k3
  dds_dde(2,2) = k3
  dds_dde(3,3) = k3
  dds_dde(4,4) = k2
  
  if (ntens == 6) then
    ! 3D case
    dds_dde(5,5) = k2
    dds_dde(6,6) = k2
  end if

  stress = stress + matmul(dds_dde,dstrain)

end subroutine user_material
```
### Windows 
```fortran
subroutine user_material(material_name, nchar, ielem ,igp ,istep ,iinc ,ntens ,nprops ,nstatev , &
                         strain ,dstrain ,coords ,time ,dtime ,props ,statev ,stress ,dds_dde) 
  implicit none
  !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_material
  character, intent(in) :: material_name (*)
  integer, intent(in) :: ielem
  integer, intent(in) :: nchar
  integer, intent(in) :: igp
  integer, intent(in) :: istep
  integer, intent(in) :: iinc
  integer, intent(in) :: ntens
  integer, intent(in) :: nprops
  integer, intent(in) :: nstatev
  real(8), dimension(ntens), intent(in) :: strain
  real(8), dimension(ntens), intent(in) :: dstrain
  real(8), dimension (3), intent(in) :: coords
  real(8), intent(in) :: time
  real(8), intent(in) :: dtime
  real(8), dimension(nprops), intent(in) :: props
  real(8), dimension(nstatev), intent(inout) :: statev 
  real(8), dimension(ntens), intent(inout) :: stress
  real(8), dimension(ntens ,ntens), intent(inout) :: dds_dde
  
  character(len=nchar) :: material_str
  
  real(8) :: E, nu, k1, k2, k3
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material_name(1:nchar), material_str)

  E = props(1)
  nu = props(2)
  
  dds_dde = 0.0d0
  
  k1 = nu * E / (1.0d0+nu) / (1.0d0-2.0d0*nu)
  k2 = E / 2.0d0 / (1.0d0+nu)
  k3 = k1 + 2.0d0 * k2
  
  dds_dde(1:3,1:3) = k1
  dds_dde(1,1) = k3
  dds_dde(2,2) = k3
  dds_dde(3,3) = k3
  dds_dde(4,4) = k2
  
  if (ntens == 6) then
    ! 3D case
    dds_dde(5,5) = k2
    dds_dde(6,6) = k2
  end if

  stress = stress + matmul(dds_dde,dstrain)

end subroutine user_material
```


-   `material_name`: material name

-   `ielem`: Element label (id)

-   `igp`: Integration point number

-   `istep`: Step number

-   `iinc`: Increment number

-   `ntens`: Total number of components of the stress/strain tensor

-   `nprops`: User-defined number of material constants associated with
    this user material.

-   `nstatev`: Number of solution-dependent state variables that are
    associated with this material type

-   `strain`: Total strains at the beginning of the increment (in Voight
    notation $\varepsilon_i$ )

-   `dstrain`: Strain increment (in Voight notation
    $\Delta\varepsilon_i$ )

-   `coords`: An array containing the coordinates of this integration
    point $x_i = \{x_1,x_2,x_3\}$. These are the current coordinates if
    geometric nonlinearity is accounted for during the step. Otherwise,
    the array contains the original coordinates of the point.

-   `time`: Value of step time at the beginning of the current increment

-   `dtime`: Time increment $\Delta t$

-   `props`: User-specified array of material constants associated with
    this user material.

-   `statev`: Solution-dependent state variables that are associated
    with this material type

-   `stress`: Stress tensor passed in as $\sigma_{ij}^{t}$ at the
    beginning of the increment and must be updated to
    $\sigma_{i}^t + \Delta \sigma_{j}$

-   `dds_dde`: Jacobian matrix of the constitutive model
    $\partial \Delta \sigma_{i} / \partial \Delta \varepsilon_{j}$