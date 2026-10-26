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
"""Node orders of other conventions (VTK/meshio, gmsh, Abaqus) and the choice of numgeo element types.

**Node permutations.** Each convention is described as published: the corner nodes of its reference element
in its own natural coordinates (VTK: ``[0, 1]`` for lines, quadrilaterals and hexahedra; gmsh and Abaqus:
``[-1, 1]``; all three: the unit simplex for triangles and tetrahedra) and every higher-order node as the
centroid of the corners it lies between (edge, face or volume). These coordinates are mapped onto numgeo's
reference element (:attr:`pynumgeo.mesh.topology.Topology.reference`, read from numgeo's shape functions) and
the permutation is *derived* by matching coordinates, see :func:`to_numgeo`.

Sources of the conventions: VTK cell classes (``vtkQuadraticEdge``, ``vtkQuadraticTriangle``,
``vtkQuadraticQuad``, ``vtkBiQuadraticQuad``, ``vtkQuadraticTetra``, ``vtkQuadraticHexahedron``,
``vtkTriQuadraticHexahedron``: parametric coordinates); gmsh reference manual, section *Node ordering*
(MSH format); Abaqus Analysis User's Guide, node ordering of the beam/truss, continuum and shell element
libraries. ``meshio`` stores every cell in VTK order (its gmsh reader permutes; its Abaqus reader does
*not*, so 3-node lines read from ``.inp`` files are in Abaqus order — use ``convention="abaqus"`` for them).

Result: numgeo's node order equals VTK's for every topology (numgeo writes its connectivity unchanged to
VTK files, ``src/output/VTK_write_cells_.f90:86-104``); gmsh differs for tet10, hex20 and hex27; Abaqus
differs for 3-node lines (mid node second). Abaqus has no 27-node brick in this table.

**Element types.** :func:`numgeo_element_type` selects a library name from the catalogue by topology,
degrees of freedom and variant; it never composes a name.

Examples:
    >>> to_numgeo("gmsh", "tet10").tolist()
    [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]
    >>> to_numgeo("abaqus", "line3").tolist()
    [0, 2, 1]
    >>> permute([[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]], "gmsh", "tet10").tolist()
    [[10, 11, 12, 13, 14, 15, 16, 17, 19, 18]]
    >>> numgeo_element_type("quad8", ["U1", "U2", "PW"], variant=["SAT"], reduced=True)
    'u8p4-sat-red'
"""

from __future__ import annotations

import functools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt

from pynumgeo import catalogue as _cat
from pynumgeo.mesh.mesh import Mesh
from pynumgeo.mesh.topology import TOPOLOGIES, Topology, element_topology, topology

__all__ = [
    "CONVENTIONS",
    "GMSH_ELEMENT_TYPES",
    "MESHIO_TYPES",
    "Convention",
    "ImportedMesh",
    "build_mesh",
    "check_element_type",
    "element_type_candidates",
    "flip_permutation",
    "from_numgeo",
    "meshio_dimension",
    "numgeo_element_type",
    "permute",
    "reference_coordinates",
    "to_numgeo",
    "topology_from_meshio",
]

IntArray = npt.NDArray[np.int64]
FloatArray = npt.NDArray[np.float64]
Convention = Literal["numgeo", "vtk", "meshio", "gmsh", "abaqus"]

#: Conventions known to :func:`to_numgeo` (``meshio`` is VTK's order).
CONVENTIONS: tuple[str, ...] = ("numgeo", "vtk", "meshio", "gmsh", "abaqus")

#: topology -> meshio cell type
MESHIO_TYPES: dict[str, str] = {t.name: t.meshio_type for t in TOPOLOGIES.values()}

#: gmsh element type id (MSH format, ``gmsh.model.mesh.getElements``) -> topology
GMSH_ELEMENT_TYPES: dict[int, str] = {
    1: "line2", 8: "line3", 2: "tri3", 9: "tri6", 3: "quad4", 16: "quad8", 10: "quad9",
    4: "tet4", 11: "tet10", 5: "hex8", 17: "hex20", 12: "hex27",
}  # fmt: skip


