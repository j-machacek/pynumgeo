# Assign material

```numgeo 
*Assign material, Elset = <element set name>, Material = <material name> [, amgcl = direct]
```

This option links material definitions (and properties) to solid (continuum) elements. `Elset` and `Material` are mandatory. 

* `Elset = <element set name>`. Set this parameter equal to the name of the element set to which the properties are defined.
	
* `Material = <material name>`. Set this parameter equal to the name of the material to be used with these elements. 
	
	The chosen material does not have to be defined previous to the solid section, but within the scope of the "Model definition section". While reading the model definition of the input file, the existence of the assigned material and element set is checked.

* `amgcl = direct` (optional). The elements are a structure which the solver [AMGCL](solver.md#amgcl) solves directly inside its preconditioner (direct set) instead of with the multigrid of the soil. Use it for every element set of a stiff structure of solid elements in contact with the soil (pile, wall), including the parts without a contact surface (pile head, cap); never for the soil. The option has no effect with the other solvers. See [Solver: AMGCL](solver.md#amgcl) for the guideline.

	```numgeo 
	*Assign material, elset=Soil, material=Sand
	*Assign material, elset=Pile, material=Steel, amgcl=direct
	```


!!! note "Do not place within part definition"

    The solid section should be placed outside the part/instance definition.


!!! info "Solid Section"

    Before 08.2025 numgeo used the Abaqus-inherited keyword `*Solid section`:

    ```numgeo 
    *Solid Section, Elset = <element set name>, Material = <material name> 
    ```

    This command has been replaced by `*Assign material`. For backward compatibility, `*Solid section` can still be used, with the same options.
