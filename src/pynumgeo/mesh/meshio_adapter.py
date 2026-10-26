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
"""Conversion between :class:`~pynumgeo.mesh.mesh.Mesh` and ``meshio.Mesh`` (meshio is optional).

meshio reads gmsh, VTK/VTU, Abaqus, XDMF, Exodus ... files; its cells are in VTK node order (its gmsh reader
permutes, see :mod:`pynumgeo.mesh.convert`). The Abaqus reader of meshio does not reorder 3-node lines, so
for meshes read from ``.inp`` files pass ``convention="abaqus"``.

What is converted (``mesh_from_meshio``):

* cell blocks whose type is a key of ``element_types`` become element blocks of the given numgeo type;
* cell blocks of a *lower* dimension than the mapped ones (boundary lines/faces, vertices of a gmsh mesh)
  are left out; their cell sets become node sets (the nodes of the cells), so physical groups on
  boundaries can be used for boundary conditions. An unmapped block of the mesh dimension is an error;
* ``cell_sets`` of mapped cells become element sets, ``point_sets`` become node sets; meshio's own
  entries (names starting with ``gmsh:``) are skipped;
* with ``renumber=True`` (default) nodes not used by an element are dropped and nodes are labelled 1..n in
  point order, elements 1..m in block order — numgeo uses node labels as positions.

Example (needs meshio):
    >>> import meshio  # doctest: +SKIP
    >>> m = meshio.read("model.msh")  # doctest: +SKIP
    >>> mesh = mesh_from_meshio(m, {"triangle6": "u6p3-sat"})  # doctest: +SKIP
"""

from __future__ import annotations

import importlib
import warnings
from collections.abc import Mapping
from typing import Any

import numpy as np

from pynumgeo.mesh.convert import (
    MESHIO_TYPES,
    ImportedMesh,
    build_mesh,
    check_element_type,
    from_numgeo,
    meshio_dimension,
    to_numgeo,
    topology_from_meshio,
)
from pynumgeo.mesh.mesh import ElementSet, Mesh, NodeSet
from pynumgeo.mesh.topology import element_topology

__all__ = ["mesh_from_meshio", "mesh_to_meshio", "meshio_import"]


def _meshio() -> Any:
    try:
        return importlib.import_module("meshio")
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError("meshio is not installed: pip install meshio (or pynumgeo[meshio])") from exc


def _cell_blocks(m: Any) -> list[tuple[str, np.ndarray[Any, Any]]]:
    return [(str(c.type), np.asarray(c.data, dtype=np.int64)) for c in m.cells]


def meshio_import(
    m: Any,
    element_types: Mapping[str, str],
    *,
    renumber: bool = True,
    convention: str = "vtk",
    dim: int | None = None,
) -> ImportedMesh:
    """Like :func:`mesh_from_meshio`, also returning the maps to the meshio numbering.

    ``ImportedMesh.node_ids[i]`` is the meshio point index of numgeo node ``i + 1``;
    ``ImportedMesh.element_ids[j]`` the index of the cell counted over all cell blocks.
    """
    mapping: dict[str, str] = {}
    for key, numgeo_type in element_types.items():
        ctype = MESHIO_TYPES.get(key, key)  # accept topology names as keys too
        check_element_type(numgeo_type, topology_from_meshio(ctype))
        mapping[ctype] = numgeo_type
    blocks = _cell_blocks(m)
    unknown = sorted(set(mapping) - {t for t, _ in blocks})
    if unknown:
        raise ValueError(f"cell types {unknown} are not in the mesh (it has {sorted({t for t, _ in blocks})})")
    if not mapping:
        raise ValueError("element_types is empty")
    top = max(meshio_dimension(t) for t in mapping)
    numgeo_blocks: list[tuple[str, np.ndarray[Any, Any], np.ndarray[Any, Any]]] = []
    ignored: dict[str, int] = {}
    offsets = np.cumsum([0] + [d.shape[0] for _, d in blocks])
    for k, (ctype, data) in enumerate(blocks):
        if ctype in mapping:
            topo = topology_from_meshio(ctype)
            conn = data[:, to_numgeo(convention, topo)] + 1  # label = point index + 1
            eids = np.arange(offsets[k], offsets[k + 1], dtype=np.int64) + 1
            if numgeo_blocks and numgeo_blocks[-1][0] == mapping[ctype]:  # e.g. one gmsh block per entity
                prev_type, prev_conn, prev_ids = numgeo_blocks[-1]
                numgeo_blocks[-1] = (
                    prev_type,
                    np.vstack([prev_conn, conn]),
                    np.concatenate([prev_ids, eids]),
                )
            else:
                numgeo_blocks.append((mapping[ctype], conn, eids))
        elif meshio_dimension(ctype) < top:
            ignored[ctype] = ignored.get(ctype, 0) + int(data.shape[0])
        else:
            raise ValueError(
                f"cell type {ctype!r} ({data.shape[0]} cells) has no numgeo element type in element_types; "
                "map it or remove the cells (only lower-dimensional cells are left out)"
            )

    node_sets: dict[str, np.ndarray[Any, Any]] = {}
    for name, members in (getattr(m, "point_sets", None) or {}).items():
        node_sets[str(name)] = np.asarray(members, dtype=np.int64).reshape(-1) + 1
    element_sets: dict[str, np.ndarray[Any, Any]] = {}
    for name, per_block in (getattr(m, "cell_sets", None) or {}).items():
        name = str(name)
        if name.startswith("gmsh:"):
            continue
        elems: list[np.ndarray[Any, Any]] = []
        nodes: list[np.ndarray[Any, Any]] = []
        for k, members in enumerate(per_block):
            if members is None or k >= len(blocks):
                continue
            idx = np.asarray(members, dtype=np.int64).reshape(-1)
            if idx.size == 0:
                continue
            ctype, data = blocks[k]
            if ctype in mapping:
                elems.append(idx + offsets[k] + 1)
            else:
                nodes.append(np.unique(data[idx]) + 1)
        if elems:
            element_sets[name] = np.concatenate(elems)
        if nodes:
            members_n = np.unique(np.concatenate(nodes))
            if name in node_sets:
                members_n = np.unique(np.concatenate([node_sets[name], members_n]))
            node_sets[name] = members_n

    points = np.asarray(m.points, dtype=np.float64)
    imp = build_mesh(
        np.arange(1, points.shape[0] + 1, dtype=np.int64),
        points,
        numgeo_blocks,
        node_sets=node_sets,
        element_sets=element_sets,
        renumber=renumber,
        dim=dim,
        ignored=ignored,
    )
    imp.node_ids = imp.node_ids - 1  # back to meshio's 0-based indices
    imp.element_ids = imp.element_ids - 1
    return imp


