# Restart 

## Restart write

```numgeo
*Restart write [, stress]
```

The `*Restart write` keyword has to be specified in the step environment. The requested output is written at the end of the step in which the keyword is defined.

### Complete restart

```numgeo
*Restart write
```

Without an additional option, the command generates all files required to continue the analysis using the `*Restart read` command described below. For u-T solids, this includes nodal temperatures and increments, integration-point state and the constitutive temperature `TEMP_MAT` of Thermal elasticity. These values are stored in double precision.

### Stress field

```numgeo
*Restart write, stress
```

The `stress` option writes the final committed stress field at all integration points to a binary file. The file is written to

```text
<job name>_restart/stress_step_<step number>.bin
```

For example, step 1 of a job named `mc_equilibrium` creates

```text
mc_equilibrium_restart/stress_step_1.bin
```

A separate file is written for every step containing `*Restart write, stress`. The file can be imported as the initial stress field of another analysis using

```numgeo
*Initial conditions, Type=stress, File=<filename>, Mesh=matching
```

as described in the [initial stress documentation](initial-conditions/stress.md#file).

The stress file contains only the integration-point stress vectors and the information required to verify a matching mesh. It does not contain strains, void ratio, temperatures, constitutive state variables or other material-specific history. It therefore cannot resume a coupled thermal analysis. Consequently, it is not a complete restart file and cannot be read using `*Restart read`.

To write both a complete restart state and a stress field at the end of the same step, specify both commands:

```numgeo
*Restart write
*Restart write, stress
```

---

## Restart read

```numgeo
*Restart read, step = <step number>
```

With this option a restart of a previous calculation is performed. The new analysis starts after the step number specified with `<step number>`. Note that the restart files have to be written beforehand in the specified step using the `*Restart write` command without the `stress` option. The input file specified in the restart analysis has to define the complete database the previous job has used and has to contain the same number of steps the original job had. Technically, the exact same input file can be used again with the addition of the `*Restart read` command. It is also possible to redefine the model (e.g. change material properties). However, the same mesh has to be used.

The restart analysis has to be specified in the command line using `oldjob=<old job name>`, where `<old job name>` is the job name of the analysis the restart is performed for.

!!! note "Temperature and material history"

    A u-T restart requires `_thermal_state_step_<n>.dat` in format `NUMGEO-THERMAL-03`. Keep the node and element layout, geometry, mechanical model, property/state layout and thermal transport data unchanged; the time increment may change. Earlier thermal restart formats must be regenerated.

    The reader checks the saved state before import and rejects missing or truncated records, non-finite values, nonpositive temperatures and inconsistent material/integration-point temperatures.

!!! note "Embedded regions"

