```numgeo 
*Geostatic
```

This procedure is used as the first step of a geotechnical analysis to
apply gravity (and surface) loads. Ideally, these loads and the
prescribed initial stresses should exactly equilibrate and produce zero
deformations. The procedure is basically identical to the `*Static`
procedure, however, the step is calculated as a "one-increment" step.
This is that neither a step-time nor an incremental approach for the
solution is considered. No following lines are required To prescribe the
initial stress field and initial state variables such as the initial
void ratio, the `*Initial...` commands of the model Section are used.

