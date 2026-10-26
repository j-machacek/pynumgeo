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
"""Element topologies of numgeo: node layout, reference coordinates, shape functions and faces.

Every numgeo element type (catalogue ``element_types``) has a *shape* (``beam``, ``triangular``,
``rectangular``, ``tetrahedral``, ``hexahedral``) and a number of nodes; together they fix the node layout,
which is the same for all formulations. The layout is read from numgeo's shape functions
(``src/fem/fem_shape_functions.f90``, routine ``shape_function``, lines 52-384): node *i* sits where
``N(i) = 1`` and all other ``N(j) = 0``. Shell elements use the same numbering
(``src/elements/element_shell_.f90:534-588``, ``shell_shape_functions``).

=========  ===========  =====  ==================================================================
topology   shape        nodes  numgeo node order (reference coordinates, see :attr:`Topology.reference`)
=========  ===========  =====  ==================================================================
line2      beam         2      ends 1 (xi=-1), 2 (xi=+1)
line3      beam         3      ends 1, 2; node 3 = mid node (``1---3---2``)
tri3       triangular   3      corners (0,0), (1,0), (0,1)
tri6       triangular   6      corners; 4 (1-2), 5 (2-3), 6 (3-1)
quad4      rectangular  4      corners counter-clockwise from (-1,-1)
quad8      rectangular  8      corners; 5 (1-2), 6 (2-3), 7 (3-4), 8 (4-1)
quad9      rectangular  9      as quad8, 9 = centre
tet4       tetrahedral  4      (0,0,0), (1,0,0), (0,1,0), (0,0,1)
tet10      tetrahedral  10     corners; 5 (1-2), 6 (2-3), 7 (3-1), 8 (1-4), 9 (2-4), 10 (3-4)
hex8       hexahedral   8      1-4 bottom (zeta=-1) counter-clockwise, 5-8 top
hex20      hexahedral   20     corners; 9-12 bottom edges, 13-16 top edges, 17-20 vertical edges
hex27      hexahedral   27     as hex20; face centres 21 (xi=-1), 22 (xi=+1), 23 (eta=-1),
                               24 (eta=+1), 25 (zeta=-1), 26 (zeta=+1); 27 = centre
=========  ===========  =====  ==================================================================

Faces (``F1``, ``F2``, ...; ``S1`` ... are accepted by numgeo as synonyms) are numgeo's
``element_face_nodes`` tables (``src/fem/fem_element_faces.f90:60-247``), read from the catalogue section
``model/surface_faces``. Face numbers and local node numbers are 1-based as in numgeo.

Examples:
    >>> t = element_topology("u8p4-sat")
    >>> t.name, t.corners, t.edges[0]
    ('quad8', (1, 2, 3, 4), (1, 2, 5))
    >>> element_faces("u8p4-sat").nodes("F2")
    (2, 3, 6)
    >>> face_connectivity("u4-solid", [[11, 12, 13, 14]], "S4").tolist()
    [[14, 11]]
"""

from __future__ import annotations

import functools
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from pynumgeo import catalogue as _cat

__all__ = [
    "TOPOLOGIES",
    "FaceTable",
    "Topology",
    "element_faces",
    "element_topology",
    "face_connectivity",
    "face_number",
    "face_table",
    "face_tables",
    "topology",
    "topology_of_shape",
]

IntArray = npt.NDArray[np.int64]
FloatArray = npt.NDArray[np.float64]
_Num = Any  # float or complex (the shape functions are also evaluated with complex arguments)

_SF = "src/fem/fem_shape_functions.f90"


# ------------------------------------------------------------------------------------------ shape functions
# Transcribed from src/fem/fem_shape_functions.f90 (routine shape_function); the line numbers are given per
# topology below. The functions accept complex arguments: derivatives are computed by the complex step.


def _n_line2(x: Sequence[_Num]) -> list[_Num]:
    xi = x[0]
    return [(1.0 - xi) / 2.0, (1.0 + xi) / 2.0]


def _n_line3(x: Sequence[_Num]) -> list[_Num]:
    xi = x[0]
    return [xi * (xi - 1.0) / 2.0, xi * (xi + 1.0) / 2.0, 1.0 - xi * xi]


def _n_tri3(x: Sequence[_Num]) -> list[_Num]:
    return [1.0 - x[0] - x[1], x[0], x[1]]


