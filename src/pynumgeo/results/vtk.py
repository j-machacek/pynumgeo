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
"""Readers for numgeo's VTK field output (``*Output, field, vtk, ascii|binary``), standard library only.

File chain (``src/output/VTK_write_results_.f90``, ``src/output/VTK_type.f90``):

* ``<job>-all-results.pvd`` (``Collection``) in the working directory: one ``<DataSet timestep=T part="0"
  file="<job>-out/<job>-all-results-<istep>-<counter>.vtm"/>`` per frame, ``T`` = total time written with
  list-directed output (``VTK_type.f90:1405``, ``VTK_write_results_.f90:147-157``);
* ``.vtm`` (``vtkMultiBlockDataSet``): block ``Model elements`` with the datasets ``1D elements``,
  ``2D elements``, ``3D elements``; with ``EMBEDDED`` output a block ``Embedded interaction regions``
  (``VTK_write_results_.f90:1135-1191``). File names are relative to the ``.vtm``;
* ``.vtu`` (``UnstructuredGrid``, one ``Piece``), ASCII or raw appended binary.

Encodings as numgeo writes them:

* ASCII (``VTK_write_DataArray_.f90:41-232``, ``VTK_write_points_.f90:64-76``): values separated by blanks;
  ``Float64`` with ``g14.6`` (**6 significant digits**, also the points), temperature arrays with
  ``es25.16e3``; Fortran drops the ``E`` of 3-digit exponents (``0.123457-100``), which is parsed exactly.
* BINARY (``VTK_type.f90:1125-1137``, ``VTK_AppendedData_type_.f90:139-175``): ``header_type="UInt64"``,
  ``byte_order="LittleEndian"``, every array ``format="appended"``; after ``<AppendedData encoding="raw">``
  and ``_`` each block is an 8-byte length followed by the raw data. The reader honours ``header_type``
  (``UInt32`` is the VTK default when absent) and ``byte_order`` as declared in the file.
  Inline ``binary``/base64 arrays and compressed files are not written by numgeo and are rejected.

Arrays: ``PointData`` holds ``NodeLabel`` (``Int32``, node labels of the input), ``CellData``
``ElementLabel`` and ``TopologicalDimension`` (``VTK_write_results_.f90:1009-1075``). Names are stored
with leading/trailing blanks removed: numgeo pads some names (``"Strain 11     "``,
``VTK_write_strain_.f90:74-78``). Cells use numgeo's element node order without reordering
(``VTK_write_cells_.f90:87-104``); connectivity is 0-based into the dataset's own compact point list.

Tensor arrays ``Stress``/``Strain`` (6 components) are in VTK order ``[11, 22, 33, 12, 23, 13]``
(``VTK_write_stress_.f90:271``, ``VTK_write_strain_.f90:257``); the shear components of ``Strain`` are
**engineering** shear strains (gamma = 2 epsilon). The reader returns them unchanged; see
:func:`pynumgeo.results.voigt_to_tensor`.

Examples:
    >>> import pathlib, tempfile
    >>> d = pathlib.Path(tempfile.mkdtemp())
    >>> _ = (d / "a.vtu").write_text('''<?xml version="1.0"?>
    ... <VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">
    ...   <UnstructuredGrid>
    ...     <Piece NumberOfPoints="2" NumberOfCells="1">
    ...       <Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">
    ...         0.0 0.0 0.0 0.123457-100 1.0 0.0 </DataArray></Points>
    ...       <Cells>
    ...         <DataArray Name="connectivity" type="Int32" format="ascii"> 0 1 </DataArray>
    ...         <DataArray Name="offsets" type="Int32" format="ascii"> 2 </DataArray>
    ...         <DataArray type="UInt8" Name="types" format="ascii"> 3 </DataArray>
    ...       </Cells>
    ...       <PointData><DataArray Name="NodeLabel" type="Int32" format="ascii"> 1 2 </DataArray>
    ...       </PointData>
    ...     </Piece>
    ...   </UnstructuredGrid>
    ... </VTKFile>''')
    >>> v = read_vtu(d / "a.vtu")
    >>> float(v.points[1, 0]), v.node_labels.tolist(), [(t, c.tolist()) for t, c in v.cells]
    (1.23457e-101, [1, 2], [(3, [[0, 1]])])
"""

