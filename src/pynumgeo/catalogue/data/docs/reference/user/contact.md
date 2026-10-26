### User defined contact properties {#numgeo:user_defined_contact_props}

This subroutine is used for user-defined contact properties,
characterized by the parameter `user` on the `*interaction, user`
command in the input file. The subroutine is called in each calculation
step and has to define the contact properties of the chosen constitutive
contact model.

### Linux 
```fortran
subroutine user_contact_properties(istep,node,slave,nprops,interaction_type,step_time,coords,   &
                                   coords_connected,disp,disp_connected,props) bind(c,name='user_contact_properties')
  use, intrinsic :: iso_c_binding
  implicit none
  integer(c_int)                    , intent(in)    :: istep              
  integer(c_int)                    , intent(in)    :: node               
  logical                           , intent(in)    :: slave              
  integer(c_int)                    , intent(in)    :: nprops             
  character(c_char)                 , intent(in)    :: interaction_type(*)
  real(c_double)                    , intent(in)    :: step_time          
  real(c_double), dimension(3)      , intent(in)    :: coords             
  real(c_double), dimension(3)      , intent(in)    :: coords_connected   
  real(c_double), dimension(3)      , intent(in)    :: disp               
  real(c_double), dimension(3)      , intent(in)    :: disp_connected     
  real(c_double), dimension(nprops) , intent(inout) :: props              

  ! user coding to define the contact properties props
  write(*,*) 'WARNING: user_contact_properties is called without user coding'
  
end subroutine user_contact_properties
```
### Windows 
```fortran
subroutine user_contact_properties(istep,node,slave,nprops,interaction_type,step_time,coords,   &
                                   coords_connected,disp,disp_connected,props) 
  implicit none
    !DEC$ ATTRIBUTES DLLEXPORT, STDCALL, REFERENCE :: user_contact_properties
  integer                    , intent(in)    :: istep              
  integer                    , intent(in)    :: node               
  logical                    , intent(in)    :: slave              
  integer                    , intent(in)    :: nprops             
  character                  , intent(in)    :: interaction_type(*)
  real(8)                    , intent(in)    :: step_time          
  real(8), dimension(3)      , intent(in)    :: coords             
  real(8), dimension(3)      , intent(in)    :: coords_connected   
  real(8), dimension(3)      , intent(in)    :: disp               
  real(8), dimension(3)      , intent(in)    :: disp_connected     
  real(8), dimension(nprops) , intent(inout) :: props              

  ! user coding to define the contact properties props
  !write(*,*) 'WARNING: user_initial_stress is called without user coding'
  props(:) = 0.0d0
  
  
end subroutine user_contact_properties
```


-   `istep`: Step number

-   `node`: Global node label

-   `slave`: True if current node is on the slave surface (always the
    first surface of a contact pair definition). False if current node
    is on the master surface

-   `nprops`: Number of properties to be defined. Depends on the
    constitutive contact model

-   `interaction_type`: Character defining the constitutive contact
    model that was chosen by the user, e.g. 'PENALTY'

-   `coords(:)`: Array containing the (reference) coordinates of the
    current node

-   `coords_connected(:)`: Array containing the (reference) coordinates
    of the node to which the current node is connected

-   `disp(:)`: Array containing the displacement of the current node

-   `disp_connected(:)`: Array containing the displacement of the node
    to which the current node is connected

-   `props(:)`: Properties defined by the user