# --------------------------------------------------------------------------------------------- layouts
@dataclass(frozen=True)
class _Layout:
    """A published node order: ``vertices`` in native natural coordinates, ``nodes[i]`` = indices (0-based)
    of the vertices whose centroid is node ``i``."""

    frame: Literal["unit", "symmetric", "simplex"]
    vertices: tuple[tuple[float, ...], ...]
    nodes: tuple[tuple[int, ...], ...]


_U_LINE = ((0.0,), (1.0,))
_S_LINE = ((-1.0,), (1.0,))
_SIMPLEX2 = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))
_U_QUAD = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
_S_QUAD = ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
_SIMPLEX3 = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
_U_HEX = tuple((float(x), float(y), float(z)) for z in (0, 1) for (x, y) in ((0, 0), (1, 0), (1, 1), (0, 1)))
_S_HEX = tuple(tuple(2.0 * v - 1.0 for v in p) for p in _U_HEX)


def _v(n: int) -> tuple[tuple[int, ...], ...]:
    return tuple((i,) for i in range(n))


# VTK (and meshio): edges, faces as listed by the VTK cell classes
_VTK_TRI_E = ((0, 1), (1, 2), (2, 0))
_VTK_QUAD_E = ((0, 1), (1, 2), (2, 3), (3, 0))
_VTK_TET_E = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
_VTK_HEX_E = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
_VTK_HEX_F = ((0, 3, 7, 4), (1, 2, 6, 5), (0, 1, 5, 4), (3, 2, 6, 7), (0, 1, 2, 3), (4, 5, 6, 7))
# gmsh: MSH node ordering
_GMSH_TET_E = ((0, 1), (1, 2), (2, 0), (3, 0), (3, 2), (3, 1))
_GMSH_HEX_E = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
_GMSH_HEX_F = ((0, 3, 2, 1), (0, 1, 5, 4), (0, 4, 7, 3), (1, 2, 6, 5), (2, 3, 7, 6), (4, 5, 6, 7))
_ALL8 = (tuple(range(8)),)

