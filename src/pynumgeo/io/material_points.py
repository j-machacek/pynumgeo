# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#                                                pynumgeo
#                              Python API for the finite element code numgeo
#                                     Copyright (C) 2026 Jan Machacek
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
#
# Author: Jan Machacek (with help of Claude Opus 5.5)
#
# pynumgeo writes, checks and runs numgeo input files and reads numgeo results. It follows the
# development of numgeo: new developments in the numgeo source code are taken over into the API, and a
# CI pipeline tests every change.
#
# License: BSD-3-Clause, see LICENSE.
#
# History
# 03.11.2026, J. Machacek - Initial version (with help of Claude Opus 5.5)
# =~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~~=~=~
"""Point files of ``*Assign material, elset=<set>, from-file`` and the assignment numgeo makes with them.

Everything below follows ``assign_material_from_file`` of numgeo-src 60135dc
(``src/input/read_solid_section_.f90:282-881``, cited as ``:line``).

**File.** Read as bytes; a UTF-8 byte order mark at the start is skipped (:368-371). Lines end at LF;
carriage returns and tabs count as blanks (:816). Blank lines are skipped. The first line with content
is a header if none of its first three fields is a number (:398-413); otherwise it is the first point.

**Points.** Every further line has exactly four fields separated by semicolons, ``x;y;z;material-name``;
an empty fifth field after a closing semicolon is ignored (:822-839). The coordinates are numbers
``[sign]digits[.digits][(e|E|d|D)[sign]digits]`` (:683-762): a decimal comma, other separators or
``inf``/``nan`` are errors. A material name has at most 256 characters; it is compared with the
``*Material`` names in upper case and without blanks (:455-456). numgeo stops at the first line with an
error (:419-438) and if the file has no point (:479-483).

**Assignment.** The centroid of an element is the mean of the coordinates of its nodes (:523-547); in 2D
analyses only ``x`` and ``y`` count. The element receives the material of the nearest point; points whose
distance exceeds the smallest one by less than ``1e-9`` times the diagonal of the bounding box of the
points count as equidistant, and of those the point given first in the file wins (:295, :549-576). Names
assigned to an element must be defined with ``*Material`` (error, :635-640); undefined names of the
file assigned to no element only give a warning (:642-647).

Examples:
    >>> import pathlib, tempfile
    >>> p = pathlib.Path(tempfile.mkdtemp()) / "ground.csv"
    >>> _ = p.write_text("x;y;z;material\\n0.0;0.0;0;Sand\\n10.0;0.0;0;Clay layer\\n")
    >>> pts = read_material_points(p)
    >>> pts.header, pts.names, pts.point_name.tolist(), pts.lines.tolist()
    ('x;y;z;material', ('SAND', 'CLAYLAYER'), [0, 1], [2, 3])
    >>> idx, dist = nearest_points(pts.coords[:, :2], np.array([[2.0, 1.0], [5.0, 3.0]]), pts.tie_tolerance(2))
    >>> [pts.names[pts.point_name[i]] for i in idx]
    ['SAND', 'SAND']
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import numpy.typing as npt

from pynumgeo.io.lexer import upper_ascii

__all__ = [
    "TIE_TOLERANCE",
    "MaterialAssignment",
    "MaterialPoints",
    "MaterialPointsError",
    "assign_materials",
    "nearest_points",
    "read_material_points",
]

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

#: Relative distance (of the diagonal of the bounding box of the points) below which points are
#: equidistant (``tie_tolerance``, :295).
TIE_TOLERANCE = 1.0e-9
#: Longest material name numgeo stores (``character(len=256)``, :859).
MAX_NAME = 256

# read_real (:683-762): [sign]digits[.digits][(e|E|d|D)[sign]digits], at least one digit in the mantissa
_REAL = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eEdD][+-]?\d+)?$")
_BOM = b"\xef\xbb\xbf"
# brute force up to this many point-centroid distances, a grid search above
_BRUTE_LIMIT = 20_000_000
_CHUNK = 2_000_000


class MaterialPointsError(ValueError):
    """The point file cannot be used: numgeo stops with this message (line numbers count from 1)."""


def _read_real(field: str) -> float | None:
    """``read_real`` of numgeo: the value, or ``None`` for anything numgeo rejects."""
    s = field.strip(" ")
    if not _REAL.match(s):
        return None
    value = float(s.replace("d", "e").replace("D", "e"))
    return value if math.isfinite(value) else None


@dataclass(frozen=True, eq=False)
class MaterialPoints:
    """The points of a point file in the order of the file.

    Attributes:
        path: the file.
        coords: ``(n, 3)`` coordinates ``x, y, z``.
        names: the material names of the file, upper case and without blanks, in order of first appearance.
        point_name: index into ``names`` of every point.
        lines: line number (from 1) of every point.
        header: the header line, ``None`` if the file has none.
    """

    path: Path
    coords: FloatArray
    names: tuple[str, ...]
    point_name: IntArray
    lines: IntArray
    header: str | None

    def tie_tolerance(self, ndim: int) -> float:
        """Distance below which two points count as equidistant in an analysis with ``ndim`` dimensions."""
        c = self.coords[:, :ndim]
        return TIE_TOLERANCE * float(np.linalg.norm(c.max(axis=0) - c.min(axis=0)))


def _fields(line: str) -> list[str]:
    fields = line.split(";")
    if len(fields) == 5 and fields[4].strip(" ") == "":
        fields = fields[:4]
    return fields


def read_material_points(path: str | os.PathLike[str]) -> MaterialPoints:
    """Read a point file as numgeo does (see module docstring).

    Raises:
        MaterialPointsError: a line numgeo rejects (the first one), or no point at all.
        OSError: the file cannot be read.
    """
    p = Path(path)
    data = p.read_bytes()
    if data.startswith(_BOM):
        data = data[len(_BOM) :]
    # numgeo compares bytes; latin-1 maps every byte to one character
    text = data.decode("latin-1")
    rows = text.split("\n")
    if rows and rows[-1] == "" and text.endswith("\n"):
        rows.pop()
    header: str | None = None
    coords: list[tuple[float, float, float]] = []
    point_name: list[int] = []
    lines: list[int] = []
    names: dict[str, int] = {}
    first = True
    for no, raw in enumerate(rows, start=1):
        line = raw.replace("\r", " ").replace("\t", " ")
        if line.strip(" ") == "":
            continue
        fields = _fields(line.rstrip(" "))
        if first:
            first = False
            if not any(_read_real(f) is not None for f in fields[:3]):
                header = line.strip(" ")
                continue
        where = f'line {no} of the file "{p}"'
        if len(fields) != 4:
            raise MaterialPointsError(
                f"{where} has {len(fields)} fields, four fields separated by semicolons are expected "
                f"(x;y;z;material-name): {line.strip(' ')[:200]}"
            )
        xyz = [_read_real(f) for f in fields[:3]]
        for f, v in zip(fields[:3], xyz, strict=True):
            if v is None:
                raise MaterialPointsError(
                    f'{where} contains an invalid coordinate "{f.strip(" ")}" (numbers with a decimal point and '
                    f"semicolons as separators are expected): {line.strip(' ')[:200]}"
                )
        name = fields[3].strip(" ")
        if not name:
            raise MaterialPointsError(f"{where} contains no material name: {line.strip(' ')[:200]}")
        if len(name) > MAX_NAME:
            raise MaterialPointsError(f"{where} contains a material name with more than {MAX_NAME} characters")
        key = upper_ascii(name.replace(" ", ""))
        coords.append((xyz[0], xyz[1], xyz[2]))  # type: ignore[arg-type]
        point_name.append(names.setdefault(key, len(names)))
        lines.append(no)
    if not coords:
        raise MaterialPointsError(f'the file "{p}" contains no data points (x;y;z;material-name)')
    return MaterialPoints(
        path=p,
        coords=np.array(coords, dtype=np.float64),
        names=tuple(names),
        point_name=np.array(point_name, dtype=np.int64),
        lines=np.array(lines, dtype=np.int64),
        header=header,
    )


# ----------------------------------------------------------------------------- nearest point
def nearest_points(points: npt.ArrayLike, queries: npt.ArrayLike, tolerance: float) -> tuple[IntArray, FloatArray]:
    """Nearest point of every query with numgeo's tie rule.

    Of the points whose distance to the query is at most the smallest distance plus ``tolerance``, the
    one with the smallest index is taken (:549-576).

    Args:
        points: ``(n, d)`` coordinates, ``n >= 1``.
        queries: ``(m, d)`` coordinates.
        tolerance: absolute distance below which points count as equidistant.

    Returns:
        Index of the chosen point (0-based) and the smallest distance, for every query.
    """
    pts = np.asarray(points, dtype=np.float64)
    qs = np.asarray(queries, dtype=np.float64)
    if pts.ndim != 2 or qs.ndim != 2 or pts.shape[1] != qs.shape[1] or pts.shape[0] == 0:
        raise ValueError("points (n, d) with n >= 1 and queries (m, d) are needed")
    if qs.shape[0] == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    if pts.shape[0] * qs.shape[0] <= _BRUTE_LIMIT:
        return _brute(pts, qs, tolerance)
    return _Grid(pts).nearest(qs, tolerance)


def _limit(d2min: FloatArray, tolerance: float) -> FloatArray:
    """Squared distance up to which points count as equidistant: ``max((sqrt(d2min)+tol)**2, d2min)``."""
    return np.maximum((np.sqrt(d2min) + tolerance) ** 2, d2min)


def _brute(pts: FloatArray, qs: FloatArray, tolerance: float) -> tuple[IntArray, FloatArray]:
    idx = np.empty(qs.shape[0], dtype=np.int64)
    dist = np.empty(qs.shape[0], dtype=np.float64)
    step = max(1, _CHUNK // pts.shape[0])
    for a in range(0, qs.shape[0], step):
        q = qs[a : a + step]
        d2 = ((q[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        d2min = d2.min(axis=1)
        idx[a : a + step] = np.argmax(d2 <= _limit(d2min, tolerance)[:, None], axis=1)
        dist[a : a + step] = np.sqrt(d2min)
    return idx, dist


class _Grid:
    """Uniform grid of the points (about one point per cell) for an exact nearest-point search.

    After the cells within the Chebyshev distance ``r`` (in cells) of the query cell are searched, every
    other point is at least ``L`` away, ``L**2 = E + (r h)**2 + 2 r h e_min``: ``E`` is the squared distance
    of the query to the bounding box of the grid, ``e_min`` the smallest distance to it in one of the
    dimensions with cells (0 inside). The search stops once ``L`` exceeds the distance looked for.
    """

    def __init__(self, pts: FloatArray) -> None:
        self.pts = pts
        n = pts.shape[0]
        self.lo = pts.min(axis=0)
        self.hi = pts.max(axis=0)
        ext = self.hi - self.lo
        self.active = ext > 0.0
        k = int(self.active.sum())
        if k == 0:
            h = 1.0
        else:
            h = float(np.prod(ext[self.active]) / n) ** (1.0 / k)
            h = max(h, float(ext[self.active].max()) / 1.0e6)
        while True:
            nc = np.where(self.active, np.floor(ext / h).astype(np.int64) + 1, 1)
            if float(np.prod(nc.astype(np.float64))) <= 4.0 * n + 64:
                break
            h *= 1.5
        self.h = h
        self.nc = nc
        cells = self._cells(pts)
        ids = np.ravel_multi_index(tuple(cells.T), tuple(nc))
        self.order = np.argsort(ids, kind="stable")
        sorted_ids = ids[self.order]
        all_ids = np.arange(int(np.prod(nc)))
        self.start = np.searchsorted(sorted_ids, all_ids, side="left")
        self.count = np.searchsorted(sorted_ids, all_ids, side="right") - self.start

    def _cells(self, x: FloatArray) -> IntArray:
        c = np.floor((x - self.lo) / self.h).astype(np.int64)
        c[:, ~self.active] = 0
        return np.clip(c, 0, self.nc - 1)

    def _offsets(self, r: int) -> list[IntArray]:
        dims = [list(range(-r, r + 1)) if a else [0] for a in self.active]
        return [np.array(o, dtype=np.int64) for o in product(*dims) if max((abs(v) for v in o), default=0) == r]

    def nearest(self, qs: FloatArray, tolerance: float) -> tuple[IntArray, FloatArray]:
        qc = self._cells(qs)
        out = np.maximum(self.lo - qs, 0.0) + np.maximum(qs - self.hi, 0.0)
        e_all = (out**2).sum(axis=1)
        e_min = np.where(self.active, out, np.inf).min(axis=1) if self.active.any() else np.zeros(len(qs))
        e_min = np.where(np.isfinite(e_min), e_min, 0.0)
        # pass 1: smallest squared distance; pass 2: smallest index within the limit of the tie rule
        d2min = self._search(qs, qc, e_all, e_min, None)
        limit = _limit(d2min, tolerance)
        idx = self._search(qs, qc, e_all, e_min, limit)
        return idx.astype(np.int64), np.sqrt(d2min)

    def _search(
        self, qs: FloatArray, qc: IntArray, e_all: FloatArray, e_min: FloatArray, limit: FloatArray | None
    ) -> FloatArray:
        m = qs.shape[0]
        n = self.pts.shape[0]
        best = np.full(m, np.inf) if limit is None else np.full(m, float(n))
        todo = np.arange(m)
        r = 0
        while todo.size:
            for off in self._offsets(r):
                cc = qc[todo] + off
                ok = np.all((cc >= 0) & (cc < self.nc), axis=1)
                if not ok.any():
                    continue
                q = todo[ok]
                cid = np.ravel_multi_index(tuple(cc[ok].T), tuple(self.nc))
                s, cnt = self.start[cid], self.count[cid]
                for j in range(int(cnt.max())):
                    sel = cnt > j
                    qi = q[sel]
                    pi = self.order[s[sel] + j]
                    d2 = ((qs[qi] - self.pts[pi]) ** 2).sum(axis=1)
                    if limit is None:
                        best[qi] = np.minimum(best[qi], d2)
                    else:
                        hit = d2 <= limit[qi]
                        best[qi[hit]] = np.minimum(best[qi[hit]], pi[hit])
            # lower bound of the distance of the points not searched yet (slightly reduced against round-off)
            rh = r * self.h * (1.0 - 1.0e-9)
            bound = e_all[todo] + rh * rh + 2.0 * rh * e_min[todo]
            need = best[todo] if limit is None else limit[todo]
            todo = todo[bound <= need] if limit is not None else todo[bound < need]
            r += 1
            if r > int(self.nc.max()) + 1:
                break
        return best


# ----------------------------------------------------------------------------- assignment
@dataclass(frozen=True, eq=False)
class MaterialAssignment:
    """The material numgeo gives every element of the set.

    Attributes:
        elements: element labels of the set, in the order of the set.
        point: index of the chosen point (0-based, order of the file) of every element.
        distance: distance between the centroid of the element and its point.
        outside: the centroid lies outside the bounding box of the points.
        materials: material name (upper case, no blanks) of every element.
    """

    elements: IntArray
    point: IntArray
    distance: FloatArray
    outside: npt.NDArray[np.bool_]
    materials: tuple[str, ...]

    def used_names(self) -> set[str]:
        """Material names assigned to at least one element."""
        return set(self.materials)


def assign_materials(
    points: MaterialPoints,
    node_labels: npt.ArrayLike,
    coords: npt.ArrayLike,
    elements: list[tuple[int, IntArray]],
    ndim: int,
) -> MaterialAssignment:
    """The material of every element of a set (see module docstring).

    Args:
        points: the point file.
        node_labels: labels of all nodes.
        coords: their coordinates (``(n, 2)`` or ``(n, 3)``; missing ``z`` counts as 0).
        elements: ``(label, node labels)`` of every element of the set, in the order of the set.
        ndim: dimension of the analysis (2 or 3).

    Raises:
        KeyError: an element has a node that is not defined (numgeo stops, :588-602).
    """
    labels = np.asarray(node_labels, dtype=np.int64)
    xyz = np.asarray(coords, dtype=np.float64)
    if xyz.shape[1] < ndim:
        xyz = np.hstack([xyz, np.zeros((xyz.shape[0], ndim - xyz.shape[1]))])
    xyz = xyz[:, :ndim]
    pos = {int(lab): i for i, lab in enumerate(labels.tolist())}
    centroids = np.empty((len(elements), ndim), dtype=np.float64)
    for k, (label, nodes) in enumerate(elements):
        try:
            rows = [pos[int(n)] for n in nodes]
        except KeyError as e:
            raise KeyError(f"node {e.args[0]} of element {label} is not defined") from None
        centroids[k] = xyz[rows].sum(axis=0) / len(rows)
    pts = points.coords[:, :ndim]
    idx, dist = nearest_points(pts, centroids, points.tie_tolerance(ndim))
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    outside = np.any((centroids < lo) | (centroids > hi), axis=1)
    names = tuple(points.names[points.point_name[i]] for i in idx.tolist())
    return MaterialAssignment(
        elements=np.array([lab for lab, _ in elements], dtype=np.int64),
        point=idx,
        distance=dist,
        outside=outside,
        materials=names,
    )