from __future__ import annotations

import itertools
import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from pynumgeo.results._fortran import parse_result_real, parse_result_reals

__all__ = [
    "DataArray",
    "PvdEntry",
    "VtmEntry",
    "VtuData",
    "find_array",
    "read_pvd",
    "read_vtm",
    "read_vtu",
]

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

#: VTK scalar type names -> numpy type codes (byte order added from the file).
_VTK_TYPES: dict[str, str] = {
    "Int8": "i1",
    "UInt8": "u1",
    "Int16": "i2",
    "UInt16": "u2",
    "Int32": "i4",
    "UInt32": "u4",
    "Int64": "i8",
    "UInt64": "u8",
    "Float32": "f4",
    "Float64": "f8",
}
_HEADER_TYPES: dict[str, str] = {"UInt32": "u4", "UInt64": "u8"}


@dataclass(frozen=True, eq=False)
class DataArray:
    """One ``DataArray`` of a ``PointData`` or ``CellData`` section.

    Attributes:
        name: array name with leading/trailing blanks removed.
        vtk_type: VTK scalar type as declared (``Float64``, ``Int32``, ``UInt8``, ...).
        values: shape ``(n,)`` for one component, ``(n, components)`` otherwise.
        component_names: ``ComponentName<i>`` attributes (numgeo writes them for the ``nset``/``elset``
            membership arrays, ``VTK_write_DataArray_.f90:403-426``), empty otherwise.
    """

    name: str
    vtk_type: str
    values: npt.NDArray[Any]
    component_names: tuple[str, ...] = ()

    @property
    def components(self) -> int:
        """Number of components."""
        return 1 if self.values.ndim == 1 else int(self.values.shape[1])


def find_array(arrays: Sequence[DataArray], name: str, where: str) -> DataArray:
    """Look up an array by name: exact (blanks stripped), else case-insensitive if unique.

    Raises:
        KeyError: no such array (the message lists the available names).
        ValueError: the name matches more than one array.
    """
    key = name.strip()
    exact = [a for a in arrays if a.name == key]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"{len(exact)} arrays named {key!r} in {where}")
    folded = [a for a in arrays if a.name.casefold() == key.casefold()]
    if len(folded) == 1:
        return folded[0]
    if len(folded) > 1:
        names = [a.name for a in folded]
        raise ValueError(f"{key!r} is ambiguous in {where}: {names}")
    raise KeyError(f"no array {key!r} in {where}; available: {[a.name for a in arrays]}")


@dataclass(frozen=True, eq=False)
class VtuData:
    """Contents of one ``.vtu`` file (one ``Piece``).

    Attributes:
        path: the file.
        points: ``(n, 3)`` coordinates (``z = 0`` in 2D models).
        connectivity: 0-based point indices of all cells, concatenated (numgeo node order).
        offsets: end position of each cell in ``connectivity`` (VTK convention).
        types: VTK cell type per cell (e.g. 23 for an 8-node quadrilateral).
        point_arrays: ``PointData`` arrays in file order.
        cell_arrays: ``CellData`` arrays in file order.
        name: dataset name in the ``.vtm`` (``"2D elements"``), ``None`` if read directly.
        block: names of the enclosing ``.vtm`` blocks, outermost first (``("Model elements",)``).
    """

    path: Path
    points: FloatArray
    connectivity: IntArray
    offsets: IntArray
    types: npt.NDArray[np.uint8]
    point_arrays: tuple[DataArray, ...]
    cell_arrays: tuple[DataArray, ...]
    name: str | None = None
    block: tuple[str, ...] = ()

    @property
    def number_of_points(self) -> int:
        """Number of points."""
        return int(self.points.shape[0])

    @property
    def number_of_cells(self) -> int:
        """Number of cells."""
        return int(self.types.shape[0])

    @property
    def cells(self) -> list[tuple[int, IntArray]]:
        """Cells as blocks ``(vtk_type, connectivity[k, nodes_per_cell])``.

        Consecutive cells with the same VTK type and node count form one block, so concatenating the
        blocks in order gives the cells in file order (the order of :meth:`cell_data`).
        """
        return cell_blocks(self.connectivity, self.offsets, self.types)

    @property
    def point_names(self) -> list[str]:
        """Names of the ``PointData`` arrays in file order."""
        return [a.name for a in self.point_arrays]

    @property
    def cell_names(self) -> list[str]:
        """Names of the ``CellData`` arrays in file order."""
        return [a.name for a in self.cell_arrays]

    def point_data(self, name: str) -> npt.NDArray[Any]:
        """Values of a ``PointData`` array (see :func:`find_array` for the name lookup)."""
        return find_array(self.point_arrays, name, f"PointData of {self.path}").values

    def cell_data(self, name: str) -> npt.NDArray[Any]:
        """Values of a ``CellData`` array (see :func:`find_array` for the name lookup)."""
        return find_array(self.cell_arrays, name, f"CellData of {self.path}").values

    @property
    def node_labels(self) -> IntArray:
        """Node labels of the points (``PointData`` ``NodeLabel``, VTK_write_results_.f90:1009-1029)."""
        return np.asarray(self.point_data("NodeLabel"), dtype=np.int64)

    @property
    def element_labels(self) -> IntArray:
        """Element labels of the cells (``CellData`` ``ElementLabel``, VTK_write_results_.f90:1034-1053)."""
        return np.asarray(self.cell_data("ElementLabel"), dtype=np.int64)


