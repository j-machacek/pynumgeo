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
"""A numgeo mesh from a FreeCAD ``Fem::FemMesh`` (FreeCAD is not imported; any object with the API works).

**Node order.** FreeCAD keeps its meshes in SMESH node order, which differs from Abaqus/VTK for volumes
(orientation and quadratic nodes). As in the numgeo-FreeCAD workbench (``numgeo_fc/mesh/meshdata.py:313-341``)
the mesh is taken from FreeCAD's own Abaqus writer, which performs that reordering, and is then permuted
from Abaqus to numgeo order (:mod:`pynumgeo.mesh.convert`; this only changes 3-node lines).

**Assumed FemMesh API** (as used by the workbench, FreeCAD 0.21 and 1.0):

* ``writeABAQUS(filename, 0, False)`` — writes ``*Node`` and ``*Element`` blocks of all elements (edges,
  faces, volumes) with FreeCAD's node and element ids (``numgeo_fc/mesh/meshdata.py:327``);
* optional, for ``groups=True``: ``Groups`` (group ids), ``getGroupName(id)``, ``getGroupElementType(id)``
  (``"Node"``, ``"Edge"``, ``"Face"``, ``"Volume"``) and ``getGroupElements(id)`` (ids of nodes or elements)
  (``numgeo_fc/mesh/sets.py:107-118``).

**Units.** FreeCAD stores lengths in mm; the deck's default unit system is m-kN-kPa. The coordinates are
multiplied by the *required* argument ``length_scale`` (``1e-3`` for mm -> m, ``1.0`` to keep mm); nothing
is converted silently.

Examples:
    >>> mesh = mesh_from_femmesh(fm, {"tet10": "u10-solid-3d"}, length_scale=1e-3)  # doctest: +SKIP
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

import numpy as np

from pynumgeo.mesh.convert import MESHIO_TYPES, ImportedMesh, build_mesh, check_element_type, to_numgeo
from pynumgeo.mesh.mesh import Mesh
from pynumgeo.mesh.topology import TOPOLOGIES

__all__ = ["ABAQUS_TOPOLOGY", "FemMeshLike", "femmesh_import", "mesh_from_femmesh", "read_abaqus_mesh"]


class FemMeshLike(Protocol):
    """The part of FreeCAD's ``Fem::FemMesh`` that pynumgeo uses (groups are optional)."""

    def writeABAQUS(self, filename: str, elemParam: int, groupParam: bool, /) -> None:
        """Write the mesh as an Abaqus input file (``elemParam=0``: all elements)."""


#: Abaqus element types written by FreeCAD (and their usual variants) -> topology.
ABAQUS_TOPOLOGY: dict[str, str] = {
    name: topo
    for topo, names in {
        "line2": "B21 B31 T2D2 T3D2",
        "line3": "B22 B32 T2D3 T3D3",
        "tri3": "S3 S3R CPS3 CPE3 CAX3 M3D3",
        "tri6": "S6 STRI65 CPS6 CPE6 CAX6 M3D6",
        "quad4": "S4 S4R CPS4 CPS4R CPE4 CPE4R CAX4 CAX4R M3D4 M3D4R",
        "quad8": "S8 S8R CPS8 CPS8R CPE8 CPE8R CAX8 CAX8R M3D8 M3D8R",
        "tet4": "C3D4",
        "tet10": "C3D10",
        "hex8": "C3D8 C3D8R",
        "hex20": "C3D20 C3D20R",
    }.items()
    for name in names.split()
}
_NO_COUNTERPART = {"C3D6": "wedge", "C3D15": "wedge", "C3D5": "pyramid", "C3D13": "pyramid"}
_KW = re.compile(r"^\s*\*\s*([A-Za-z ]+?)\s*(,.*)?$")


def _options(rest: str | None) -> dict[str, str]:
    out = {}
    for chunk in (rest or "").split(","):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out[k.strip().upper()] = v.strip()
    return out


