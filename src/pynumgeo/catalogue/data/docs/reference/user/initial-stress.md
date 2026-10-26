### User defined initial stress field

This subroutine is used for user-defined initial stresses, characterized
by the parameter `user` on the `*initial conditions, type=stress, user`
command in the input file. The subroutine is called at the start of the
analysis for each applicable material calculation point in the model and
can be used to define all active initial stress components at material
points as functions of coordinates, element number, integration point
number, etc.

### Linux 
```fortran
subroutine user_initial_stress(ie,igp,ndim,ntens,nchar,material,coords,stress)&
             bind(c,name='user_initial_stress')
  use, intrinsic :: iso_c_binding
  implicit none
  integer(c_int)                  , intent(in)    :: ie         
  integer(c_int)                  , intent(in)    :: igp      
  integer(c_int)                  , intent(in)    :: ndim        
  integer(c_int)                  , intent(in)    :: ntens  
  integer(c_int)                  , intent(in)    :: nchar 
  character(c_char)               , intent(in)    :: material(*) 
  real(c_double), dimension(3)    , intent(in)    :: coords       
  real(c_double), dimension(ntens), intent(inout) :: stress       

  character(len=nchar) :: material_str
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material(1:nchar), material_str)
  
  ... user coding

end subroutine user_initial_stress
```
### Windows 
```fortran
subroutine user_initial_stress(ie,igp,ndim,ntens,nchar,material,coords,stress)
	implicit none
	!DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_initial_stress
  implicit none
  integer                  , intent(in)    :: ie         
  integer                  , intent(in)    :: igp      
  integer                  , intent(in)    :: ndim        
  integer                  , intent(in)    :: ntens  
  integer                  , intent(in)    :: nchar 
  character                , intent(in)    :: material(*) 
  real(8), dimension(3)    , intent(in)    :: coords       
  real(8), dimension(ntens), intent(inout) :: stress       

  character(len=nchar) :: material_str
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material(1:nchar), material_str)
  
  ... user coding

end subroutine user_initial_stress
```

-   `ie`: Element label (id)

-   `igp`: Integration point number in the element

-   `ndim`: Number of coordinates

-   `ntens`: Number of stresses to be defined, which depends on the
    element type.

-   `nchar`: length of the material name

-   `material`: Material name assigned to the current element

-   `coords(:)`: Array containing the coordinates of the current
    integration point

-   `stress(:)`: Array containing the initial stress values to be
    defined