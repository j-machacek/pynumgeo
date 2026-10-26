# Execute Command 

```numgeo 
*Execute Command [, frequency =<>]
<list of commands to be executed, separated by linebreaks> 
``` 

This keyword is used to execute any arbitrary command via the command
line at the end of a step or with the given frequency (command has to be
defined within the step environment). Note that the command is executed
at the start of an increment (prior to writing output). The command has
to be opened and closed by a \$, e.g. `$python3 setup.py$`.