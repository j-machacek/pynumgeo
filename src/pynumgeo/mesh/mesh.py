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
"""The mesh of a deck: nodes, element blocks, node and element sets, surfaces (numpy based).

This is the hand-off contract between front-ends (FreeCAD, gmsh/meshio, scripts) and pynumgeo:

* node labels are **1..n in the order of definition** — numgeo uses node labels as array positions;
  :meth:`Mesh.renumbered` produces such a mesh and the maps back to the original labels;
* connectivities are node labels in **numgeo node order** (catalogue element types);
* sets are named collections of labels (or a solver-side query such as ``find``); surfaces refer to
  element sets and face numbers, or to a node set.

Examples:
    >>> import numpy as np
    >>> m = Mesh()
    >>> m.add_nodes([[0, 0], [1, 0], [1, 1], [0, 1]])
    array([1, 2, 3, 4])
    >>> m.add_elements("u4-solid", [[1, 2, 3, 4]])
    array([1])
    >>> m.add_nset("Bottom", [1, 2]).name
    'Bottom'
    >>> m.node_count, m.element_count, m.check()
    (4, 1, [])
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt

__all__ = ["ElementBlock", "ElementSet", "Mesh", "NodeSet", "SetKind", "Surface"]

IntArray = npt.NDArray[np.int64]
FloatArray = npt.NDArray[np.float64]
SetKind = Literal["list", "generate", "find", "boundingbox", "cylinder"]


def _ints(values: Iterable[int] | npt.ArrayLike) -> IntArray:
    a = np.asarray(values, dtype=np.int64)
    return a.reshape(-1)


@dataclass
class ElementBlock:
    """Elements of one type. ``connectivity[i]`` are node labels of element ``labels[i]`` in numgeo order.

    ``options`` holds further ``*Element`` options as read (e.g. ``("BI-QUADRATIC", None)``).
    """

    type: str
    labels: IntArray
    connectivity: IntArray
    options: list[tuple[str, str | None]] = field(default_factory=list)
    #: ``**`` lines the writer puts above the block (not part of comparisons)
    comment: str | None = None

    def __post_init__(self) -> None:
        self.labels = _ints(self.labels)
        self.connectivity = np.asarray(self.connectivity, dtype=np.int64)
        if self.connectivity.ndim != 2 or self.connectivity.shape[0] != self.labels.shape[0]:
            raise ValueError(f"connectivity of {self.type} must have shape (n_elements, n_nodes)")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ElementBlock):
            return NotImplemented
        return (
            self.type.upper() == other.type.upper()
            and np.array_equal(self.labels, other.labels)
            and np.array_equal(self.connectivity, other.connectivity)
            and [(k.upper(), None if v is None else v.upper()) for k, v in self.options]
            == [(k.upper(), None if v is None else v.upper()) for k, v in other.options]
        )


@dataclass
class _LabelSet:
    name: str
    kind: SetKind = "list"
    members: IntArray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    #: generate: (first, last, increment); find: point (3); boundingbox: 6 values; cylinder: 4..8 values
    values: list[float] = field(default_factory=list)
    internal: bool = False
    instance: str | None = None
    #: ``**`` lines the writer puts above the set (not part of comparisons)
    comment: str | None = None

    def __post_init__(self) -> None:
        self.members = _ints(self.members)

    @property
    def key(self) -> str:
        """Name as numgeo compares it (upper case, no blanks)."""
        return self.name.upper().replace(" ", "")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (
            self.key == other.key
            and self.kind == other.kind
            and np.array_equal(self.members, other.members)
            and [float(v) for v in self.values] == [float(v) for v in other.values]
            and self.internal == other.internal
            and (self.instance or "").upper() == (other.instance or "").upper()
        )


@dataclass(eq=False)
class NodeSet(_LabelSet):
    """A node set (``*Nset``): node labels, or a query evaluated by numgeo (``find`` and variants)."""


@dataclass(eq=False)
class ElementSet(_LabelSet):
    """An element set (``*Elset``): element labels, or a query evaluated by numgeo."""


@dataclass
class Surface:
    """A surface (``*Surface``).

    ``type="element"`` rows are ``(elset, face)``, ``type="node"`` rows ``(nset,)``.
    """

    name: str
    type: Literal["element", "node"] = "element"
    rows: list[tuple[str, ...]] = field(default_factory=list)
    #: ``**`` lines the writer puts above the surface (not part of comparisons)
    comment: str | None = None

    @property
    def key(self) -> str:
        """Name as numgeo compares it."""
        return self.name.upper().replace(" ", "")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Surface):
            return NotImplemented
        return (
            self.key == other.key
            and self.type == other.type
            and [tuple(x.upper() for x in r) for r in self.rows] == [tuple(x.upper() for x in r) for r in other.rows]
        )


class Mesh:
    """Nodes, element blocks, sets and surfaces of a deck (see module docstring)."""

    def __init__(self) -> None:
        self.node_labels: IntArray = np.zeros(0, dtype=np.int64)
        self.coords: FloatArray = np.zeros((0, 2), dtype=np.float64)
        self.blocks: list[ElementBlock] = []
        self.nsets: list[NodeSet] = []
        self.elsets: list[ElementSet] = []
        self.surfaces: list[Surface] = []
        #: ``**`` lines the writer puts above ``*Node`` (not part of comparisons)
        self.comment: str | None = None

    # ------------------------------------------------------------------ building
    def add_nodes(self, coords: npt.ArrayLike, labels: npt.ArrayLike | None = None) -> IntArray:
        """Append nodes; labels default to the next numbers after the current maximum."""
        c = np.atleast_2d(np.asarray(coords, dtype=np.float64))
        if labels is None:
            start = int(np.max(self.node_labels)) + 1 if self.node_labels.size else 1
            lab = np.arange(start, start + c.shape[0], dtype=np.int64)
        else:
            lab = _ints(labels)
        if lab.shape[0] != c.shape[0]:
            raise ValueError("number of labels and coordinates differ")
        if self.coords.shape[0] == 0:
            self.coords = c
        else:
            if c.shape[1] != self.coords.shape[1]:
                w = max(c.shape[1], self.coords.shape[1])
                self.coords = _pad(self.coords, w)
                c = _pad(c, w)
            self.coords = np.vstack([self.coords, c])
        self.node_labels = np.concatenate([self.node_labels, lab])
        return lab

    def add_elements(
        self, type: str, connectivity: npt.ArrayLike, labels: npt.ArrayLike | None = None, *, comment: str | None = None
    ) -> IntArray:
        """Append a block of elements of one type; labels default to the next numbers."""
        conn = np.atleast_2d(np.asarray(connectivity, dtype=np.int64))
        if labels is None:
            mx = max((int(np.max(b.labels)) for b in self.blocks if b.labels.size), default=0)
            lab = np.arange(mx + 1, mx + 1 + conn.shape[0], dtype=np.int64)
        else:
            lab = _ints(labels)
        self.blocks.append(ElementBlock(type=type, labels=lab, connectivity=conn, comment=comment))
        return lab

    def add_nset(
        self, name: str, members: Iterable[int] | npt.ArrayLike, *, internal: bool = False, comment: str | None = None
    ) -> NodeSet:
        """Add a node set given by node labels."""
        s = NodeSet(name=name, members=_ints(members), internal=internal, comment=comment)
        self.nsets.append(s)
        return s

    def add_elset(
        self, name: str, members: Iterable[int] | npt.ArrayLike, *, internal: bool = False, comment: str | None = None
    ) -> ElementSet:
        """Add an element set given by element labels."""
        s = ElementSet(name=name, members=_ints(members), internal=internal, comment=comment)
        self.elsets.append(s)
        return s

    def add_surface(
        self,
        name: str,
        rows: Sequence[Sequence[str]],
        type: Literal["element", "node"] = "element",
        *,
        comment: str | None = None,
    ) -> Surface:
        """Add a surface: element-based rows ``(elset, "F1")`` or node-based rows ``(nset,)``."""
        s = Surface(name=name, type=type, rows=[tuple(r) for r in rows], comment=comment)
        self.surfaces.append(s)
        return s

    # ------------------------------------------------------------------ queries
    @property
    def node_count(self) -> int:
        """Number of nodes."""
        return int(self.node_labels.shape[0])

    @property
    def element_count(self) -> int:
        """Number of elements over all blocks."""
        return sum(int(b.labels.shape[0]) for b in self.blocks)

    @property
    def element_labels(self) -> IntArray:
        """All element labels in block order."""
        if not self.blocks:
            return np.zeros(0, dtype=np.int64)
        return np.concatenate([b.labels for b in self.blocks])

    def nset(self, name: str) -> NodeSet:
        """First node set of that name (numgeo also uses the first one)."""
        k = name.upper().replace(" ", "")
        for s in self.nsets:
            if s.key == k:
                return s
        raise KeyError(f"no node set {name!r}")

    def elset(self, name: str) -> ElementSet:
        """First element set of that name."""
        k = name.upper().replace(" ", "")
        for s in self.elsets:
            if s.key == k:
                return s
        raise KeyError(f"no element set {name!r}")

    def surface(self, name: str) -> Surface:
        """First surface of that name."""
        k = name.upper().replace(" ", "")
        for s in self.surfaces:
            if s.key == k:
                return s
        raise KeyError(f"no surface {name!r}")

    def find_nearest_node(self, point: Sequence[float], candidates: IntArray | None = None) -> int:
        """Label of the node nearest to ``point`` as numgeo's ``find`` does (first minimum wins)."""
        idx = np.arange(self.node_count) if candidates is None else candidates
        d = self.coords.shape[1]
        p = np.zeros(d)
        p[: min(d, len(point))] = list(point)[:d]
        dist = np.linalg.norm(self.coords[idx] - p, axis=1)
        return int(self.node_labels[idx[int(np.argmin(dist))]])

    # ------------------------------------------------------------------ checks and transforms
    def check(self) -> list[str]:
        """Problems that make numgeo fail or compute wrong results (empty list = fine).

        Checks: node labels 1..n in order, unique element labels, connectivity refers to existing
        nodes, every node used by an element.
        """
        out: list[str] = []
        n = self.node_count
        if n and not np.array_equal(self.node_labels, np.arange(1, n + 1)):
            out.append("node labels must be 1..n in the order of definition (numgeo uses them as positions)")
        el = self.element_labels
        if el.size and np.unique(el).size != el.size:
            out.append("element labels are not unique")
        if self.blocks and n:
            used = np.unique(np.concatenate([b.connectivity.reshape(-1) for b in self.blocks]))
            missing = np.setdiff1d(used, self.node_labels)
            if missing.size:
                out.append(f"{missing.size} connectivity entries refer to undefined nodes, e.g. {int(missing[0])}")
            unused = np.setdiff1d(self.node_labels, used)
            if unused.size:
                out.append(f"{unused.size} nodes are not used by any element (numgeo stops), e.g. {int(unused[0])}")
        return out

    def renumbered(self) -> tuple[Mesh, IntArray, IntArray]:
        """Copy with node labels 1..n and element labels 1..m (block order).

        Returns:
            ``(mesh, node_map, element_map)`` where ``node_map[i]`` / ``element_map[j]`` are the original
            labels of new node ``i+1`` / element ``j+1``.
        """
        new = Mesh()
        node_map = self.node_labels.copy()
        lookup = {int(old): i + 1 for i, old in enumerate(node_map)}
        new.coords = self.coords.copy()
        new.node_labels = np.arange(1, self.node_count + 1, dtype=np.int64)
        elem_map = self.element_labels.copy()
        el_lookup = {int(old): j + 1 for j, old in enumerate(elem_map)}
        vmap = np.vectorize(lambda x: lookup[int(x)], otypes=[np.int64])
        start = 1
        for b in self.blocks:
            m = b.labels.shape[0]
            conn = vmap(b.connectivity) if b.connectivity.size else b.connectivity.copy()
            new.blocks.append(
                ElementBlock(b.type, np.arange(start, start + m, dtype=np.int64), conn, list(b.options), b.comment)
            )
            start += m
        for s in self.nsets:
            mem = np.array([lookup[int(x)] for x in s.members], dtype=np.int64) if s.kind == "list" else s.members
            new.nsets.append(NodeSet(s.name, s.kind, mem, list(s.values), s.internal, s.instance, s.comment))
        for e in self.elsets:
            mem = np.array([el_lookup[int(x)] for x in e.members], dtype=np.int64) if e.kind == "list" else e.members
            new.elsets.append(ElementSet(e.name, e.kind, mem, list(e.values), e.internal, e.instance, e.comment))
        new.surfaces = [Surface(s.name, s.type, list(s.rows), s.comment) for s in self.surfaces]
        new.comment = self.comment
        return new, node_map, elem_map

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mesh):
            return NotImplemented
        return (
            np.array_equal(self.node_labels, other.node_labels)
            and self.coords.shape == other.coords.shape
            and np.array_equal(self.coords, other.coords)
            and self.blocks == other.blocks
            and self.nsets == other.nsets
            and self.elsets == other.elsets
            and self.surfaces == other.surfaces
        )

    __hash__ = None  # type: ignore[assignment]

    def summary(self) -> dict[str, object]:
        """Counts and names, e.g. for agents (no arrays)."""
        return {
            "nodes": self.node_count,
            "dimension_of_coordinates": int(self.coords.shape[1]) if self.node_count else 0,
            "elements": _count_by_type(self.blocks),
            "node_sets": [s.name for s in self.nsets],
            "element_sets": [s.name for s in self.elsets],
            "surfaces": [s.name for s in self.surfaces],
        }


def _count_by_type(blocks: list[ElementBlock]) -> dict[str, int]:
    out: dict[str, int] = {}
    for b in blocks:
        out[b.type.lower()] = out.get(b.type.lower(), 0) + int(b.labels.shape[0])
    return out


def _pad(a: FloatArray, width: int) -> FloatArray:
    if a.shape[1] >= width:
        return a
    return np.hstack([a, np.zeros((a.shape[0], width - a.shape[1]))])
