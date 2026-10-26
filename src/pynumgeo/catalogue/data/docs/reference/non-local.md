# Non-local

```numgeo 
*Non-local, elset = <set name, local-len = <local length>, statev = <local length> [, time] [, frequency =<>]
<list of total time at which a non-local smoothing is performed, separated by comma> 
``` 

With this keyword state variables are smoothed spatially. The keyword is defined within a `Step` environment. The user has to make the following definitions:

-   `elset`

    The element set for which the smoothing is performed.

-   `local-len`

    The local-length for which the smoothing is performed. The smoothing accounts for points with an approximate maximum distance of two-times the local-length to the smoothed point.

-   `statev`

    The number of state variable which is smoothed. For the hypoplastic model, for instance, `statev=1` would smooth the void ratio.

The following optional statements can be made:

-   `time`

    The total time at which the smoothing is performed. The time has to be given in the subsequent line with multiple values separated by comma.

-   `frequency`

    The frequency in terms of increments at which a smoothing is performed. No subsequent line exists.

Either `time` or `frequency` has to be defined.