### User defined loads {#numgeo:user_load}

This subroutine is used for user-defined distributed loads,
characterized by the parameter `*Dload, user` or `*DSload, user`  command in the input file.
The header and variable description are given in the following. The
coordinates of all nodes of the underlying element are provided via the
interface. However, only the nodes at the element face being load are
assigned a value, even if a value is given to the other nodes of the
element. Notice that `numgeo` searches for the file `user_load.so`  (Linux) or `user_load.dll` (Windows)  in
the current working directory.

### Linux 
```fortran
subroutine user_load(istep,step_time,nnode,ndim,coords,iface,value) &
                    bind(c,name='user_load')
use, intrinsic :: iso_c_binding
implicit none
  integer(c_int)                        , intent(in)    :: istep     
  real(c_double)                        , intent(in)    :: step_time 
  integer(c_int)                        , intent(in)    :: nnode    
  integer(c_int)                        , intent(in)    :: ndim      
  real(c_double), dimension(ndim,nnode) , intent(in)    :: coords    
  integer(c_int)                        , intent(in)    :: iface    
  real(c_double), dimension(nnode)      , intent(inout) :: value     

  ... user coding to define value

  ! For example:

  ! Assign load for each node according to its x-coordinate
  value(1:nnode) = -coords(1,1:nnode)*10.0d0
   
end subroutine user_load
```
### Windows 
```fortran
subroutine user_load(istep,step_time,nnode,ndim,coords,iface,value) 
  implicit none
  !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_load
  integer                        , intent(in)    :: istep     
  real(8)                        , intent(in)    :: step_time 
  integer                        , intent(in)    :: nnode     
  integer                        , intent(in)    :: ndim      
  real(8), dimension(ndim,nnode) , intent(in)    :: coords    
  integer                        , intent(in)    :: iface     
  real(8), dimension(nnode)      , intent(inout) :: value     

  ... user coding to define value

  ! For example:

  ! Assign load for each node according to its x-coordinate
  value(1:nnode) = -coords(1,1:nnode)*10.0d0
   
end subroutine user_load
```

-   `istep`: Step number

-   `step_time`: Step time

-   `nnode`: Number of nodes of the underlying element

-   `ndim`: Number of dimensions

-   `coords(:)`: Coordinates of all nodes of the underlying element

-   `iface`: Face number to which the load is applied

-   `value`: Value of the load for each node of the element
