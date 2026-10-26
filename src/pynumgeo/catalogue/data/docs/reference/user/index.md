# User files

In most cases, the implemented methods accessible via the input keywords
are well suited to define initial fields or boundary conditions.
However, in some cases, greater flexibility is required, e.g. when
facing issues with complex geometries such as slopes with inhomogeneous
material distribution. The user subroutines in `numgeo` allow some parts
of the program to be customized for particular applications, without
changing the source code or recompiling the entire program. Therefore,
for specific tasks well-defined interfaces are put at the disposal of
the user, as depicted in the following picture


<p align="center">
  <img src="./images/numgeo_extension2.png" width=55%/><br>
</p>


These abstract interfaces are based on the intrinsic `iso_c_binding`
module and allow to load external procedure during run-time and access
its (C) address via Fortran pointer. The body of the routine has to be
written by the user. To include user subroutines in an analysis, the use
of external subroutines has to be specified in the input file and the
corresponding shared object (file ending `.so`) for Linux or a Dynamic Link Library (file ending `.dll`) for Windows is placed in the
calculation folder. At the beginning of an analysis, `numgeo` then loads
the external procedure to memory.

To create the dynamic-link library or shared object, shell scripts are available together with the different user routines [here](../../assets/user.zip). These shell scripts are run automatically by `numgeo` at the start of an analysis if the corresponding user routine is specified in the input file, the Fortran file is present in the calculation folder, and the shell script is available in that folder. For example, the shell scripts for `user_initial_state_variables.f90` are:

=== "Windows (user_initial_state_variables.bat)"

	```shell
	ifx -O3 /dll user_initial_state_variables.f90
	```

=== "Linux (user_initial_state_variables.sh)"

	```shell
	#!/bin/bash
	ifort -c -shared -fPIC user_initial_state_variables.f90
	ifort -shared -fPIC user_initial_state_variables.o -o user_initial_state_variables.so
	```
