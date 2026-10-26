# Initial conditions, Type=stress

```numgeo
*Initial conditions, Type=stress, <option>
<element set>, <ic parameter 1>, ..., <ic parameter n>
```

Specify the initial values of initial stress at the integration points
of an element or element set. Use one of the following
`options`:

-   `Homogeneous`

    use this option to prescribe a homogeneous distribution of initial
    stress for a particular element set. The command line takes the
    following form:

    `*Initial Conditions, Type = stress, Homogeneous`

    `<element set name>, sigma_{xx,0}, sigma_{yy,0}, sigma_{zz,0}`

-   `Geostatic`

    Use this option to assign an elevation-dependent initial stress
    field to all members of a given element set. When a geostatic stress
    is prescribed for a particular element set, the stress in the
    vertical direction $h$ (assumed to be the $z$-direction in 3-D and
    axisymmetric models and the $y$-direction in 2-D models) is assumed
    to vary piecewise linearly with this vertical coordinate. The
    command line takes the following form:

    `*Initial Conditions, Type = stress, Geostatic`

    `<element set name>, h_1, sigma_0(h_1), h_2, sigma_0(h_2), K_{x,0}, K_{y,0}`

    $K_{x,0}$ and $K_{y,0}$ are the lateral stress coefficients.

-   `Full`

    use this option to prescribe each component of the initial
    stress for a particular element set. The command line takes the
    following form:

    `*Initial Conditions, Type = stress, Full`

    `<element set name>, sigma_{xx,0}, sigma_{yy,0}, sigma_{zz,0}, sigma_{xy,0}, sigma_{xz,0}, sigma_{yz,0}`

-   `User`

    Use this option to specify the use of a user defined subroutine to
    define the initial stress field:

    `*Initial Conditions, Type = stress, User`

    The required user routine is described [here](../user/index.md).

<a id="file"></a>

-   `File`

    Use this option to import an integration-point stress field from a
    binary file written by [`*Restart write, stress`](../restart.md#stress-field):

    ```numgeo
    *Initial conditions, Type=stress, File=<filename>, Mesh=matching
    ```

    No data line follows this command. The `Mesh=matching` parameter is
    mandatory and identifies the currently available transfer method.
    Other mesh-transfer methods may be introduced as separate values in
    future versions.

    The source and target meshes have to match exactly. numgeo verifies
    the spatial dimension, node labels and coordinates, element labels,
    element types, connectivity, integration-point layout and stress-vector
    sizes before applying the imported field. A mismatch or a corrupt or
    incomplete file causes the import to be rejected.

    The file stores only the stress vectors. Strains, void ratio,
    constitutive state variables and other material-specific history are
    not transferred. These quantities have to be initialized separately
    when required by the constitutive model used in the target analysis.

    Use lower-case filenames and paths in the input command. For example,
    the stress field written after step 1 of the job `mc_equilibrium` can
    be imported using

    ```numgeo
    *Initial conditions, Type=stress, File=mc_equilibrium_restart/stress_step_1.bin, Mesh=matching
    ```