_VTK: dict[str, _Layout] = {
    "line2": _Layout("unit", _U_LINE, _v(2)),
    "line3": _Layout("unit", _U_LINE, (*_v(2), (0, 1))),
    "tri3": _Layout("simplex", _SIMPLEX2, _v(3)),
    "tri6": _Layout("simplex", _SIMPLEX2, _v(3) + _VTK_TRI_E),
    "quad4": _Layout("unit", _U_QUAD, _v(4)),
    "quad8": _Layout("unit", _U_QUAD, _v(4) + _VTK_QUAD_E),
    "quad9": _Layout("unit", _U_QUAD, _v(4) + _VTK_QUAD_E + ((0, 1, 2, 3),)),
    "tet4": _Layout("simplex", _SIMPLEX3, _v(4)),
    "tet10": _Layout("simplex", _SIMPLEX3, _v(4) + _VTK_TET_E),
    "hex8": _Layout("unit", _U_HEX, _v(8)),
    "hex20": _Layout("unit", _U_HEX, _v(8) + _VTK_HEX_E),
    "hex27": _Layout("unit", _U_HEX, _v(8) + _VTK_HEX_E + _VTK_HEX_F + _ALL8),
}
_GMSH: dict[str, _Layout] = {
    "line2": _Layout("symmetric", _S_LINE, _v(2)),
    "line3": _Layout("symmetric", _S_LINE, (*_v(2), (0, 1))),
    "tri3": _Layout("simplex", _SIMPLEX2, _v(3)),
    "tri6": _Layout("simplex", _SIMPLEX2, _v(3) + _VTK_TRI_E),
    "quad4": _Layout("symmetric", _S_QUAD, _v(4)),
    "quad8": _Layout("symmetric", _S_QUAD, _v(4) + _VTK_QUAD_E),
    "quad9": _Layout("symmetric", _S_QUAD, _v(4) + _VTK_QUAD_E + ((0, 1, 2, 3),)),
    "tet4": _Layout("simplex", _SIMPLEX3, _v(4)),
    "tet10": _Layout("simplex", _SIMPLEX3, _v(4) + _GMSH_TET_E),
    "hex8": _Layout("symmetric", _S_HEX, _v(8)),
    "hex20": _Layout("symmetric", _S_HEX, _v(8) + _GMSH_HEX_E),
    "hex27": _Layout("symmetric", _S_HEX, _v(8) + _GMSH_HEX_E + _GMSH_HEX_F + _ALL8),
}
# Abaqus: 3-node beams/trusses list the mid node second (B22, B32, T2D3, T3D3); no 27-node brick here.
_ABAQUS: dict[str, _Layout] = {
    "line2": _Layout("symmetric", _S_LINE, _v(2)),
    "line3": _Layout("symmetric", _S_LINE, ((0,), (0, 1), (1,))),
    "tri3": _Layout("simplex", _SIMPLEX2, _v(3)),
    "tri6": _Layout("simplex", _SIMPLEX2, _v(3) + _VTK_TRI_E),
    "quad4": _Layout("symmetric", _S_QUAD, _v(4)),
    "quad8": _Layout("symmetric", _S_QUAD, _v(4) + _VTK_QUAD_E),
    "quad9": _Layout("symmetric", _S_QUAD, _v(4) + _VTK_QUAD_E + ((0, 1, 2, 3),)),
    "tet4": _Layout("simplex", _SIMPLEX3, _v(4)),
    "tet10": _Layout("simplex", _SIMPLEX3, _v(4) + _VTK_TET_E),
    "hex8": _Layout("symmetric", _S_HEX, _v(8)),
    "hex20": _Layout("symmetric", _S_HEX, _v(8) + _VTK_HEX_E),
}
_LAYOUTS: dict[str, dict[str, _Layout]] = {"vtk": _VTK, "meshio": _VTK, "gmsh": _GMSH, "abaqus": _ABAQUS}


def _check_convention(convention: str) -> str:
    c = convention.lower()
    if c not in CONVENTIONS:
        raise KeyError(f"unknown convention {convention!r}; known: {', '.join(CONVENTIONS)}")
    return c


def reference_coordinates(convention: str, topology_name: str) -> FloatArray:
    """Reference coordinates of the nodes of ``convention`` (in its node order), expressed in numgeo's
    natural coordinates (``[-1, 1]`` for lines, quadrilaterals and hexahedra, the unit simplex otherwise).

    >>> reference_coordinates("vtk", "line3").tolist()
    [[-1.0], [1.0], [0.0]]
    """
    c = _check_convention(convention)
    t = topology(topology_name)
    if c == "numgeo":
        return t.reference_array()
    layout = _LAYOUTS[c].get(t.name)
    if layout is None:
        raise KeyError(f"no {t.name} in the {c} convention known to pynumgeo")
    verts = np.array(layout.vertices, dtype=np.float64)
    if layout.frame == "unit":
        verts = 2.0 * verts - 1.0
    return np.array([np.mean(verts[list(idx)], axis=0) for idx in layout.nodes], dtype=np.float64)


def _match(source: FloatArray, target: FloatArray) -> IntArray:
    """``p`` with ``source[p] == target`` (each target node found exactly once in source)."""
    if source.shape != target.shape:
        raise ValueError(f"node counts differ: {source.shape} vs {target.shape}")
    p = np.empty(target.shape[0], dtype=np.int64)
    for j, x in enumerate(target):
        hits = np.flatnonzero(np.all(np.abs(source - x) < 1e-12, axis=1))
        if hits.size != 1:
            raise ValueError(f"node at {x.tolist()} found {hits.size} times")
        p[j] = hits[0]
    if np.unique(p).size != p.size:
        raise ValueError("coordinates do not define a permutation")
    return p


@functools.cache
def _perm(convention: str, topology_name: str) -> tuple[int, ...]:
    src = reference_coordinates(convention, topology_name)
    return tuple(int(i) for i in _match(src, topology(topology_name).reference_array()))