def cell_blocks(connectivity: IntArray, offsets: IntArray, types: npt.NDArray[Any]) -> list[tuple[int, IntArray]]:
    """Split VTK cell arrays into ``(vtk_type, connectivity[k, n])`` blocks of consecutive equal cells."""
    ncells = int(types.shape[0])
    if ncells == 0:
        return []
    starts = np.concatenate([[0], offsets[:-1]]).astype(np.int64)
    counts = offsets.astype(np.int64) - starts
    change = np.flatnonzero((types[1:] != types[:-1]) | (counts[1:] != counts[:-1])) + 1
    bounds = [0, *change.tolist(), ncells]
    blocks: list[tuple[int, IntArray]] = []
    for i, j in itertools.pairwise(bounds):
        n = int(counts[i])
        conn = connectivity[int(starts[i]) : int(offsets[j - 1])].reshape(j - i, n)
        blocks.append((int(types[i]), conn))
    return blocks


@dataclass(frozen=True)
class PvdEntry:
    """One ``<DataSet>`` of a ``.pvd`` collection.

    Attributes:
        time: ``timestep`` attribute: numgeo writes the total time (``cdb%time``; ``cdb%time0`` for a
            frame of increment 0), VTK_write_results_.f90:151-157.
        file: referenced file, resolved against the folder of the ``.pvd``.
        part: ``part`` attribute (numgeo writes 0).
    """

    time: float
    file: Path
    part: int


@dataclass(frozen=True)
class VtmEntry:
    """One ``<DataSet>`` with a file in a ``.vtm`` multiblock file.

    Attributes:
        name: dataset name (``"1D elements"``, ``"Beam"``, ``"Interaction surface"``).
        block: names of the enclosing blocks, outermost first.
        file: referenced ``.vtu``, resolved against the folder of the ``.vtm``.
    """

    name: str
    block: tuple[str, ...]
    file: Path


def read_pvd(path: str | Path) -> list[PvdEntry]:
    """Read a ParaView collection file (``<job>-all-results.pvd``), entries in file order.

    Raises:
        ValueError: if the file is not a ``Collection`` or an entry lacks ``timestep``/``file``.
    """
    p = Path(path)
    root = ET.parse(p).getroot()
    if root.tag != "VTKFile" or root.get("type") != "Collection":
        raise ValueError(f"{p}: not a VTK Collection file")
    coll = root.find("Collection")
    if coll is None:
        raise ValueError(f"{p}: no <Collection> element")
    out: list[PvdEntry] = []
    for ds in coll.findall("DataSet"):
        ts, fn = ds.get("timestep"), ds.get("file")
        if ts is None or fn is None:
            raise ValueError(f"{p}: <DataSet> without timestep or file")
        out.append(PvdEntry(time=parse_result_real(ts), file=p.parent / fn, part=int(ds.get("part", "0"))))
    return out