def _n_tri6(x: Sequence[_Num]) -> list[_Num]:
    a, b = x[0], x[1]
    return [
        2.0 * (0.5 - a - b) * (1.0 - a - b),
        2.0 * a * (a - 0.5),
        2.0 * b * (b - 0.5),
        4.0 * a * (1.0 - a - b),
        4.0 * a * b,
        4.0 * b * (1.0 - a - b),
    ]


def _n_quad4(x: Sequence[_Num]) -> list[_Num]:
    a, b = x[0], x[1]
    return [
        0.25 * (1.0 - a) * (1.0 - b),
        0.25 * (1.0 + a) * (1.0 - b),
        0.25 * (1.0 + a) * (1.0 + b),
        0.25 * (1.0 - a) * (1.0 + b),
    ]


def _n_quad8(x: Sequence[_Num]) -> list[_Num]:
    a, b = x[0], x[1]
    n5 = 0.5 * (1.0 - a * a) * (1.0 - b)
    n6 = 0.5 * (1.0 + a) * (1.0 - b * b)
    n7 = 0.5 * (1.0 - a * a) * (1.0 + b)
    n8 = 0.5 * (1.0 - a) * (1.0 - b * b)
    return [
        (1.0 - a) * (1.0 - b) / 4.0 - 0.5 * (n8 + n5),
        (1.0 + a) * (1.0 - b) / 4.0 - 0.5 * (n5 + n6),
        (1.0 + a) * (1.0 + b) / 4.0 - 0.5 * (n6 + n7),
        (1.0 - a) * (1.0 + b) / 4.0 - 0.5 * (n7 + n8),
        n5,
        n6,
        n7,
        n8,
    ]


def _n_quad9(x: Sequence[_Num]) -> list[_Num]:
    a, b = x[0], x[1]
    return [
        a * b * (1.0 - a) * (1.0 - b) / 4.0,
        -a * b * (1.0 + a) * (1.0 - b) / 4.0,
        a * b * (1.0 + a) * (1.0 + b) / 4.0,
        -a * b * (1.0 - a) * (1.0 + b) / 4.0,
        -0.5 * (1.0 - a * a) * (1.0 - b) * b,
        0.5 * (1.0 - b * b) * (a + 1.0) * a,
        0.5 * (1.0 - a * a) * (b + 1.0) * b,
        -0.5 * (1.0 - b * b) * (1.0 - a) * a,
        (1.0 - a * a) * (1.0 - b * b),
    ]


def _n_tet4(x: Sequence[_Num]) -> list[_Num]:
    return [1.0 - x[0] - x[1] - x[2], x[0], x[1], x[2]]


def _n_tet10(x: Sequence[_Num]) -> list[_Num]:
    a, b, c = x[0], x[1], x[2]
    d = 1.0 - a - b - c
    return [
        (2.0 * d - 1.0) * d,
        (2.0 * a - 1.0) * a,
        (2.0 * b - 1.0) * b,
        (2.0 * c - 1.0) * c,
        4.0 * d * a,
        4.0 * a * b,
        4.0 * b * d,
        4.0 * d * c,
        4.0 * a * c,
        4.0 * b * c,
    ]


def _n_hex8(x: Sequence[_Num]) -> list[_Num]:
    an, ap, bn, bp, cn, cp = 1.0 - x[0], 1.0 + x[0], 1.0 - x[1], 1.0 + x[1], 1.0 - x[2], 1.0 + x[2]
    return [
        an * bn * cn / 8.0,
        ap * bn * cn / 8.0,
        ap * bp * cn / 8.0,
        an * bp * cn / 8.0,
        an * bn * cp / 8.0,
        ap * bn * cp / 8.0,
        ap * bp * cp / 8.0,
        an * bp * cp / 8.0,
    ]


