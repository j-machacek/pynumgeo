# User defined boundary conditions 

This subroutine is used for user-defined boundary values, characterized by the parameter `*UBoundary` command in the input file. The header and variable description is given in the following. Notice that `numgeo` searches for the file `user_boundary_conditions.so` (Linux) or `user_boundary_conditions.dll` (Windows) in the current working directory.

---------

## Linux 
```fortran
subroutine user_boundary_conditions(dof,inode,istep,time,coords,bc_value)&
             bind(c,name='user_boundary_conditions')
  use, intrinsic :: iso_c_binding
  implicit none
  character(kind=c_char,len=2) , intent(in)    :: dof        
  integer(c_int)               , intent(in)    :: inode   
  integer(c_int)               , intent(in)    :: istep    
  real(c_double)               , intent(in)    :: time      
  real(c_double), dimension(3) , intent(in)    :: coords    
  real(c_double), dimension(3) , intent(inout) :: bc_value

  ... user coding

end subroutine user_boundary_conditions
```

--------

## Windows 
```fortran
subroutine user_boundary_conditions(dof,inode,istep,time,coords,bc_value) 
  implicit none
  !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_boundary_conditions
  character(2)         , intent(in)    :: dof          
  integer              , intent(in)    :: inode   
  integer              , intent(in)    :: istep    
  real(8)              , intent(in)    :: time      
  real(8), dimension(3), intent(in)    :: coords    
  real(8), dimension(3), intent(inout) :: bc_value

  ... user coding

end subroutine user_boundary_conditions
```

---------

-   `dof`: Degree of freedom to assign the boundary condition to, e.g.
    `u1` for the displacement in horizontal direction, or `pw` for the
    pore water pressure

-   `inode`: Node label (id)

-   `istep`: Step number

-   `time`: Step time

-   `coords(:)`: Coordinates of the current node

-   `bc_value(:)`: Total value of the prescribed variable at this point. The variable may be displacement, pore water pressure, etc., depending on the degree of freedom constrained. `bc_value(1)` will be passed into the routine as the value defined by any magnitude and/or amplitude specification for the boundary condition or connector motion. If the analysis procedure requires that the time derivatives of prescribed variables be defined (for example, in a dynamic analysis the velocity and acceleration, as well as the value of the variable, are needed), must be given in `bc_value(2)` and in `bc_value(3)`. As outlined in  [UBoundary](../boundary-conditions/Uboundary.md), an optional keyword `<type>` can be used to define time derivatives in the subroutine rather than the actual value of the boundary conditions. For instance, if `type=velocity` is defined, the integrated value (e.g. displacement) is automatically calculated after the call of the subroutine, such that it is not required to define the integrated value (e.g. displacement) within the subroutine. Therefore, when using the optional keyword `type=velocity` , the definition of `bc_value(1)` is obsolete in the subroutine. Likewise, definition of `bc_value(1)` and `bc_value(2)` is obsolete in case `type=acceleration` is used. 