def to_numgeo(convention: str, topology_name: str) -> IntArray:
    """Permutation ``p`` (0-based) with ``numgeo_connectivity = connectivity[:, p]``.

    Derived by matching the reference coordinates of ``convention`` with numgeo's
    (:func:`reference_coordinates`).

    Args:
        convention: ``vtk``, ``meshio`` (= VTK), ``gmsh``, ``abaqus`` or ``numgeo`` (identity).
        topology_name: ``line2`` ... ``hex27``.

    >>> to_numgeo("vtk", "hex27").tolist() == list(range(27))
    True
    """
    return np.array(_perm(_check_convention(convention), topology(topology_name).name), dtype=np.int64)


def from_numgeo(convention: str, topology_name: str) -> IntArray:
    """Inverse of :func:`to_numgeo`: ``connectivity_in_convention = numgeo_connectivity[:, q]``.

    >>> from_numgeo("abaqus", "line3").tolist()
    [0, 2, 1]
    """
    return np.argsort(to_numgeo(convention, topology_name)).astype(np.int64)


def permute(connectivity: npt.ArrayLike, convention: str, topology_name: str) -> IntArray:
    """Connectivity rows given in ``convention`` order, reordered to numgeo order."""
    conn = np.atleast_2d(np.asarray(connectivity, dtype=np.int64))
    t = topology(topology_name)
    if conn.shape[1] != t.nnodes:
        raise ValueError(f"{t.name} has {t.nnodes} nodes, the connectivity has {conn.shape[1]} columns")
    return conn[:, to_numgeo(convention, t.name)]


@functools.cache
def _flip(topology_name: str) -> tuple[int, ...]:
    t = topology(topology_name)
    ref = t.reference_array()
    mirrored = ref.copy()
    if t.dim == 1:
        mirrored[:, 0] = -mirrored[:, 0]
    else:
        mirrored[:, [0, 1]] = mirrored[:, [1, 0]]
    return tuple(int(i) for i in _match(ref, mirrored))


def flip_permutation(topology_name: str) -> IntArray:
    """Permutation (0-based, numgeo order -> numgeo order) that reverses the orientation of an element.

    Obtained by mirroring numgeo's reference element (``xi <-> eta``; lines: ``xi -> -xi``). For the
    surface topologies it equals numgeo's face ``F2`` of the shell elements
    (``src/fem/fem_element_faces.f90:129-138``).

    >>> (flip_permutation("quad8") + 1).tolist()
    [1, 4, 3, 2, 8, 7, 6, 5]
    """
    return np.array(_flip(topology(topology_name).name), dtype=np.int64)


_MESHIO_TO_TOPOLOGY = {v: k for k, v in MESHIO_TYPES.items()}
_MESHIO_DIM = {"vertex": 0, "line": 1, "triangle": 2, "quad": 2, "polygon": 2, "tetra": 3, "hexahedron": 3,
               "wedge": 3, "pyramid": 3}  # fmt: skip


def topology_from_meshio(cell_type: str) -> str:
    """The topology of a meshio cell type (``triangle6`` -> ``tri6``); ``KeyError`` if numgeo has none.

    Topology names are accepted too (``tri6`` -> ``tri6``).
    """
    if cell_type in _MESHIO_TO_TOPOLOGY:
        return _MESHIO_TO_TOPOLOGY[cell_type]
    if cell_type in TOPOLOGIES:
        return cell_type
    raise KeyError(f"numgeo has no element with the node layout of meshio cell type {cell_type!r}")


def meshio_dimension(cell_type: str) -> int:
    """Topological dimension of a meshio cell type (``vertex`` 0 ... ``hexahedron27`` 3)."""
    if cell_type in TOPOLOGIES:
        return topology(cell_type).dim
    stem = cell_type.rstrip("0123456789")
    if stem not in _MESHIO_DIM:
        raise KeyError(f"unknown meshio cell type {cell_type!r}")
    return _MESHIO_DIM[stem]


# --------------------------------------------------------------------------------------------- element types
_NEUTRAL_TOKENS = frozenset({"AX", "RED", "3D"})