def read_vtm(path: str | Path) -> list[VtmEntry]:
    """Read a ``vtkMultiBlockDataSet`` file: all datasets with a file, in document order.

    Raises:
        ValueError: if the file is not a ``vtkMultiBlockDataSet``.
    """
    p = Path(path)
    root = ET.parse(p).getroot()
    if root.tag != "VTKFile" or root.get("type") != "vtkMultiBlockDataSet":
        raise ValueError(f"{p}: not a vtkMultiBlockDataSet file")
    top = root.find("vtkMultiBlockDataSet")
    if top is None:
        raise ValueError(f"{p}: no <vtkMultiBlockDataSet> element")
    out: list[VtmEntry] = []

    def walk(node: ET.Element, path_names: tuple[str, ...]) -> None:
        for child in node:
            if child.tag == "Block":
                walk(child, (*path_names, child.get("name", "")))
            elif child.tag == "DataSet" and child.get("file"):
                out.append(VtmEntry(child.get("name", ""), path_names, p.parent / str(child.get("file"))))

    walk(top, ())
    return out


def read_vtu(path: str | Path, *, name: str | None = None, block: tuple[str, ...] = ()) -> VtuData:
    """Read an ``UnstructuredGrid`` ``.vtu`` file as numgeo writes it (ASCII or raw appended binary).

    Args:
        path: the file.
        name: dataset name to record (from the ``.vtm``).
        block: enclosing block names to record (from the ``.vtm``).

    Raises:
        ValueError: for anything numgeo does not write (several pieces, compression, base64, unknown
            types) or inconsistent sizes.
    """
    p = Path(path)
    raw = p.read_bytes()
    root, appended = _split_appended(raw, p)
    if root.tag != "VTKFile" or root.get("type") != "UnstructuredGrid":
        raise ValueError(f"{p}: not a VTK UnstructuredGrid file")
    if root.get("compressor"):
        raise ValueError(f"{p}: compressed VTK files are not supported (numgeo writes none)")
    order = root.get("byte_order", "LittleEndian")
    if order not in ("LittleEndian", "BigEndian"):
        raise ValueError(f"{p}: unknown byte_order {order!r}")
    header = root.get("header_type", "UInt32")
    if header not in _HEADER_TYPES:
        raise ValueError(f"{p}: unknown header_type {header!r}")
    ctx = _Context(p, appended, "<" if order == "LittleEndian" else ">", _HEADER_TYPES[header])

    grid = root.find("UnstructuredGrid")
    pieces = [] if grid is None else grid.findall("Piece")
    if len(pieces) != 1:
        raise ValueError(f"{p}: expected one <Piece>, found {len(pieces)}")
    piece = pieces[0]
    npoints = int(piece.get("NumberOfPoints", "0"))
    ncells = int(piece.get("NumberOfCells", "0"))

    pts_el = piece.find("Points/DataArray")
    if pts_el is None:
        raise ValueError(f"{p}: no <Points> array")
    pts = _read_array(pts_el, ctx, npoints, "Points")
    if pts.components != 3 and npoints:
        raise ValueError(f"{p}: Points have {pts.components} components, expected 3")
    points = pts.values.astype(np.float64).reshape(npoints, 3)

    cell_arrays = {(el.get("Name") or "").strip(): el for el in piece.findall("Cells/DataArray")}
    for key in ("connectivity", "offsets", "types"):
        if key not in cell_arrays:
            raise ValueError(f"{p}: no Cells array {key!r}")
    offsets = _read_array(cell_arrays["offsets"], ctx, ncells, "offsets").values.astype(np.int64)
    nconn = int(offsets[-1]) if ncells else 0
    conn = _read_array(cell_arrays["connectivity"], ctx, nconn, "connectivity")
    connectivity = conn.values.astype(np.int64)
    types = _read_array(cell_arrays["types"], ctx, ncells, "types").values.astype(np.uint8)

    pdata = tuple(_read_array(el, ctx, npoints, "PointData") for el in piece.findall("PointData/DataArray"))
    cdata = tuple(_read_array(el, ctx, ncells, "CellData") for el in piece.findall("CellData/DataArray"))
    return VtuData(p, points, connectivity, offsets, types, pdata, cdata, name=name, block=block)


