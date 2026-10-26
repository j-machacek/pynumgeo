# Submodel

```numgeo 
*Submodel [, frequency = <frequency of the submodel simulation>]
<list of total time at which a submodel simulation is performed, separated by comma>
``` 

With this option a submodel analysis is performed. A submodel analysis
is an additional simulation using the same model as the original job,
importing the state of the model at the increment the submodel analysis
is performed and eventually updating some state variables as defined by
the user. The submodel analysis requires an input file for the submodel
which has to have the same name as the input file of the simulation
starting the submodel analysis plus the ending `_submodel`. In addition,
a second `numgeo` program name `numgeo_submodel` has to be present in
the calculation folder, which is used to perform the submodel process.
The first line in the *\_submodel* input file has to be:

```numgeo 
*Restart read, step = <step number>, submodel
``` 

The `_submodel` input file performs the steps `<step number + 1>` until
the maximum number of defined steps. The state variables at the end of
the last step are saved and read by the main simulation which initiated
the submodel analysis.

The submodel analysis is either performed with a fixed frequency
` [, frequency = <frequency of the submodel simulation>]` or at a fixed
total time, given as a list below the `*Submodel` statement.