def _tokens(name: str) -> tuple[str, frozenset[str]]:
    parts = name.upper().split("-")
    return parts[0], frozenset(parts[1:])


def element_type_candidates(
    topology_name: str,
    dofs: Iterable[str] | None = None,
    *,
    ndim: int | None = None,
    axisymmetric: bool | None = None,
    reduced: bool | None = None,
    variant: Iterable[str] | None = None,
    stem: str | None = None,
    formulation: str | None = None,
    usable_only: bool = True,
) -> list[str]:
    """Library names (upper case, catalogue spelling) that match; ``None`` means "do not filter".

    Args:
        topology_name: ``tri3`` ... ``hex27``.
        dofs: degrees of freedom per node, e.g. ``["U1", "U2", "PW"]`` (compared as a set).
        ndim: model dimension of the element type (2 or 3); default ``max(2, topology dimension)``.
        axisymmetric: the catalogue's ``axisymmetric`` flag (the library value, not the name).
        reduced: name token ``RED`` (reduced integration) present.
        variant: name tokens besides ``AX``, ``RED`` and ``3D`` (e.g. ``["SAT"]``, ``["SAT", "STAB"]``,
            ``["SOLID"]``); compared as a set, ``[]`` means none.
        stem: first part of the name, e.g. ``U6P3`` (separates ``U6P3`` from ``U6P6``).
        formulation: the element routine (``element_UP_saturated``) or a part of the family text.
        usable_only: skip library entries numgeo accepts but has no formulation for.
    """
    t = topology(topology_name)
    want_dim = ndim if ndim is not None else max(2, t.dim)
    want_dofs = None if dofs is None else frozenset(d.upper() for d in dofs)
    want_variant = None if variant is None else frozenset(v.upper() for v in variant)
    out = []
    for e in _cat.load().element_types:
        if (e.shape, e.nnodes) != (t.shape, t.nnodes) or e.ndim != want_dim:
            continue
        if usable_only and not e.usable:
            continue
        if want_dofs is not None and frozenset(d.upper() for d in e.dofs) != want_dofs:
            continue
        if axisymmetric is not None and e.axisymmetric != axisymmetric:
            continue
        e_stem, toks = _tokens(e.name)
        if reduced is not None and ("RED" in toks) != reduced:
            continue
        if want_variant is not None and toks - _NEUTRAL_TOKENS != want_variant:
            continue
        if stem is not None and e_stem != stem.upper():
            continue
        if formulation is not None:
            f = formulation.lower()
            if f != str(e.raw.get("formulation_routine") or "").lower() and f not in e.family.lower():
                continue
        out.append(e.name)
    return out


def numgeo_element_type(
    topology_name: str,
    dofs: Iterable[str],
    *,
    ndim: int | None = None,
    axisymmetric: bool = False,
    reduced: bool = False,
    variant: Iterable[str] | None = None,
    stem: str | None = None,
    formulation: str | None = None,
) -> str:
    """The one numgeo element type (lower case, as pynumgeo writes it) for a topology and formulation.

    Filters the catalogue as :func:`element_type_candidates` does; returns the single match.

    Raises:
        ValueError: if no or more than one library entry matches (the message lists the candidates and the
            tokens that tell them apart).

    Examples:
        >>> numgeo_element_type("tet10", ["U1", "U2", "U3"])
        'u10-solid-3d'
        >>> numgeo_element_type("quad4", ["U1", "U2"], variant=["SOLID"], axisymmetric=True, reduced=True)
        'u4-solid-ax-red'
        >>> numgeo_element_type("tri3", ["U1", "U2", "U3", "R1", "R2", "R3"], ndim=3)
        'u3-shell'
    """
    dofs = list(dofs)
    hits = element_type_candidates(
        topology_name, dofs, ndim=ndim, axisymmetric=axisymmetric, reduced=reduced, variant=variant,
        stem=stem, formulation=formulation,
    )  # fmt: skip
    if len(hits) == 1:
        return hits[0].lower()
    looser = element_type_candidates(topology_name, dofs, ndim=ndim)
    what = (
        f"{topology_name}, dofs {','.join(d.upper() for d in dofs)}, axisymmetric={axisymmetric}, "
        f"reduced={reduced}, variant={None if variant is None else sorted(v.upper() for v in variant)}"
        + (f", stem={stem}" if stem else "")
        + (f", formulation={formulation}" if formulation else "")
    )
    if not hits:
        raise ValueError(
            f"no numgeo element type for {what}; element types with this topology and these dofs: "
            f"{', '.join(n.lower() for n in looser) or 'none'}"
        )
    raise ValueError(
        f"{len(hits)} numgeo element types match {what}: {', '.join(n.lower() for n in hits)}; "
        "give variant= (name tokens) or stem= to choose one"
    )