def _n_hex20(x: Sequence[_Num]) -> list[_Num]:
    a, b, c = x[0], x[1], x[2]
    an, ap, bn, bp, cn, cp = 1.0 - a, 1.0 + a, 1.0 - b, 1.0 + b, 1.0 - c, 1.0 + c
    return [
        -an * bn * cn * (2.0 + a + b + c) / 8.0,
        -ap * bn * cn * (2.0 - a + b + c) / 8.0,
        -ap * bp * cn * (2.0 - a - b + c) / 8.0,
        -an * bp * cn * (2.0 + a - b + c) / 8.0,
        -an * bn * cp * (2.0 + a + b - c) / 8.0,
        -ap * bn * cp * (2.0 - a + b - c) / 8.0,
        -ap * bp * cp * (2.0 - a - b - c) / 8.0,
        -an * bp * cp * (2.0 + a - b - c) / 8.0,
        an * ap * bn * cn / 4.0,
        bn * bp * ap * cn / 4.0,
        an * ap * bp * cn / 4.0,
        bn * bp * an * cn / 4.0,
        an * ap * bn * cp / 4.0,
        bn * bp * ap * cp / 4.0,
        an * ap * bp * cp / 4.0,
        bn * bp * an * cp / 4.0,
        cn * cp * an * bn / 4.0,
        cn * cp * ap * bn / 4.0,
        cn * cp * ap * bp / 4.0,
        cn * cp * an * bp / 4.0,
    ]


def _n_hex27(x: Sequence[_Num]) -> list[_Num]:
    a, b, c = x[0], x[1], x[2]
    an, ap, bn, bp, cn, cp = a - 1.0, 1.0 + a, b - 1.0, 1.0 + b, c - 1.0, 1.0 + c
    qa, qb, qc = 1.0 - a * a, 1.0 - b * b, 1.0 - c * c
    abc = a * b * c
    return [
        an * bn * cn * abc / 8.0,
        ap * bn * cn * abc / 8.0,
        ap * bp * cn * abc / 8.0,
        an * bp * cn * abc / 8.0,
        an * bn * cp * abc / 8.0,
        ap * bn * cp * abc / 8.0,
        ap * bp * cp * abc / 8.0,
        an * bp * cp * abc / 8.0,
        qa * bn * cn * b * c / 4.0,
        qb * ap * cn * a * c / 4.0,
        qa * bp * cn * b * c / 4.0,
        qb * an * cn * a * c / 4.0,
        qa * bn * cp * b * c / 4.0,
        qb * ap * cp * a * c / 4.0,
        qa * bp * cp * b * c / 4.0,
        qb * an * cp * a * c / 4.0,
        qc * an * bn * a * b / 4.0,
        qc * ap * bn * a * b / 4.0,
        qc * ap * bp * a * b / 4.0,
        qc * an * bp * a * b / 4.0,
        (a - 1.0) * a * qb * qc / 2.0,
        (1.0 + a) * a * qb * qc / 2.0,
        qa * (b - 1.0) * b * qc / 2.0,
        qa * (1.0 + b) * b * qc / 2.0,
        qa * qb * (c - 1.0) * c / 2.0,
        qa * qb * (1.0 + c) * c / 2.0,
        qa * qb * qc,
    ]


# --------------------------------------------------------------------------------------------- topologies
@dataclass(frozen=True)
class Topology:
    """Node layout of one numgeo element topology (independent of the formulation).

    Attributes:
        name: pynumgeo name (``tri6``, ``hex20`` ...).
        shape: numgeo element shape (``beam``, ``triangular``, ``rectangular``, ``tetrahedral``,
            ``hexahedral``).
        nnodes: number of nodes.
        dim: dimension of the reference element (1, 2 or 3).
        reference: reference coordinates of nodes 1..n in numgeo's natural coordinates (``[-1, 1]`` for
            beam, rectangular and hexahedral shapes, the unit simplex for triangles and tetrahedra).
        corners: local numbers (1-based) of the corner nodes.
        edges: ``(a, b)`` or ``(a, b, mid)`` per edge (1-based); for quadratic topologies edge *k* carries
            mid node ``len(corners) + k``.
        face_centres: mid-face nodes (hex27 only).
        centre: the interior node (quad9, hex27), else ``None``.
        vtk_type: VTK cell type with the same node layout.
        meshio_type: meshio cell type name with the same node layout.
        source: numgeo source lines of the shape functions that define the layout.
    """

    name: str
    shape: str
    nnodes: int
    dim: int
    reference: tuple[tuple[float, ...], ...]
    corners: tuple[int, ...]
    edges: tuple[tuple[int, ...], ...]
    face_centres: tuple[int, ...]
    centre: int | None
    vtk_type: int
    meshio_type: str
    source: str
    _n: Callable[[Sequence[_Num]], list[_Num]] = field(repr=False, compare=False)

    @property
    def order(self) -> int:
        """Polynomial order of the interpolation along an edge (1 or 2)."""
        return 1 if self.nnodes == len(self.corners) else 2

    @property
    def mid_nodes(self) -> tuple[int, ...]:
        """All nodes that are not corners (1-based)."""
        return tuple(i for i in range(1, self.nnodes + 1) if i not in self.corners)

    @property
    def centroid(self) -> tuple[float, ...]:
        """Reference coordinates of the element centre (where :mod:`~pynumgeo.mesh.quality` checks)."""
        return tuple(float(v) for v in np.mean(np.array([self.reference[i - 1] for i in self.corners]), axis=0))

    def reference_array(self) -> FloatArray:
        """:attr:`reference` as a ``(nnodes, dim)`` array."""
        return np.array(self.reference, dtype=np.float64)

    def shape_functions(self, xi: Sequence[float]) -> FloatArray:
        """numgeo's shape functions ``N(1..n)`` at the natural coordinates ``xi``.

        >>> topology("line3").shape_functions([0.0]).tolist()
        [-0.0, 0.0, 1.0]
        """
        return np.array(self._n(list(xi)), dtype=np.float64)

    def shape_derivatives(self, xi: Sequence[float]) -> FloatArray:
        """``dN/dxi`` at ``xi`` as a ``(dim, nnodes)`` array (exact complex-step derivative of
        :meth:`shape_functions`).

        >>> topology("quad4").shape_derivatives([0.0, 0.0]).tolist()
        [[-0.25, 0.25, 0.25, -0.25], [-0.25, -0.25, 0.25, 0.25]]
        """
        h = 1.0e-30
        out = np.zeros((self.dim, self.nnodes))
        for k in range(self.dim):
            z: list[complex] = [complex(v) for v in xi]
            z[k] += 1j * h
            out[k] = np.imag(np.array(self._n(z), dtype=np.complex128)) / h
        return out


