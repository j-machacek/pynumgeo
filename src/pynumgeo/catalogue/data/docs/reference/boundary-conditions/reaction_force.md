# Reaction forces

Reaction forces acting on constrained nodes can be saved at the end of a step and applied in subsequent steps:

* [Save reaction forces](#save-reaction-forces)
* [Apply reaction forces](#apply-reaction-forces)

The table below summarises the possible global directions of the reaction forces.

|Global direction  | Description                        | 
|--------------------|------------------------------------| 
| `1`                |Reaction force in x1-direction        | 
| `2`                |Reaction force in x2-direction        | 
| `3`                |Reaction force in x3-direction        | 
| `w1`               |Fluid reaction force in x1-direction  | 
| `w2`               |Fluid reaction force in x2-direction  | 
| `w3`               |Fluid reaction force in x3-direction  | 

## Save reaction forces

```numgeo 
*Save reaction force
<node set name>, <Global direction>
```

With this option, the reaction forces at the end of the current step are saved in memory and can be used in a subsequent step. The entries of the `<subsequent lines>` are the node-set name `<node set name>` and the global direction `<Global direction {1,2,3}>` for reaction forces of the solid phase, or `<Global direction {w1,w2,w3}>` for reaction forces of the fluid phase if elements discretising fluid displacement are used. A reaction force can be used in a subsequent step only if it was saved for the corresponding set and direction (see [*Reaction force](#apply-reaction-forces)).

## Apply reaction forces

```numgeo 
*Reaction force
<node set name>, <Global direction>
```

With this option, the reaction forces from a previous step are imposed to the specified set. A typical application is the release of a support: the support is omitted in the step, its reaction force of the previous step is applied instead and reduced to zero with a decreasing amplitude (e.g. `*Amplitude, name=Release, type=ramp` with `0.0, 1.0, 1.0, 0.0` and `*Reaction force, amplitude=Release`), see the release of the props in the tutorial [Geogrid-reinforced wall with a propped facing panel](../../tutorial/geosynthetics/propped-panel-wall.md#step-25-release-of-the-props). The entries of the `<subsequent lines>` are the name of the node set `<node set name>`, and the global direction `<Global direction {1,2,3}>` in case of reaction  forces of the solid phase or the global direction `<Global direction {w1,w2,w3}>`  in case of reaction forces of the fluid phase if elements discretising fluid displacement are used. Only if the reaction force was saved for a set and it's direction it can be used. The `<amplitude type>` is mandatory.

