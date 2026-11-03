# Assign material

```numgeo 
*Assign material, Elset = <element set name>, Material = <material name> [, amgcl = direct]
*Assign material, Elset = <element set name>, from-file
<file name>
```

This option links material definitions (and properties) to solid (continuum) elements. `Elset` is mandatory, together with either `Material` (one material for all elements of the set) or `from-file` (the material of each element is read from a point file, see [Materials from a point file](#materials-from-a-point-file)).

* `Elset = <element set name>`. Set this parameter equal to the name of the element set to which the properties are defined.
	
* `Material = <material name>`. Set this parameter equal to the name of the material to be used with these elements. 
	
	The chosen material does not have to be defined previous to the solid section, but within the scope of the "Model definition section". While reading the model definition of the input file, the existence of the assigned material and element set is checked.

* `amgcl = direct` (optional). The elements are a structure which the solver [AMGCL](solver.md#amgcl) solves directly inside its preconditioner (direct set) instead of with the multigrid of the soil. Use it for every element set of a stiff structure of solid elements in contact with the soil (pile, wall), including the parts without a contact surface (pile head, cap); never for the soil. The option has no effect with the other solvers. See [Solver: AMGCL](solver.md#amgcl) for the guideline.

	```numgeo 
	*Assign material, elset=Soil, material=Sand
	*Assign material, elset=Pile, material=Steel, amgcl=direct
	```

* `from-file` (instead of `Material`). Each element of the set receives the material of the point of the file `<file name>` which is nearest to the centroid of the element. The name of the file is given in the line following the keyword.


!!! note "Models with parts"

    In models with parts, place the material assignment inside the part definition, after the element set it refers to.


## Materials from a point file

```numgeo 
*Assign material, elset = <element set name>, from-file
<file name>
```

The option `from-file` assigns spatially varying materials to the elements of one element set, e.g. the soil layers of a ground model, the soil classes of a random field or the result of a geostatistical simulation. The materials are given at points; numgeo assigns to each element the material of the point nearest to the element centroid. The method, its accuracy and the choice of the point spacing are described in the [Theory Manual](../theory/material-assignment.md); the [tutorial](../tutorial/rigid-foundation/heterogeneous-soil.md) shows the complete workflow.

```numgeo 
*Assign material, elset=soil, from-file
ground-model.csv
*Material, name=sand
...
*Material, name=clay
...
```

**File.** The line following the keyword holds the name of the file, relative to the folder in which numgeo is started, or with its full path. As all file names of the input file, it is read in lower case and without blanks; on Linux the name of the file itself has to be in lower case.

**Format.** Every line holds the coordinates and the material of one point, separated by semicolons:

```
x_m;y_m;z_m;mat-name
-22.585;-25.547;0.010;layer-2
-22.585;-25.547;-0.490;layer-1
...
```

* The first line may be a header. It is recognised as a header if none of its first three fields is a number; otherwise it is the first point.
* Each further line holds exactly four fields: the coordinates $x$, $y$, $z$ (length unit of the model) and the name of the material. A semicolon at the end of the line is allowed. The numbers have a decimal point (`0.5`, `5e-1`, `-3.2E+02`); a decimal comma or other separators (`0,5`, `0.5,1.0`) are rejected with an error message that names the line.
* In 2D analyses only $x$ and $y$ are used, but the column $z$ has to be present (any number, e.g. 0).
* Blank lines are skipped. Lines with Windows or Unix line ends and a UTF-8 byte order mark (spreadsheet export) are accepted. Comment lines are not allowed.
* The material names are compared with the names of the `*Material` definitions without regard to upper or lower case and without blanks (`Layer 2` = `layer2` = `LAYER2`).

**Assignment.** The centroid of an element is the arithmetic mean of the coordinates of all its nodes in the input file (initial configuration, global coordinates). The element receives the material of the point with the smallest distance to the centroid ($x$, $y$ in 2D; $x$, $y$, $z$ in 3D). Points with the same distance, apart from round-off (relative difference below $10^{-9}$ of the diagonal of the bounding box of the points), are resolved in favour of the point given first in the file. The result therefore depends neither on the number of threads nor on the order of the search. The material is assigned once, when the input file is read; the points are not interpolated (no averaging between points of different materials).

**Materials.** Every material name that is assigned to at least one element has to be defined with `*Material`; otherwise numgeo stops with an error message listing the undefined names. Names of the file that are assigned to no element (e.g. points outside the model) and are not defined only cause a warning. Materials which do not occur in the file are allowed.

**Log file.** numgeo writes a summary of the assignment to the `.log` file. Check it after every change of the file or of the mesh (example from the [tutorial](../tutorial/rigid-foundation/heterogeneous-soil.md)):

```
   Material assignment nr. 1 from file field-1.csv (element set SOIL)
     Header line: x_m;y_m;z_m;material
     Data points: 12261, material names: 3, elements: 1920 (material of the data point nearest to the element centroid)
       Material                              Points    Elements
       SILT                                    4187         644
       SAND                                    5691         899
       CLAY                                    2383         377
     Distance element centroid - nearest data point: mean =  7.0711E-02, max =  7.0711E-02 (element 1)
     Elements with the centroid outside the bounding box of the data points: 0 (  0.00 %)
     Elapsed time:        0.009 s
```

* A mean or largest distance of the order of the point spacing or smaller is expected. A distance of the order of the model size, or many element centroids outside the bounding box of the points, indicates points in another coordinate system (e.g. a global survey system against a local model system, or a missing coordinate offset) or a file that covers only part of the model.
* The element output [`Mat`](output/field.md#element-output) writes one cell array `Mat:<material name>` per material to the VTK output, with which the assignment can be displayed.

**Speed.** The file is read in one piece and its lines are converted in parallel. The nearest point is found with a kd-tree (search effort of the order of $\log n$ for $n$ points), and the elements are searched in parallel with the threads of the command-line option `ncpus`. The effort grows only slightly faster than linearly with the number of points and elements; the elapsed time is given in the log file.

**Combination with other options.**

* Besides `elset`, only `amgcl = direct` may be given together with `from-file`; `material` is not allowed.
* [`*Initial conditions, type=state variables`](initial-conditions/state-variables.md#element-sets-with-different-materials) (options `default`, `*-data`, `fluctuation` and `user`) and `*Modify` can be used with the set. Since its elements have different materials, the state variable is looked up for the material of each element after the materials have been assigned. The value is set for all elements whose material has a state variable of this name; the elements of the other materials keep their state variables, and the log file names these materials in a warning. If none of the materials of the set has the state variable, numgeo stops with an error message. One statement sets the same value (`default`, `*Modify`) or one field (`*-data`, `fluctuation`) for all materials of the set; values that depend on the material are set with the option `user` (the user subroutine receives the name of the material of each element).
* All other initial conditions (stress, pore pressure, void ratio), loads and outputs refer to the element set and its subsets as usual. [`*Model change`](model-change/material.md) with a new material replaces the materials of all elements of the set.


!!! info "Solid Section"

    Before 08.2025 numgeo used the Abaqus-inherited keyword `*Solid section`:

    ```numgeo 
    *Solid Section, Elset = <element set name>, Material = <material name> 
    ```

    This command has been replaced by `*Assign material`. For backward compatibility, `*Solid section` can still be used, with the same options.