# --------------------------------------------------------------------------------------------- import helper
@dataclass
class ImportedMesh:
    """A mesh built from another format, with the maps back to the original numbering.

    Attributes:
        mesh: the numgeo mesh (node labels 1..n when built with ``renumber=True``).
        node_ids: original id of numgeo node ``i + 1`` (meshio: point index; FreeCAD: node id).
        element_ids: original id of numgeo element ``j + 1`` in block order (meshio: cell index counted
            over all cell blocks; FreeCAD: element id).
        ignored: cell types left out as lower-dimensional (boundary) cells and how many.
    """

    mesh: Mesh
    node_ids: IntArray
    element_ids: IntArray
    ignored: dict[str, int] = field(default_factory=dict)


@dataclass
class _Block:
    numgeo_type: str
    connectivity: IntArray  # original node ids, numgeo order
    element_ids: IntArray


def _model_dimension(types: Iterable[str]) -> int:
    dims = {t: _cat.element_type(t).ndim for t in types}
    values = set(dims.values())
    if len(values) > 1:
        raise ValueError(f"element types of different model dimension: {dims}")
    return values.pop() if values else 0


def check_element_type(numgeo_type: str, topology_name: str | None = None) -> Topology:
    """The topology of ``numgeo_type``, checked against the topology of the cells it is given to.

    Raises:
        KeyError: if the catalogue has no such element type (the message suggests similar names).
        ValueError: if the type has another topology, or numgeo has no formulation for it.
    """
    t = element_topology(numgeo_type)
    if topology_name is not None and t.name != topology(topology_name).name:
        raise ValueError(f"element type {numgeo_type} is a {t.name} element, the cells are {topology_name}")
    if not _cat.element_type(numgeo_type).usable:
        raise ValueError(f"numgeo accepts {numgeo_type} but has no formulation for it (it stops when used)")
    return t