@dataclass(frozen=True)
class _Context:
    path: Path
    appended: bytes | None
    byte_order: str
    header_code: str


def _split_appended(raw: bytes, path: Path) -> tuple[ET.Element, bytes | None]:
    """XML part (parsed) and the raw appended data after ``_`` (VTK_type.f90:1159-1164)."""
    idx = raw.find(b"<AppendedData")
    if idx < 0:
        return ET.fromstring(raw), None
    tag_end = raw.index(b">", idx)
    tag = raw[idx : tag_end + 1].decode("ascii", "replace")
    m = re.search(r'encoding\s*=\s*"([^"]*)"', tag)
    if m is None or m.group(1) != "raw":
        raise ValueError(f"{path}: only raw appended data is supported, found {tag!r}")
    underscore = raw.find(b"_", tag_end + 1)
    if underscore < 0 or raw[tag_end + 1 : underscore].strip():
        raise ValueError(f"{path}: appended data does not start with '_'")
    return ET.fromstring(raw[:idx] + b"</VTKFile>"), raw[underscore + 1 :]


def _read_array(el: ET.Element, ctx: _Context, ntuples: int, where: str) -> DataArray:
    name = (el.get("Name") or "").strip()
    vtk_type = el.get("type", "")
    if vtk_type not in _VTK_TYPES:
        raise ValueError(f"{ctx.path}: {where} array {name!r} has unsupported type {vtk_type!r}")
    ncomp = int(el.get("NumberOfComponents", "1"))
    fmt = el.get("format", "ascii")
    code = _VTK_TYPES[vtk_type]
    if fmt == "ascii":
        tokens = (el.text or "").split()
        try:
            if code.startswith("f"):
                values: npt.NDArray[Any] = parse_result_reals(tokens).astype(code)
            else:
                values = np.array(tokens, dtype=np.int64).astype(code)
        except ValueError as exc:
            raise ValueError(f"{ctx.path}: {where} array {name!r}: {exc}") from None
    elif fmt == "appended":
        values = _read_appended(el, ctx, code, name, where)
    else:
        raise ValueError(f"{ctx.path}: {where} array {name!r}: format {fmt!r} is not supported")
    expected = ntuples * ncomp
    if values.size != expected:
        raise ValueError(f"{ctx.path}: {where} array {name!r} has {values.size} values, expected {ntuples} x {ncomp}")
    if ncomp > 1:
        values = values.reshape(ntuples, ncomp)
    comp_names = []
    for i in range(ncomp):
        cn = el.get(f"ComponentName{i}")
        if cn is None:
            break
        comp_names.append(cn)
    return DataArray(name, vtk_type, values, tuple(comp_names))


def _read_appended(el: ET.Element, ctx: _Context, code: str, name: str, where: str) -> npt.NDArray[Any]:
    if ctx.appended is None:
        raise ValueError(f"{ctx.path}: {where} array {name!r} is appended but the file has no AppendedData")
    offset = int(el.get("offset", "-1"))
    hdt = np.dtype(ctx.byte_order + ctx.header_code)
    start = offset + hdt.itemsize
    if offset < 0 or start > len(ctx.appended):
        raise ValueError(f"{ctx.path}: {where} array {name!r}: offset {offset} outside the appended data")
    nbytes = int(np.frombuffer(ctx.appended, dtype=hdt, count=1, offset=offset)[0])
    if start + nbytes > len(ctx.appended):
        raise ValueError(f"{ctx.path}: {where} array {name!r}: block of {nbytes} bytes is truncated")
    dt = np.dtype(ctx.byte_order + code)
    if nbytes % dt.itemsize:
        raise ValueError(f"{ctx.path}: {where} array {name!r}: {nbytes} bytes is not a multiple of {dt}")
    data = np.frombuffer(ctx.appended, dtype=dt, count=nbytes // dt.itemsize, offset=start)
    return data.astype(np.dtype(code))