def _ref(*pts: tuple[float, ...]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(float(v) for v in p) for p in pts)


_LINE2 = _ref((-1,), (1,))
_TRI3 = _ref((0, 0), (1, 0), (0, 1))
_QUAD4 = _ref((-1, -1), (1, -1), (1, 1), (-1, 1))
_QUAD8 = _QUAD4 + _ref((0, -1), (1, 0), (0, 1), (-1, 0))
_TET4 = _ref((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
_HEX8 = _ref((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
_HEX20 = _HEX8 + _ref(
    (0, -1, -1), (1, 0, -1), (0, 1, -1), (-1, 0, -1),
    (0, -1, 1), (1, 0, 1), (0, 1, 1), (-1, 0, 1),
    (-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0),
)  # fmt: skip
_TRI_EDGES = ((1, 2), (2, 3), (3, 1))
_QUAD_EDGES = ((1, 2), (2, 3), (3, 4), (4, 1))
_TET_EDGES = ((1, 2), (2, 3), (3, 1), (1, 4), (2, 4), (3, 4))
_HEX_EDGES = ((1, 2), (2, 3), (3, 4), (4, 1), (5, 6), (6, 7), (7, 8), (8, 5), (1, 5), (2, 6), (3, 7), (4, 8))


def _with_mid(edges: tuple[tuple[int, int], ...], first: int) -> tuple[tuple[int, ...], ...]:
    return tuple((a, b, first + k) for k, (a, b) in enumerate(edges))


_TET10_MID = _ref((0.5, 0, 0), (0.5, 0.5, 0), (0, 0.5, 0), (0, 0, 0.5), (0.5, 0, 0.5), (0, 0.5, 0.5))
_HEX27_MID = _ref((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (0, 0, 0))
_HEX_CORNERS = tuple(range(1, 9))


def _t(
    name: str,
    shape: str,
    dim: int,
    reference: tuple[tuple[float, ...], ...],
    corners: tuple[int, ...],
    edges: tuple[tuple[int, ...], ...],
    vtk: tuple[int, str],
    lines: str,
    n: Callable[[Sequence[_Num]], list[_Num]],
    face_centres: tuple[int, ...] = (),
    centre: int | None = None,
) -> Topology:
    return Topology(
        name, shape, len(reference), dim, reference, corners, edges, face_centres, centre, vtk[0], vtk[1],
        f"{_SF}:{lines}", n,
    )  # fmt: skip


def _topologies() -> dict[str, Topology]:
    t = [
        _t("line2", "beam", 1, _LINE2, (1, 2), ((1, 2),), (3, "line"), "72-75", _n_line2),
        _t("line3", "beam", 1, _LINE2 + _ref((0,)), (1, 2), ((1, 2, 3),), (21, "line3"), "76-81", _n_line3),
        _t("tri3", "triangular", 2, _TRI3, (1, 2, 3), _TRI_EDGES, (5, "triangle"), "95-99", _n_tri3),
        _t(
            "tri6", "triangular", 2, _TRI3 + _ref((0.5, 0), (0.5, 0.5), (0, 0.5)), (1, 2, 3),
            _with_mid(_TRI_EDGES, 4), (22, "triangle6"), "120-129", _n_tri6,
        ),
        _t("quad4", "rectangular", 2, _QUAD4, (1, 2, 3, 4), _QUAD_EDGES, (9, "quad"), "143-148", _n_quad4),
        _t(
            "quad8", "rectangular", 2, _QUAD8, (1, 2, 3, 4), _with_mid(_QUAD_EDGES, 5), (23, "quad8"),
            "160-171", _n_quad8,
        ),
        _t(
            "quad9", "rectangular", 2, _QUAD8 + _ref((0, 0)), (1, 2, 3, 4), _with_mid(_QUAD_EDGES, 5),
            (28, "quad9"), "172-185", _n_quad9, centre=9,
        ),
        _t("tet4", "tetrahedral", 3, _TET4, (1, 2, 3, 4), _TET_EDGES, (10, "tetra"), "199-206", _n_tet4),
        _t(
            "tet10", "tetrahedral", 3, _TET4 + _TET10_MID, (1, 2, 3, 4), _with_mid(_TET_EDGES, 5),
            (24, "tetra10"), "227-242", _n_tet10,
        ),
        _t("hex8", "hexahedral", 3, _HEX8, _HEX_CORNERS, _HEX_EDGES, (12, "hexahedron"), "263-274", _n_hex8),
        _t(
            "hex20", "hexahedral", 3, _HEX20, _HEX_CORNERS, _with_mid(_HEX_EDGES, 9), (25, "hexahedron20"),
            "295-319", _n_hex20,
        ),
        _t(
            "hex27", "hexahedral", 3, _HEX20 + _HEX27_MID, _HEX_CORNERS, _with_mid(_HEX_EDGES, 9),
            (29, "hexahedron27"), "323-364", _n_hex27, face_centres=(21, 22, 23, 24, 25, 26), centre=27,
        ),
    ]  # fmt: skip
    return {x.name: x for x in t}


#: All topologies by name.
TOPOLOGIES: dict[str, Topology] = _topologies()

_BY_SHAPE = {(t.shape, t.nnodes): t for t in TOPOLOGIES.values()}


def topology(name: str) -> Topology:
    """A topology by name (``line2`` ... ``hex27``).

    Raises:
        KeyError: for an unknown name.
    """
    try:
        return TOPOLOGIES[name.lower()]
    except KeyError:
        raise KeyError(f"unknown topology {name!r}; known: {', '.join(TOPOLOGIES)}") from None


def topology_of_shape(shape: str, nnodes: int) -> Topology:
    """The topology of a numgeo element shape with ``nnodes`` nodes.

    >>> topology_of_shape("hexahedral", 27).name
    'hex27'
    """
    try:
        return _BY_SHAPE[(shape.lower(), int(nnodes))]
    except KeyError:
        raise KeyError(f"numgeo has no {nnodes}-node {shape} element") from None


def element_topology(element_type: str) -> Topology:
    """The topology of a numgeo element type (library name or alias, any case).

    Raises:
        KeyError: if the element type is not in the catalogue.
    """
    e = _cat.element_type(element_type)
    return topology_of_shape(e.shape, e.nnodes)


# --------------------------------------------------------------------------------------------- faces
@dataclass(frozen=True)
class FaceTable:
    """numgeo's face table of one topology (``element_face_nodes``).

    Attributes:
        name: numgeo/catalogue key, e.g. ``triangular-quadratic`` or ``rectangular-shell-8``.
        faces: local nodes (1-based) of faces ``F1``, ``F2``, ... in numgeo's order.
        topology: the element topology the table belongs to.
        exterior: number of corner nodes at the start of each face row (the rest are mid/centre nodes).
        source: ``file:line (routine)`` of the table in the numgeo source.
    """

    name: str
    faces: tuple[tuple[int, ...], ...]
    topology: str
    exterior: int
    source: str

    @property
    def labels(self) -> tuple[str, ...]:
        """``("F1", "F2", ...)``."""
        return tuple(f"F{k}" for k in range(1, len(self.faces) + 1))

    def nodes(self, face: str | int) -> tuple[int, ...]:
        """Local nodes (1-based) of a face given as ``"F2"``, ``"S2"`` or ``2``."""
        k = face_number(face)
        if not 1 <= k <= len(self.faces):
            raise KeyError(f"{self.name} has faces F1..F{len(self.faces)}, not F{k}")
        return self.faces[k - 1]


#: catalogue face-table key -> topology (shell tables are named after the element in fem_element_faces.f90)
_TABLE_TOPOLOGY = {
    "beam-linear": "line2",
    "beam-quadratic": "line3",
    "triangular-linear": "tri3",
    "triangular-quadratic": "tri6",
    "rectangular-linear": "quad4",
    "rectangular-quadratic": "quad8",
    "tetrahedral-linear": "tet4",
    "tetrahedral-quadratic": "tet10",
    "hexahedral-linear": "hex8",
    "hexahedral-quadratic": "hex20",
    "hexahedral-bi-quadratic": "hex27",
    "triangular-shell-3": "tri3",
    "rectangular-shell-4": "quad4",
    "triangular-shell-6": "tri6",
    "rectangular-shell-8": "quad8",
}


@functools.cache
def face_tables() -> dict[str, FaceTable]:
    """All face tables of the catalogue (section ``model/surface_faces``) by key."""
    out: dict[str, FaceTable] = {}
    for s in _cat.load().section("model", "surface_faces"):
        key = str(s["topology"])
        topo = TOPOLOGIES[_TABLE_TOPOLOGY[key]]
        rows = tuple(tuple(int(n) for n in s["faces"][f"F{k}"]) for k in range(1, len(s["faces"]) + 1))
        exterior = sum(1 for n in rows[0] if n in topo.corners)
        src = s.get("source") or {}
        out[key] = FaceTable(
            key, rows, topo.name, exterior, f"{src.get('file')}:{src.get('line')} ({src.get('routine')})"
        )
    return out


def face_table(name: str) -> FaceTable:
    """A face table by catalogue key (``hexahedral-quadratic``, ``triangular-shell-6`` ...)."""
    try:
        return face_tables()[name]
    except KeyError:
        raise KeyError(f"unknown face table {name!r}; known: {', '.join(face_tables())}") from None


def element_faces(element_type: str) -> FaceTable:
    """The face table numgeo uses for element-based surfaces of an element type.

    This is the catalogue's ``surface_face_topology`` of the element type (the selection of
    ``src/contacts/contact_.f90:553-610``: 2D models by interpolation, 3D models by shape; triangles and
    quadrilaterals in 3D models are shells with the faces ``F1`` (side of the normal) and ``F2``).
    """
    e = _cat.element_type(element_type)
    if not e.face_topology:
        raise KeyError(f"element type {e.name} has no face table in the catalogue")
    return face_table(e.face_topology)


_FACE_RE = re.compile(r"^\s*[FS]?(\d+)\s*$", re.IGNORECASE)


def face_number(face: str | int) -> int:
    """Face number of ``"F3"``, ``"s3"`` or ``3`` (numgeo accepts ``F1``-``F6`` and ``S1``-``S6``,
    ``src/contacts/contact_.f90:638``).

    >>> face_number("S3"), face_number("f2"), face_number(1)
    (3, 2, 1)
    """
    if isinstance(face, int):
        return face
    m = _FACE_RE.match(face)
    if not m:
        raise KeyError(f"not a face label: {face!r} (use F1..F6 or S1..S6)")
    return int(m.group(1))


def face_connectivity(element_type: str, connectivity: npt.ArrayLike, face: str | int) -> IntArray:
    """Global node labels of one face of each element (rows of ``connectivity`` in numgeo order).

    Args:
        element_type: numgeo element type of the rows.
        connectivity: ``(n_elements, nnodes)`` node labels in numgeo order.
        face: ``"F1"`` ... (or ``"S1"`` ..., or the number).

    Returns:
        ``(n_elements, n_face_nodes)`` node labels in the order of numgeo's face table.
    """
    conn = np.atleast_2d(np.asarray(connectivity, dtype=np.int64))
    table = element_faces(element_type)
    nodes = np.array(table.nodes(face), dtype=np.int64) - 1
    if conn.shape[1] < int(np.max(nodes)) + 1:
        raise ValueError(f"connectivity has {conn.shape[1]} columns, {element_type} needs more")
    return conn[:, nodes]