def build_mesh(
    node_ids: npt.ArrayLike,
    coords: npt.ArrayLike,
    blocks: Sequence[tuple[str, npt.ArrayLike, npt.ArrayLike]],
    *,
    node_sets: Mapping[str, npt.ArrayLike] | None = None,
    element_sets: Mapping[str, npt.ArrayLike] | None = None,
    renumber: bool = True,
    dim: int | None = None,
    ignored: Mapping[str, int] | None = None,
) -> ImportedMesh:
    """Build a :class:`~pynumgeo.mesh.mesh.Mesh` from nodes and element blocks with arbitrary ids.

    Args:
        node_ids: original node ids (unique integers).
        coords: ``(n, 2 or 3)`` coordinates (already scaled to the deck's length unit).
        blocks: ``(numgeo_type, connectivity, element_ids)``; connectivity in **numgeo order** with original
            node ids.
        node_sets: name -> original node ids.
        element_sets: name -> original element ids (of elements in ``blocks``).
        renumber: ``True``: keep only the nodes used by the elements and number nodes 1..n in the order of
            the original ids, elements 1..m in block order (what numgeo needs). ``False``: keep all
            nodes and the original ids as labels (:meth:`Mesh.check` reports what numgeo would reject).
        dim: model dimension (2 or 3); default: the dimension of the element types. For a 2D model a
            third coordinate must be zero (it is dropped; numgeo ignores it with a warning,
            ``read_nodes_.f90:115-121``).
        ignored: passed through to :attr:`ImportedMesh.ignored`.

    Raises:
        ValueError: unknown or unusable element types, a type that does not fit its cells, non-zero third
            coordinates in a 2D model, set members that are not part of the mesh.
    """
    ids = np.asarray(node_ids, dtype=np.int64).reshape(-1)
    xyz = np.atleast_2d(np.asarray(coords, dtype=np.float64))
    if xyz.shape[0] != ids.shape[0]:
        raise ValueError("number of node ids and coordinates differ")
    if np.unique(ids).size != ids.size:
        raise ValueError("node ids are not unique")
    blks: list[_Block] = []
    for numgeo_type, conn, eids in blocks:
        t = check_element_type(numgeo_type)
        c = np.asarray(conn, dtype=np.int64)
        if c.ndim != 2:
            c = c.reshape(-1, t.nnodes)
        if c.shape[1] != t.nnodes:
            raise ValueError(f"{numgeo_type} has {t.nnodes} nodes, the connectivity has {c.shape[1]} columns")
        blks.append(_Block(numgeo_type, c, np.asarray(eids, dtype=np.int64).reshape(-1)))
    model_dim = dim if dim is not None else _model_dimension(b.numgeo_type for b in blks)
    if model_dim not in (2, 3):
        raise ValueError(f"model dimension must be 2 or 3, not {model_dim}")
    if xyz.shape[1] > model_dim:
        extra = xyz[:, model_dim:]
        scale = max(1.0, float(np.max(np.abs(xyz[:, :model_dim]))) if xyz.size else 1.0)
        if extra.size and float(np.max(np.abs(extra))) > 1e-12 * scale:
            raise ValueError(
                f"{model_dim}D element types, but coordinates beyond the first {model_dim} are not zero "
                f"(max {float(np.max(np.abs(extra)))}); move the mesh into the x-y plane first"
            )
        xyz = xyz[:, :model_dim]
    elif xyz.shape[1] < model_dim:
        raise ValueError(f"{model_dim}D element types need {model_dim} coordinates, got {xyz.shape[1]}")

    pos = {int(i): k for k, i in enumerate(ids)}
    all_conn = np.concatenate([b.connectivity.reshape(-1) for b in blks]) if blks else np.zeros(0, np.int64)
    missing = [int(i) for i in np.unique(all_conn) if int(i) not in pos]
    if missing:
        raise ValueError(f"{len(missing)} element nodes are not defined, e.g. {missing[0]}")
    keep = np.unique(all_conn) if renumber else ids  # renumber: used nodes in the order of their ids
    rows = np.array([pos[int(i)] for i in keep], dtype=np.int64)

    m = Mesh()
    if keep.size:
        m.add_nodes(xyz[rows], labels=keep)
    for b in blks:
        m.add_elements(b.numgeo_type, b.connectivity, labels=b.element_ids)
    kept = {int(i) for i in keep}
    for name, members in (node_sets or {}).items():
        mem = np.asarray(members, dtype=np.int64).reshape(-1)
        bad = [int(i) for i in mem if int(i) not in kept]
        if bad:
            raise ValueError(f"node set {name!r}: {len(bad)} nodes are not part of the mesh, e.g. {bad[0]}")
        m.add_nset(name, mem)
    elem_ids = {int(i) for b in blks for i in b.element_ids}
    for name, members in (element_sets or {}).items():
        mem = np.asarray(members, dtype=np.int64).reshape(-1)
        bad = [int(i) for i in mem if int(i) not in elem_ids]
        if bad:
            raise ValueError(f"element set {name!r}: {len(bad)} elements are not part of the mesh, e.g. {bad[0]}")
        m.add_elset(name, mem)
    if renumber:
        m, node_map, elem_map = m.renumbered()
    else:
        node_map, elem_map = m.node_labels.copy(), m.element_labels.copy()
    return ImportedMesh(m, node_map, elem_map, dict(ignored or {}))
