### Initial state variables 

This subroutine is used to initialize user-defined state variables
(`statev`) at particular material points (integration points),
characterized by the parameter `user` on the `*initial conditions`
command in the input file:
`*initial conditions, type = state variables, user`
### Linux 
```fortran
subroutine user_initial_state_variables(ie,igp,ndim,nstatev,nchar,material, &
             coords,statev) bind(c,name='user_initial_state_variables')
  use, intrinsic :: iso_c_binding
  implicit none
  integer(c_int)                    , intent(in)    :: ie         
  integer(c_int)                    , intent(in)    :: igp         
  integer(c_int)                    , intent(in)    :: ndim         
  integer(c_int)                    , intent(in)    :: nstatev     
  integer(c_int)                    , intent(in)    :: nchar 
  character(c_char)                 , intent(in)    :: material(*) 
  real(c_double), dimension(3)      , intent(in)    :: coords      
  real(c_double), dimension(nstatev), intent(inout) :: statev      

  character(len=nchar) :: material_str
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material(1:nchar), material_str)
  
  ... user coding

end subroutine user_initial_state_variables
```
### Windows 
```fortran
subroutine user_initial_state_variables(ie,igp,ndim,nstatev,nchar,material,coords,statev)
  implicit none
    !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_initial_state_variables
  integer                    , intent(in)    :: ie         
  integer                    , intent(in)    :: igp         
  integer                    , intent(in)    :: ndim         
  integer                    , intent(in)    :: nstatev     
  integer                    , intent(in)    :: nchar 
  character                  , intent(in)    :: material(*) 
  real(8), dimension(3)      , intent(in)    :: coords      
  real(8), dimension(nstatev), intent(inout) :: statev      

  character(len=nchar) :: material_str
  
  ! required to make the material name usable in select case of if-clauses
  material_str = transfer(material(1:nchar), material_str)
  
  ... user coding

end subroutine user_initial_state_variables
```

-   `ie`: Element label (id)

-   `igp`: Integration point number in the element

-   `ndim`: Number of coordinates

-   `nstatev`: Number of solution-dependent state variables (depends on
    the material)

-   `nchar`: length of the material name

-   `material`: Material name assigned to the current element

-   `coords(:)`: Array containing the coordinates of the current
    integration point

-   `statev(:)`: Array containing the solution-dependent state variable
    to be defined