def read_abaqus_mesh(
    text: str,
) -> tuple[dict[int, tuple[float, ...]], list[tuple[str, int, list[int]]]]:
    """Nodes and elements of the ``*Node`` / ``*Element`` blocks of an Abaqus input text.

    Returns:
        ``(nodes, elements)``: node id -> coordinates; ``(abaqus_type, element_id, node_ids)`` in file order
        and in Abaqus node order. Other keywords (sets ...) are skipped.

    Raises:
        ValueError: unknown element types, wedges/pyramids (numgeo has none), incomplete element lines.

    >>> nodes, elements = read_abaqus_mesh("*Node\\n1, 0, 0, 0\\n2, 1, 0, 0\\n3, 0.5, 0, 0\\n"
    ...                                    "*Element, type=B32\\n7, 1, 3, 2\\n")
    >>> nodes[3], elements
    ((0.5, 0.0, 0.0), [('B32', 7, [1, 3, 2])])
    """
    nodes: dict[int, tuple[float, ...]] = {}
    elements: list[tuple[str, int, list[int]]] = []
    mode: str | None = None
    etype = ""
    nn = 0
    pending: list[int] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        m = _KW.match(line)
        if m:
            if pending:
                raise ValueError(f"incomplete *Element data line for type {etype}: {pending}")
            kw = m.group(1).replace(" ", "").upper()
            opts = _options(m.group(2))
            mode = None
            if kw == "NODE":
                mode = "node"
            elif kw == "ELEMENT":
                etype = opts.get("TYPE", "").upper()
                if etype in _NO_COUNTERPART:
                    raise ValueError(
                        f"Abaqus element type {etype} ({_NO_COUNTERPART[etype]}): numgeo has no such element"
                    )
                if etype not in ABAQUS_TOPOLOGY:
                    raise ValueError(f"unknown Abaqus element type {etype!r}")
                nn = TOPOLOGIES[ABAQUS_TOPOLOGY[etype]].nnodes
                mode = "element"
            continue
        tokens = [t for t in line.replace(",", " ").split() if t]
        if mode == "node":
            nodes[int(tokens[0])] = tuple(float(t) for t in tokens[1:])
        elif mode == "element":
            pending.extend(int(t) for t in tokens)
            while len(pending) >= nn + 1:
                elements.append((etype, pending[0], pending[1 : nn + 1]))
                pending = pending[nn + 1 :]
    if pending:
        raise ValueError(f"incomplete *Element data line for type {etype}: {pending}")
    return nodes, elements


def _topology_key(key: str) -> str:
    if key in TOPOLOGIES:
        return key
    inverse = {v: k for k, v in MESHIO_TYPES.items()}
    if key in inverse:
        return inverse[key]
    raise KeyError(f"element_types key {key!r} is not a topology ({', '.join(TOPOLOGIES)})")


def _groups(femmesh: Any) -> Iterable[tuple[str, str, list[int]]]:
    for gid in femmesh.Groups:
        yield (
            str(femmesh.getGroupName(gid)),
            str(femmesh.getGroupElementType(gid)),
            [int(e) for e in femmesh.getGroupElements(gid)],
        )


