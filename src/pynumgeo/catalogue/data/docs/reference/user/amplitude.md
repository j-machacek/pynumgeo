### User defined amplitudes {#numgeo:user_amplitude}

This subroutine is used for user-defined amplitude values, characterized
by the parameter `*Amplitude, type=user` command in the input file. The
header and variable description are given in the following. Notice that
`numgeo` searches for the file `user_amplitude.so` (Linux) or `user_amplitude.dll` (Windows) in the current
working directory.

### Linux 
```fortran
subroutine user_amplitude(time,nprops,props,value) bind(c,name='user_amplitude')
use, intrinsic :: iso_c_binding
  implicit none
  real(c_double)                    , intent(in)    :: time  
  integer(c_int)                    , intent(in)    :: nprops
  real(c_double), dimension(nprops) , intent(in)    :: props 
  real(c_double), dimension(3)      , intent(inout) :: value    
  
  ... user coding

end subroutine user_amplitude
```
### Windows 
```fortran
subroutine user_amplitude(time,nprops,props,value) 
  implicit none
  !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_amplitude
  real(8)                    , intent(in)    :: time                !! current step time 
  integer                    , intent(in)    :: nprops              !! number of user specified properties
  real(8), dimension(nprops) , intent(in)    :: props               !! properties of this amplitude
  real(8), dimension(3)      , intent(inout) :: value               !! value of this amplitude     

... user coding

end subroutine user_amplitude
```

-   `time`: Step time

-   `nprops`: Number of properties defined in the input file

-   `props(:)`: Properties defined in the input file

-   `value(:)`: Total value of the amplitude at the given time. If the
    analysis procedure requires that the time derivatives of prescribed
    variables be defined (for example, in a dynamic analysis the
    velocity and acceleration, as well as the value of the variable, are
    needed), must be given in `bc_value(2)` and in `bc_value(3)`.
