# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#                                                pynumgeo
#                              Python API for the finite element code numgeo
#                                     Copyright (C) 2026 Jan Machacek
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#
# Author: Jan Machacek
#
# pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
# development of numgeo: new developments in the numgeo source code are taken over into the API, and a
# CI pipeline tests every change.
#
# License: BSD-3-Clause, see LICENSE.
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Mesh container and conversions.

* :mod:`~pynumgeo.mesh.mesh` — the container (:class:`Mesh`);
* :mod:`~pynumgeo.mesh.topology` — node layout, shape functions and faces of numgeo's elements;
* :mod:`~pynumgeo.mesh.convert` — node permutations from VTK/meshio, gmsh, Abaqus; choice of element types;
* :mod:`~pynumgeo.mesh.meshio_adapter`, :mod:`~pynumgeo.mesh.freecad_adapter` — meshio and FreeCAD meshes
  (both optional dependencies, imported when used);
* :mod:`~pynumgeo.mesh.quality` — element orientation (positive Jacobian).
"""

from pynumgeo.mesh.convert import (
    ImportedMesh,
    build_mesh,
    from_numgeo,
    numgeo_element_type,
    permute,
    to_numgeo,
)
from pynumgeo.mesh.freecad_adapter import femmesh_import, mesh_from_femmesh
from pynumgeo.mesh.mesh import ElementBlock, ElementSet, Mesh, NodeSet, Surface
from pynumgeo.mesh.meshio_adapter import mesh_from_meshio, mesh_to_meshio, meshio_import
from pynumgeo.mesh.topology import Topology, element_faces, element_topology, face_connectivity

__all__ = [
    "ElementBlock",
    "ElementSet",
    "ImportedMesh",
    "Mesh",
    "NodeSet",
    "Surface",
    "Topology",
    "build_mesh",
    "element_faces",
    "element_topology",
    "face_connectivity",
    "femmesh_import",
    "from_numgeo",
    "mesh_from_femmesh",
    "mesh_from_meshio",
    "mesh_to_meshio",
    "meshio_import",
    "numgeo_element_type",
    "permute",
    "to_numgeo",
]