def femmesh_import(
    femmesh: FemMeshLike,
    element_types: Mapping[str, str],
    *,
    length_scale: float,
    renumber: bool = True,
    groups: bool = True,
    dim: int | None = None,
) -> ImportedMesh:
    """Like :func:`mesh_from_femmesh`, also returning the maps to FreeCAD's node and element ids."""
    number = isinstance(length_scale, int | float) and not isinstance(length_scale, bool)
    if not (number and math.isfinite(length_scale) and length_scale > 0):
        raise ValueError(f"length_scale must be a positive number (1e-3 for mm -> m), not {length_scale!r}")
    mapping = {_topology_key(k): v for k, v in element_types.items()}
    for topo_name, numgeo_type in mapping.items():
        check_element_type(numgeo_type, topo_name)
    if not mapping:
        raise ValueError("element_types is empty")
    with tempfile.TemporaryDirectory(prefix="pynumgeo_") as tmp:
        path = os.path.join(tmp, "femmesh.inp")
        femmesh.writeABAQUS(path, 0, False)
        with open(path, encoding="utf-8", errors="replace") as fh:
            nodes, elements = read_abaqus_mesh(fh.read())

    top = max(TOPOLOGIES[t].dim for t in mapping)
    order: list[str] = []
    rows: dict[str, list[list[int]]] = {}
    ids: dict[str, list[int]] = {}
    ignored: dict[str, int] = {}
    element_nodes: dict[int, list[int]] = {}
    for abq, eid, conn in elements:
        topo = ABAQUS_TOPOLOGY[abq]
        element_nodes[eid] = conn
        if topo in mapping:
            numgeo_type = mapping[topo]
            if numgeo_type not in rows:
                order.append(numgeo_type)
                rows[numgeo_type], ids[numgeo_type] = [], []
            rows[numgeo_type].append([conn[p] for p in to_numgeo("abaqus", topo)])
            ids[numgeo_type].append(eid)
        elif TOPOLOGIES[topo].dim < top:
            ignored[abq] = ignored.get(abq, 0) + 1
        else:
            raise ValueError(
                f"FreeCAD element {eid} is a {topo} ({abq}) without a numgeo element type in element_types"
            )
    blocks = [(t, np.array(rows[t], dtype=np.int64), np.array(ids[t], dtype=np.int64)) for t in order]
    imported = {i for t in order for i in ids[t]}

    node_sets: dict[str, list[int]] = {}
    element_sets: dict[str, list[int]] = {}
    if groups:
        if not hasattr(femmesh, "Groups"):
            raise ValueError("this FemMesh has no group API (Groups/getGroupName/...); pass groups=False")
        for name, kind, members in _groups(femmesh):
            if kind.lower() == "node":
                node_sets[name] = sorted(set(node_sets.get(name, [])) | set(members))
                continue
            elems = [e for e in members if e in imported]
            if elems:
                element_sets[name] = element_sets.get(name, []) + elems
            rest = [e for e in members if e not in imported]
            unknown = [e for e in rest if e not in element_nodes]
            if unknown:
                raise ValueError(f"group {name!r}: element {unknown[0]} is not in the mesh written by FreeCAD")
            if rest:
                nds = {n for e in rest for n in element_nodes[e]}
                node_sets[name] = sorted(set(node_sets.get(name, [])) | nds)

    node_ids = np.array(sorted(nodes), dtype=np.int64)
    width = max((len(nodes[int(i)]) for i in node_ids), default=3)
    coords = np.zeros((node_ids.size, width))
    for k, i in enumerate(node_ids):
        c = nodes[int(i)]
        coords[k, : len(c)] = c
    coords *= float(length_scale)
    return build_mesh(
        node_ids,
        coords,
        blocks,
        node_sets=node_sets,
        element_sets=element_sets,
        renumber=renumber,
        dim=dim,
        ignored=ignored,
    )


def mesh_from_femmesh(
    femmesh: FemMeshLike,
    element_types: Mapping[str, str],
    *,
    length_scale: float,
    renumber: bool = True,
    groups: bool = True,
    dim: int | None = None,
) -> Mesh:
    """A numgeo mesh from a FreeCAD ``Fem::FemMesh``.

    Args:
        femmesh: the FemMesh (see the module docstring for the API used).
        element_types: topology (``tri6``, ``tet10`` ...; meshio names are accepted too) -> numgeo element
            type, e.g. ``{"tet10": "u10-solid-3d"}``. Elements of lower dimension than the mapped ones
            (the edges and faces FreeCAD stores with a volume mesh) are left out.
        length_scale: factor applied to FreeCAD's coordinates (mm): ``1e-3`` for a deck in m, ``1.0`` for a
            deck in mm. Required — there is no default unit conversion.
        renumber: nodes 1..n (in the order of FreeCAD's node ids, unused nodes dropped) and elements 1..m in
            block order (default); ``False`` keeps FreeCAD's ids as labels.
        groups: turn FemMesh groups into sets: node groups and the nodes of lower-dimensional groups become
            node sets, groups of mapped elements element sets.
        dim: model dimension; default from the element types. A 2D mesh must lie in the x-y plane (z = 0).

    Raises:
        ValueError: invalid ``length_scale``, unmapped elements of the mesh dimension, wedges/pyramids,
            element types that do not fit the cells, a 2D mesh outside the x-y plane.
    """
    return femmesh_import(
        femmesh, element_types, length_scale=length_scale, renumber=renumber, groups=groups, dim=dim
    ).mesh