def mesh_from_meshio(
    m: Any,
    element_types: Mapping[str, str],
    *,
    renumber: bool = True,
    convention: str = "vtk",
    dim: int | None = None,
) -> Mesh:
    """A numgeo mesh from a ``meshio.Mesh``.

    Args:
        m: the meshio mesh (anything with ``points``, ``cells`` (``type``, ``data``), optional
            ``point_sets`` and ``cell_sets``).
        element_types: meshio cell type (or pynumgeo topology name) -> numgeo element type, e.g.
            ``{"triangle6": "u6p3-sat"}``; see :func:`pynumgeo.mesh.convert.numgeo_element_type`.
        renumber: drop unused points and label nodes 1..n / elements 1..m (default). With ``False`` every
            point is kept with label ``index + 1`` and elements are labelled ``cell index + 1``.
        convention: node order of the cells: ``vtk`` (meshio's own, default) or ``abaqus`` (meshio's Abaqus
            reader keeps Abaqus order) or ``gmsh`` (raw gmsh order).
        dim: model dimension; default from the element types. 2D models drop a zero third coordinate.

    Raises:
        ValueError: see :func:`pynumgeo.mesh.convert.build_mesh`; also for unmapped cells of the mesh
            dimension.
    """
    return meshio_import(m, element_types, renumber=renumber, convention=convention, dim=dim).mesh


def _expand(s: NodeSet | ElementSet) -> np.ndarray[Any, Any] | None:
    if s.kind == "list":
        return s.members
    if s.kind == "generate" and len(s.values) >= 2:
        first, last = int(s.values[0]), int(s.values[1])
        inc = int(s.values[2]) if len(s.values) > 2 else 1
        return np.arange(first, last + 1, inc, dtype=np.int64)
    return None


def mesh_to_meshio(mesh: Mesh) -> Any:
    """A ``meshio.Mesh`` (VTK node order) from a numgeo mesh, e.g. to write VTU/XDMF for inspection.

    Node sets become ``point_sets`` and element sets ``cell_sets`` (list and ``generate`` sets; sets that
    numgeo evaluates itself — ``find``, ``boundingbox``, ``cylinder`` — cannot be represented and are left
    out with a warning). ``cell_data["numgeo:label"]`` holds the element labels. Surfaces are not converted.

    Raises:
        KeyError: for an element type that is not in the catalogue.
    """
    meshio = _meshio()
    node_pos = {int(lab): k for k, lab in enumerate(mesh.node_labels)}
    cells = []
    labels = []
    block_of: dict[int, tuple[int, int]] = {}
    for bi, b in enumerate(mesh.blocks):
        topo = element_topology(b.type)
        if b.connectivity.shape[1] != topo.nnodes:
            raise ValueError(f"block {bi} ({b.type}) has {b.connectivity.shape[1]} nodes per element")
        idx = np.vectorize(lambda x: node_pos[int(x)], otypes=[np.int64])(b.connectivity)
        cells.append((topo.meshio_type, idx[:, from_numgeo("vtk", topo.name)]))
        labels.append(b.labels.copy())
        for row, lab in enumerate(b.labels):
            block_of[int(lab)] = (bi, row)
    point_sets = {}
    for s in mesh.nsets:
        mem = _expand(s)
        if mem is None:
            warnings.warn(f"node set {s.name} ({s.kind}) is evaluated by numgeo; left out", stacklevel=2)
            continue
        point_sets[s.name] = np.array([node_pos[int(x)] for x in mem], dtype=np.int64)
    cell_sets = {}
    for e in mesh.elsets:
        mem = _expand(e)
        if mem is None:
            warnings.warn(f"element set {e.name} ({e.kind}) is evaluated by numgeo; left out", stacklevel=2)
            continue
        per_block: list[list[int]] = [[] for _ in mesh.blocks]
        for x in mem:
            bi, row = block_of[int(x)]
            per_block[bi].append(row)
        cell_sets[e.name] = [np.array(r, dtype=np.int64) for r in per_block]
    return meshio.Mesh(
        mesh.coords.copy(),
        cells,
        cell_data={"numgeo:label": labels},
        point_sets=point_sets,
        cell_sets=cell_sets,
    )
