<!--
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
                                               pynumgeo
                             Python API for the finite element code numgeo
                                    Copyright (C) 2026 Jan Machacek
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~

Author: Jan Machacek

pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
development of numgeo: new developments in the numgeo source code are taken over into the API, and a
CI pipeline tests every change.

License: BSD-3-Clause, see LICENSE.
=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
-->

# Installation

pynumgeo needs Python 3.11 or newer and runs on Windows and Linux. Its only runtime dependencies are
numpy and pydantic 2.

```console
pip install pynumgeo                 # once released on PyPI
pip install "pynumgeo[meshio]"       # + meshio for mesh import/export (Gmsh, VTK, ...)
pip install "pynumgeo[pandas]"       # + pandas for result tables
```

From a checkout of the repository:

```console
pip install -e .
pip install -e ".[docs]"             # to build this documentation: zensical build
```

## The numgeo executable

`ng.run` and `pynumgeo run` look for numgeo in this order:

1. the `executable=` argument (`--exe` on the command line),
2. the environment variable `NUMGEO_EXE`,
3. `numgeo` (Windows: `numgeo.exe`) on the `PATH`.

pynumgeo does not ship numgeo. Reading, writing and validating need no executable.

## Inside FreeCAD

The numgeo FreeCAD workbench uses pynumgeo from FreeCAD's own Python. That Python must be 3.11 or newer,
and numpy and pydantic must be installed into it (numpy usually is). `pynumgeo.mesh.mesh_from_femmesh`
converts a FreeCAD FEM mesh (FreeCAD stores lengths in mm, so it takes a `length_scale`); pynumgeo
itself never imports FreeCAD.

## Environment variables

| variable | used by | meaning |
|---|---|---|
| `NUMGEO_EXE` | `run` | path of the numgeo executable |
| `PYNUMGEO_CATALOGUE` | `catalogue` | path of another catalogue file (the full, non-public catalogue for numgeo developers) |
